from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
from eventgenoutput import Output
import multiprocessing
import csv
import copy
import re

class GeneratorPlugin(multiprocessing.Process):
    queueable = True
    sampleLines = None
    sampleDict = None

    def __init__(self, sample):
        self._sample = sample
        
        self._queue = deque([])

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

        logger.debug("Starting GeneratorPlugin for sample '%s' with generator '%s'" % (self._sample.name, self._sample.generator))

        multiprocessing.Process.__init__(self)

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def _openSampleFile(self):
        logger.debugv("Opening sample '%s' in app '%s'" % (self._sample.name, self._sample.app))
        self._sampleFH = open(self._sample.filePath, 'rU')

    def _closeSampleFile(self):
        logger.debugv("Closing sample '%s' in app '%s'" % (self._sample.name, self._sample.app))
        self._sampleFH.close()

    def loadSample(self):
        """Load sample from disk into self._sample.sampleLines and self._sample.sampleDict, 
        using cached copy if possible"""
        # Making a copy of self._sample in a short name to save typing
        s = self._sample

        if s.sampletype == 'raw':
            # 5/27/12 CS Added caching of the sample file
            if s.sampleLines == None or s.sampleDict == None:
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
            if s.sampleLines == None or s.sampleDict == None:
                self._openSampleFile()
                logger.debugv("Reading csv sample '%s' in app '%s'" % (s.name, s.app))
                self.sampleDict = [ ]
                self.sampleLines = [ ]
                # Fix to load large csv files, work with python 2.5 onwards
                csv.field_size_limit(sys.maxint)
                csvReader = csv.DictReader(self._sampleFH)
                for line in csvReader:
                    self.sampleDict.append(line)
                    try:
                        tempstr = line['_raw'].decode('string_escape')
                        # Hack for bundlelines
                        if s.bundlelines:
                            tempstr = tempstr.replace('\n', 'NEWLINEREPLACEDHERE!!!')
                        self.sampleLines.append(tempstr)
                    except ValueError:
                        logger.error("Error in sample at line '%d' in sample '%s' in app '%s' - did you quote your backslashes?" % (csvReader.line_num, self.name, self.app))
                    except AttributeError:
                        logger.error("Missing _raw at line '%d' in sample '%s' in app '%s'" % (csvReader.line_num, self.name, self.app))
                self._closeSampleFile()
                s.sampleDict = copy.deepcopy(self.sampleDict)
                s.sampleLines = copy.deepcopy(self.sampleLines)
                logger.debug('Finished creating sampleDict & sampleLines.  Len samplesLines: %d Len sampleDict: %d' % (len(self.sampleLines), len(self.sampleDict)))
            else:
                # If we're set to bundlelines, we'll modify sampleLines regularly.
                # Since lists in python are referenced rather than copied, we
                # need to make a fresh copy every time if we're bundlelines.
                # If not, just used the cached copy, we won't mess with it.
                if not s.bundlelines:
                    self.sampleDict = s.sampleDict
                    self.sampleLines = s.sampleLines
                else:
                    self.sampleDict = copy.deepcopy(s.sampleDict)
                    self.sampleLines = copy.deepcopy(s.sampleLines)

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


def load():
    return GeneratorPlugin