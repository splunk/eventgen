from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
from eventgenoutput import Output
import multiprocessing
import csv

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

    def loadSample(self):
        """Load sample from disk into self._sample.sampleLines and self._sample.sampleDict, 
        using cached copy if possible"""
        # Making a copy of self._sample in a short name to save typing
        sample = self._sample

        logger.debugv("Opening sample '%s' in app '%s'" % (sample.name, sample.app) )
        sampleFH = open(sample.filePath, 'rU')
        if sample.sampletype == 'raw':
            # 5/27/12 CS Added caching of the sample file
            if sample.sampleLines == None:
                logger.debug("Reading raw sample '%s' in app '%s'" % (sample.name, sample.app))
                self.sampleLines = sampleFH.readlines()
                sample.sampleLines = self.sampleLines
                self.sampleDict = [ ]
            else:
                self.sampleLines = sample.sampleLines
        elif self.sampletype == 'csv':
            logger.debug("Reading csv sample '%s' in app '%s'" % (sample.name, sample.app))
            if sample.sampleLines == None:
                logger.debug("Reading csv sample '%s' in app '%s'" % (self.name, self.app))
                self.sampleDict = [ ]
                self.sampleLines = [ ]
                # Fix to load large csv files, work with python 2.5 onwards
                csv.field_size_limit(sys.maxint)
                csvReader = csv.DictReader(sampleFH)
                for line in csvReader:
                    self.sampleDict.append(line)
                    try:
                        tempstr = line['_raw'].decode('string_escape')
                        # Hack for bundlelines
                        if sample.bundlelines:
                            tempstr = tempstr.replace('\n', 'NEWLINEREPLACEDHERE!!!')
                        self.sampleLines.append(tempstr)
                    except ValueError:
                        logger.error("Error in sample at line '%d' in sample '%s' in app '%s' - did you quote your backslashes?" % (csvReader.line_num, self.name, self.app))
                    except AttributeError:
                        logger.error("Missing _raw at line '%d' in sample '%s' in app '%s'" % (csvReader.line_num, self.name, self.app))
                sample.sampleDict = copy.deepcopy(sampleDict)
                sample.sampleLines = copy.deepcopy(sampleLines)
                logger.debug('Finished creating sampleDict & sampleLines.  Len samplesLines: %d Len sampleDict: %d' % (len(sampleLines), len(sampleDict)))
            else:
                # If we're set to bundlelines, we'll modify sampleLines regularly.
                # Since lists in python are referenced rather than copied, we
                # need to make a fresh copy every time if we're bundlelines.
                # If not, just used the cached copy, we won't mess with it.
                if not sample.bundlelines:
                    self.sampleDict = sample.sampleDict
                    self.sampleLines = sample.sampleLines
                else:
                    self.sampleDict = copy.deepcopy(sample.sampleDict)
                    self.sampleLines = copy.deepcopy(sample.sampleLines)


def load():
    return GeneratorPlugin