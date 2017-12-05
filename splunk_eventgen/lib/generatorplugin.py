from __future__ import division
import logging
import logging.handlers
import pprint
import datetime
from timeparser import timeParser
import httplib2, urllib
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from eventgenoutput import Output

class GeneratorPlugin(object):
    sampleLines = None
    sampleDict = None

    def __init__(self, sample):
        self._sample = sample
        self._setup_logging()

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def __getstate__(self):
        temp = self.__dict__
        if getattr(self, 'logger', None):
            temp.pop('logger', None)
        return temp

    def __setstate__(self, d):
        self.__dict__ = d
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')

    def updateConfig(self, config, outqueue):
        self.config = config
        self.outputQueue = outqueue
        # TODO: Figure out if this maxQueueLength needs to even be set here.  I think this should exist on the output
        # process and the generator shouldn't have anything to do with this.
        self.outputPlugin = self.config.getPlugin('output.' + self._sample.outputMode, self._sample)
        if self._sample.maxQueueLength == 0:
            self._sample.maxQueueLength = self.outputPlugin.MAXQUEUELENGTH
        # Output = output process, not the plugin.  The plugin is loaded by the output process.
        self._out = Output(self._sample)
        self._out.updateConfig(self.config)
        if self.outputPlugin.useOutputQueue or self.config.useOutputQueue:
            self._out._update_outputqueue(self.outputQueue)

    def updateCounts(self, sample=None, count=None, start_time=None, end_time=None):
        if sample:
            self._sample=sample
        self.count = count
        self.start_time = start_time
        self.end_time = end_time

    def setOutputMetadata(self, event):
        # self.logger.debug("Sample Index: %s Host: %s Source: %s Sourcetype: %s" % (self.index, self.host, self.source, self.sourcetype))
        # self.logger.debug("Event Index: %s Host: %s Source: %s Sourcetype: %s" % (sampleDict[x]['index'], sampleDict[x]['host'], sampleDict[x]['source'], sampleDict[x]['sourcetype']))
        if self._sample.sampletype == 'csv' and (event['index'] != self._sample.index or \
                                        event['host'] != self._sample.host or \
                                        event['source'] != self._sample.source or \
                                        event['sourcetype'] != self._sample.sourcetype):
            self._sample.index = event['index']
            self._sample.host = event['host']
            # Allow randomizing the host:
            if(self._sample.hostToken):
                self.host = self._sample.hostToken.replace(self.host)

            self._sample.source = event['source']
            self._sample.sourcetype = event['sourcetype']
            self.logger.debugv("Sampletype CSV.  Setting CSV parameters. index: '%s' host: '%s' source: '%s' sourcetype: '%s'" \
                        % (self._sample.index, self._sample.host, self._sample.source, self._sample.sourcetype))

    def setupBackfill(self):
        """Called by non-queueable plugins or by the timer to setup backfill times per config or based on a Splunk Search"""
        s = self._sample

        if s.backfill != None:
            try:
                s.backfillts = timeParser(s.backfill, timezone=s.timezone)
                self.logger.info("Setting up backfill of %s (%s)" % (s.backfill,s.backfillts))
            except Exception as ex:
                self.logger.error("Failed to parse backfill '%s': %s" % (s.backfill, ex))
                raise

            if s.backfillSearch != None:
                if s.backfillSearchUrl == None:
                    try:
                        s.backfillSearchUrl = c.getSplunkUrl(s)[0]
                    except ValueError:
                        self.logger.error("Backfill Search URL not specified for sample '%s', not running backfill search" % s.name)
                if not s.backfillSearch.startswith('search'):
                    s.backfillSearch = 'search ' + s.backfillSearch
                s.backfillSearch += '| head 1 | table _time'

                if s.backfillSearchUrl != None:
                    self.logger.debug("Searching Splunk URL '%s/services/search/jobs' with search '%s' with sessionKey '%s'" % (s.backfillSearchUrl, s.backfillSearch, s.sessionKey))
    
                    results = httplib2.Http(disable_ssl_certificate_validation=True).request(\
                                s.backfillSearchUrl + '/services/search/jobs',
                                'POST', headers={'Authorization': 'Splunk %s' % s.sessionKey}, \
                                body=urllib.urlencode({'search': s.backfillSearch,
                                                        'earliest_time': s.backfill,
                                                        'exec_mode': 'oneshot'}))[1]
                    try:
                        temptime = minidom.parseString(results).getElementsByTagName('text')[0].childNodes[0].nodeValue
                        # self.logger.debug("Time returned from backfill search: %s" % temptime)
                        # Results returned look like: 2013-01-16T10:59:15.411-08:00
                        # But the offset in time can also be +, so make sure we strip that out first
                        if len(temptime) > 0:
                            if temptime.find('+') > 0:
                                temptime = temptime.split('+')[0]
                            temptime = '-'.join(temptime.split('-')[0:3])
                        s.backfillts = datetime.datetime.strptime(temptime, '%Y-%m-%dT%H:%M:%S.%f')
                        self.logger.debug("Backfill search results: '%s' value: '%s' time: '%s'" % (pprint.pformat(results), temptime, s.backfillts))
                    except (ExpatError, IndexError): 
                        pass

        if s.end != None:
            parsed = False
            try:
                s.end = int(s.end)
                s.endts = None
                parsed = True
            except ValueError:
                self.logger.debug("Failed to parse end '%s' for sample '%s', treating as end time" % (s.end, s.name))
                
            if not parsed:    
                try:
                    s.endts = timeParser(s.end, timezone=s.timezone)
                    self.logger.info("Ending generation at %s (%s)" % (s.end, s.endts))
                except Exception as ex:
                    self.logger.error("Failed to parse end '%s' for sample '%s', treating as number of executions" % (s.end, s.name))
                    raise
    def run(self):
        self.gen(count=self.count, earliest=self.start_time, latest=self.end_time, samplename=self._sample.name)
        #TODO: Make this some how handle an output queue and support intervals and a master queue
        # Just double check to see if there's something in queue to flush out at the end of run
        if len(self._out._queue) > 0:
            self.logger.debug("Queue is not empty, flush out at the end of each run")
            self._out.flush()

def load():
    return GeneratorPlugin
