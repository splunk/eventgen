# TODO: Sample object is incredibly overloaded and not threadsafe. Need to make it simpler to get a copy without the
# whole object get a copy of whats needed without the whole object.

from __future__ import division

import datetime
import random

from generatorplugin import GeneratorPlugin


class DefaultGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def gen(self, count, earliest, latest, samplename=None):
        self.logger.debug("Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'" %
                          (self._sample.name, self._sample.app, count, earliest, latest))
        startTime = datetime.datetime.now()

        # If we're random, fill random events from sampleDict into eventsDict
        if self._sample.randomizeEvents:
            eventsDict = []
            sdlen = len(self._sample.sampleDict)
            self.logger.debugv("Random filling eventsDict for sample '%s' in app '%s' with %d events" %
                               (self._sample.name, self._sample.app, count))
            # Count is -1, replay the whole file, but in randomizeEvents I think we'd want it to actually
            # just put as many events as there are in the file
            if count == -1:
                count = sdlen
            while len(eventsDict) < count:
                eventsDict.append(self._sample.sampleDict[random.randint(0, sdlen - 1)])

        # If we're bundlelines, create count copies of the sampleDict
        elif self._sample.bundlelines:
            eventsDict = []
            self.logger.debugv(
                "Bundlelines, filling eventsDict for sample '%s' in app '%s' with %d copies of sampleDict" %
                (self._sample.name, self._sample.app, count))
            for x in xrange(count):
                eventsDict.extend(self._sample.sampleDict)

        # Otherwise fill count events into eventsDict or keep making copies of events out of sampleDict until
        # eventsDict is as big as count
        else:
            # If count is -1, play the whole file, else grab a subset
            if count == -1:
                count = len(self._sample.sampleDict)
            eventsDict = self._sample.sampleDict[0:count]

            # Continue to fill events array until len(events) == count
            if len(eventsDict) < count:
                self.logger.debugv(
                    "Events fill for sample '%s' in app '%s' less than count (%s vs. %s); continuing fill" %
                    (self._sample.name, self._sample.app, len(eventsDict), count))
                self.logger.debugv("Current eventsDict: %s" % eventsDict)
                # run a modulus on the size of the eventdict to figure out what the last event was.  Populate to count
                # from there.

                while len(eventsDict) < count:
                    if len(self._sample.sampleDict):
                        nextEventToUse = self._sample.sampleDict[len(eventsDict) % len(self._sample.sampleDict)]
                        self.logger.debugv("Next event to add: %s" % nextEventToUse)
                        eventsDict.append(nextEventToUse)
                self.logger.debugv("Events fill complete for sample '%s' in app '%s' length %d" %
                                   (self._sample.name, self._sample.app, len(eventsDict)))

        GeneratorPlugin.build_events(self, eventsDict, startTime, earliest, latest)

def load():
    return DefaultGenerator
