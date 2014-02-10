from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import random
import copy

class DefaultGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, count, earliest, latest, samplename=None):
        # For shortness sake, we're going to call the sample s
        s = None
        for x in c.samples:
            if x.name == samplename:
                s = copy.deepcopy(x)
                self._sample = s
                # Load sample from a file, using cache if possible, from superclass GeneratorPlugin
                self.loadSample(s)

        if s == None:
            raise ValueError("Error in DefaultGenerator.gen: Sample '%s' not found" % samplename)

        logger.debug("Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'" % (s.name, s.app, count, earliest, latest))
        startTime = datetime.datetime.now()

        # If we're random, fill random events from sampleDict into eventsDict
        if s.randomizeEvents:
            eventsDict = [ ]
            sdlen = len(self.sampleDict)
            logger.debugv("Random filling eventsDict for sample '%s' in app '%s' with %d events" % (s.name, s.app, count))
            # Count is zero, replay the whole file, but in randomizeEvents I think we'd want it to actually 
            # just put as many events as there are in the file
            if count == 0:
                count = sdlen
            while len(eventsDict) < count:
                eventsDict.append(self.sampleDict[random.randint(0, sdlen-1)])
        # If we're bundlelines, create count copies of the sampleDict
        elif s.bundlelines:
            eventsDict = [ ]
            logger.debugv("Bundlelines, filling eventsDict for sample '%s' in app '%s' with %d copies of sampleDict" % (s.name, s.app, count))
            for x in xrange(count):
                eventsDict.extend(self.sampleDict)
        # Otherwise fill count events into eventsDict or keep making copies of events out of sampleDict until
        # eventsDict is as big as count
        else:
            # If count is 0, play the whole file, else grab a subset
            if count == 0:
                count = len(self.sampleDict)
            eventsDict = self.sampleDict[0:count]

            ## Continue to fill events array until len(events) == count
            if len(eventsDict) < count:
                logger.debugv("Events fill for sample '%s' in app '%s' less than count (%s vs. %s); continuing fill" % (s.name, s.app, len(eventsDict), count) )
                tempEventsDict = eventsDict[:]
                while len(eventsDict) < count:
                    y = 0
                    while len(eventsDict) < count and y < len(tempEventsDict):
                        eventsDict.append(tempEventsDict[y])
                        y += 1
                logger.debugv("Events fill complete for sample '%s' in app '%s' length %d" % (s.name, s.app, len(eventsDict)))


        for x in range(len(eventsDict)):
            event = eventsDict[x]['_raw']

            # Maintain state for every token in a given event
            # Hash contains keys for each file name which is assigned a list of values
            # picked from a random line in that file
            mvhash = { }

            ## Iterate tokens
            for token in s.tokens:
                token.mvhash = mvhash
                # logger.debugv("Replacing token '%s' of type '%s' in event '%s'" % (token.token, token.replacementType, event))
                event = token.replace(event, et=earliest, lt=latest, s=s)
            if(s.hostToken):
                # clear the host mvhash every time, because we need to re-randomize it
                s.hostToken.mvhash =  {}

            host = eventsDict[x]['host']
            if (s.hostToken):
                host = s.hostToken.replace(host, s=s)

            if s.timestamp == None:
                s.timestamp = s.now()
            l = [ { '_raw': event,
                    'index': eventsDict[x]['index'],
                    'host': host,
                    'hostRegex': s.hostRegex,
                    'source': eventsDict[x]['source'],
                    'sourcetype': eventsDict[x]['sourcetype'],
                    '_time': time.mktime(s.timestamp.timetuple()) } ]

            s.out.bulksend(l)
            s.timestamp = None

        endTime = datetime.datetime.now()
        timeDiff = endTime - startTime
        timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
        s.out.flush(endOfInterval=True)
        logger.debug("Generation of sample '%s' in app '%s' completed in %s seconds." % (s.name, s.app, timeDiffFrac) )

def load():
    return DefaultGenerator