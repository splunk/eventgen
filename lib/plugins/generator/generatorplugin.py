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
from timeparser import timeParser
import httplib2, urllib
from xml.dom import minidom
from xml.parsers.expat import ExpatError

class GeneratorPlugin:
    queueable = True
    sampleLines = None
    sampleDict = None

    def __init__(self):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

        # logger.debug("Starting GeneratorPlugin for sample '%s' with generator '%s'" % (self._sample.name, self._sample.generator))

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

    def _openSampleFile(self):
        logger.debugv("Opening sample '%s' in app '%s'" % (self._sample.name, self._sample.app))
        self._sampleFH = open(self._sample.filePath, 'rU')

    def _closeSampleFile(self):
        logger.debugv("Closing sample '%s' in app '%s'" % (self._sample.name, self._sample.app))
        self._sampleFH.close()

    def loadSample(self, s):
        """Load sample from disk into self._sample.sampleLines and self._sample.sampleDict, 
        using cached copy if possible"""

        if s.sampletype == 'raw':
            # 5/27/12 CS Added caching of the sample file
            if s.sampleDict == None:
                self._openSampleFile()
                if s.breaker == c.breaker:
                    logger.debugv("Reading raw sample '%s' in app '%s'" % (s.name, s.app))
                    sampleLines = self._sampleFH.readlines()
                # 1/5/14 CS Moving to using only sampleDict and doing the breaking up into events at load time instead of on every generation
                else:
                    logger.debugv("Non-default breaker '%s' detected for sample '%s' in app '%s'" \
                                    % (s.breaker, s.name, s.app) ) 

                    sampleData = self._sampleFH.read()
                    sampleLines = [ ]

                    logger.debug("Filling array for sample '%s' in app '%s'; sampleData=%s, breaker=%s" \
                                    % (s.name, s.app, len(sampleData), s.breaker))

                    try:
                        breakerRE = re.compile(s.breaker, re.M)
                    except:
                        logger.error("Line breaker '%s' for sample '%s' in app '%s' could not be compiled; using default breaker" \
                                    % (s.breaker, s.name, s.app) )
                        s.breaker = c.breaker

                    # Loop through data, finding matches of the regular expression and breaking them up into
                    # "lines".  Each match includes the breaker itself.
                    extractpos = 0
                    searchpos = 0
                    breakerMatch = breakerRE.search(sampleData, searchpos)
                    while breakerMatch:
                        logger.debugv("Breaker found at: %d, %d" % (breakerMatch.span()[0], breakerMatch.span()[1]))
                        # Ignore matches at the beginning of the file
                        if breakerMatch.span()[0] != 0:
                            sampleLines.append(sampleData[extractpos:breakerMatch.span()[0]])
                            extractpos = breakerMatch.span()[0]
                        searchpos = breakerMatch.span()[1]
                        breakerMatch = breakerRE.search(sampleData, searchpos)
                    sampleLines.append(sampleData[extractpos:])

                self._closeSampleFile()

                self.sampleDict = [ { '_raw': line, 'index': s.index, 'host': s.host, 'source': s.source, 'sourcetype': s.sourcetype } for line in sampleLines ]
                s.sampleDict = self.sampleDict
                logger.debug('Finished creating sampleDict & sampleLines.  Len samplesLines: %d Len sampleDict: %d' % (len(sampleLines), len(self.sampleDict)))
            else:
                self.sampleLines = s.sampleLines
                self.sampleDict = s.sampleDict
        elif s.sampletype == 'csv':
            if s.sampleDict == None:
                self._openSampleFile()
                logger.debugv("Reading csv sample '%s' in app '%s'" % (s.name, s.app))
                self.sampleDict = [ ]
                # Fix to load large csv files, work with python 2.5 onwards
                csv.field_size_limit(sys.maxint)
                csvReader = csv.DictReader(self._sampleFH)
                for line in csvReader:
                    if '_raw' in line:
                        self.sampleDict.append(line)
                    else:
                        logger.error("Missing _raw in line '%s'" % pprint.pformat(line))
                self._closeSampleFile()
                s.sampleDict = copy.deepcopy(self.sampleDict)
                logger.debug('Finished creating sampleDict & sampleLines.  Len sampleDict: %d' % (len(self.sampleDict)))
            else:
                self.sampleDict = s.sampleDict
                self.sampleLines = s.sampleLines

        # Ensure all lines have a newline
        for i in xrange(0, len(self.sampleDict)):
            if self.sampleDict[i]['_raw'][-1] != '\n':
                self.sampleDict[i]['_raw'] += '\n'

    def setOutputMetadata(self, event):
        # logger.debug("Sample Index: %s Host: %s Source: %s Sourcetype: %s" % (self.index, self.host, self.source, self.sourcetype))
        # logger.debug("Event Index: %s Host: %s Source: %s Sourcetype: %s" % (sampleDict[x]['index'], sampleDict[x]['host'], sampleDict[x]['source'], sampleDict[x]['sourcetype']))
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
            logger.debugv("Sampletype CSV.  Setting CSV parameters. index: '%s' host: '%s' source: '%s' sourcetype: '%s'" \
                        % (self._sample.index, self._sample.host, self._sample.source, self._sample.sourcetype))

    def setupBackfill(self, s):
        """Called by non-queueable plugins or by the timer to setup backfill times per config or based on a Splunk Search"""
        if s.backfill != None:
            try:
                s.backfillts = timeParser(s.backfill, timezone=s.timezone)
                logger.info("Setting up backfill of %s (%s)" % (s.backfill,s.backfillts))
            except Exception as ex:
                logger.error("Failed to parse backfill '%s': %s" % (s.backfill, ex))
                raise

            if s.backfillSearch != None:
                if s.backfillSearchUrl == None:
                    s.backfillSearchUrl = c.getSplunkUrl(s)[0]
                if not s.backfillSearch.startswith('search'):
                    s.backfillSearch = 'search ' + s.backfillSearch
                s.backfillSearch += '| head 1 | table _time'

                logger.debug("Searching Splunk URL '%s/services/search/jobs' with search '%s' with sessionKey '%s'" % (s.backfillSearchUrl, s.backfillSearch, s.sessionKey))

                results = httplib2.Http(disable_ssl_certificate_validation=True).request(\
                            s.backfillSearchUrl + '/services/search/jobs',
                            'POST', headers={'Authorization': 'Splunk %s' % s.sessionKey}, \
                            body=urllib.urlencode({'search': s.backfillSearch,
                                                    'earliest_time': s.backfill,
                                                    'exec_mode': 'oneshot'}))[1]
                try:
                    temptime = minidom.parseString(results).getElementsByTagName('text')[0].childNodes[0].nodeValue
                    # logger.debug("Time returned from backfill search: %s" % temptime)
                    # Results returned look like: 2013-01-16T10:59:15.411-08:00
                    # But the offset in time can also be +, so make sure we strip that out first
                    if len(temptime) > 0:
                        if temptime.find('+') > 0:
                            temptime = temptime.split('+')[0]
                        temptime = '-'.join(temptime.split('-')[0:3])
                    s.backfillts = datetime.datetime.strptime(temptime, '%Y-%m-%dT%H:%M:%S.%f')
                    logger.debug("Backfill search results: '%s' value: '%s' time: '%s'" % (pprint.pformat(results), temptime, s.backfillts))
                except (ExpatError, IndexError): 
                    pass


def load():
    return GeneratorPlugin