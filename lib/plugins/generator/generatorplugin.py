from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
from eventgenoutput import Output
import csv
import copy
import re
import pprint
import datetime
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

        # 2/10/14 CS Make a threadsafe copy of all of the samples for us to work on
        # with c.copyLock:
        self._samples = dict((s.name, copy.deepcopy(s)) for s in c.samples)
        self._sample = sample

        # self.logger.debug("Starting GeneratorPlugin for sample '%s' with generator '%s'" % (self._sample.name, self._sample.generator))

        # multiprocessing.Process.__init__(self)

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def updateSample(self, sample):
        self._sample = sample

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
                    s.backfillSearchUrl = c.getSplunkUrl(s)[0]
                if not s.backfillSearch.startswith('search'):
                    s.backfillSearch = 'search ' + s.backfillSearch
                s.backfillSearch += '| head 1 | table _time'

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
            try:
                s.endts = timeParser(s.end, timezone=s.timezone)
                self.logger.info("Ending generation at %s (%s)" % (s.end, s.endts))
            except Exception as ex:
                self.logger.error("Failed to parse end '%s': %s" % (s.end, ex))
                raise


def load():
    return GeneratorPlugin