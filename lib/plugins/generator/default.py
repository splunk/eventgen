from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime
import random

class DefaultGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, count, earliest, latest):
        # For shortness sake, we're going to call the sample s
        s = self._sample

        logger.debug("Generating sample '%s' in app '%s'" % (self._sample.name, self._sample.app))
        startTime = datetime.datetime.now()
        # Load sample from a file, using cache if possible, from superclass GeneratorPlugin
        self.loadSample()

        if s.randomizeEvents:
            eventsDict = [ ]
            sdlen = len(self.sampleDict)
            while len(eventsDict) < count:
                eventsDict.append(self.sampleDict[random.randint(0, sdlen-1)])
        else:
            eventsDict = self.sampleDict[0:count if count < len(self.sampleDict) else len(self.sampleDict)]

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
                logger.debugv("Replacing token '%s' of type '%s' in event '%s'" % (token.token, token.replacementType, event))
                event = token.replace(event)
            if(s.hostToken):
                # clear the host mvhash every time, because we need to re-randomize it
                s.hostToken.mvhash =  {}

            self.setOutputMetadata(eventsDict[x])

            s.out.send(event)

        endTime = datetime.datetime.now()
        timeDiff = endTime - startTime
        timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
        logger.info("Generation of sample '%s' in app '%s' completed in %s seconds." % (s.name, s.app, timeDiffFrac) )

def load():
    return DefaultGenerator