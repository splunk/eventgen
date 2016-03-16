from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
import csv
import copy
import re
import pprint
import datetime, time
from timeparser import timeParser
import httplib2, urllib
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from eventgenoutput import Output

class GeneratorPlugin:
    queueable = True
    sampleLines = None
    sampleDict = None

    def __init__(self, sample):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'GeneratorPlugin', 'sample': sample.name})
        self.logger = adapter
        
        from eventgenconfig import Config
        globals()['c'] = Config()
        
        # # 2/10/14 CS Make a threadsafe copy of all of the samples for us to work on
        # with c.copyLock:
        #     # 10/9/15 CS Moving this to inside the lock, in theory, there should only be one thread
        #     # trying to start at once, going to try to ensure this is the case and hoping for no deadlocks
        #     while c.pluginsStarting.value() > 0:
        #         self.logger.debug("Waiting for exclusive lock to start for GeneratorPlugin '%s'" % sample.name)
        #         time.sleep(0.1)
            
        #     c.pluginsStarting.increment()
        self.logger.debug("GeneratorPlugin being initialized for sample '%s'" % sample.name)
        
        self._out = Output(sample)
        
        # # 9/6/15 Don't do any work until all the timers have started
        # while c.timersStarted.value() < len(c.sampleTimers):
        #     self.logger.debug("Not all timers started, sleeping for GeneratorPlugin '%s'" % sample.name)
        #     time.sleep(1.0)
        
        self._samples = { }
        for s in c.samples:
            news = copy.copy(s)
            news.tokens = [ copy.copy(t) for t in s.tokens ]
            for setting in c._jsonSettings:
                if setting in s.__dict__:
                    setattr(news, setting, getattr(s, setting))
            self._samples[news.name] = news
             
        # self._samples = dict((s.name, copy.deepcopy(s)) for s in c.samples)
        self._sample = sample
    
            # c.pluginsStarting.decrement()
            # c.pluginsStarted.increment()
            # # self.logger.debug("Starting GeneratorPlugin for sample '%s' with generator '%s'" % (self._sample.name, self._sample.generator))

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def updateSample(self, samplename):
        self._sample = self._samples[samplename]

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


def load():
    return GeneratorPlugin