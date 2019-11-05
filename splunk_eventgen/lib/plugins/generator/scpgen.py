# TODO: Sample object is incredibly overloaded and not threadsafe. Need to make it simpler to get a copy without the
# whole object get a copy of whats needed without the whole object.

from __future__ import division

import time
import datetime
import random

from generatorplugin import GeneratorPlugin
from eventgentimestamp import EventgenTimestamp
from logging_config import logger

class SCPGen(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def replace_tokens(self, eventsDict, earliest, latest, ignore_tokens=False):
        """Iterate event tokens and replace them. This will help calculations for event size when tokens are used."""
        eventcount = 0
        send_events = []
        total_count = len(eventsDict)
        index = None
        if total_count > 0:
            index = random.choice(self._sample.index_list) if len(self._sample.index_list) else eventsDict[0]['index']
        for targetevent in eventsDict:
            if self.gc_obj is not None:
                with self.gc_obj.get_lock():
                    self.gc_obj.value += 1
                    global_count = self.gc_obj.value
            event = targetevent["_raw"]
            # Maintain state for every token in a given event, Hash contains keys for each file name which is
            # assigned a list of values picked from a random line in that file
            mvhash = {}
            host = targetevent['host']
            if hasattr(self._sample, "sequentialTimestamp") and self._sample.sequentialTimestamp and \
                    self._sample.generator != 'perdayvolumegenerator':
                pivot_timestamp = EventgenTimestamp.get_sequential_timestamp(earliest, latest, eventcount, total_count)
            else:
                pivot_timestamp = EventgenTimestamp.get_random_timestamp(earliest, latest)
            # Iterate tokens
            if not ignore_tokens:
                for token in self._sample.tokens:
                    if self.gc_obj is not None:
                        setattr(token, "global_count", global_count)
                    token.mvhash = mvhash
                    event = token.replace(event, et=earliest, lt=latest, s=self._sample,
                                          pivot_timestamp=pivot_timestamp)
                    if token.replacementType == 'timestamp' and self._sample.timeField != '_raw':
                        self._sample.timestamp = None
                        token.replace(targetevent[self._sample.timeField], et=self._sample.earliestTime(),
                                      lt=self._sample.latestTime(), s=self._sample, pivot_timestamp=pivot_timestamp)
                if self._sample.hostToken:
                    # clear the host mvhash every time, because we need to re-randomize it
                    self._sample.hostToken.mvhash = {}
                if self._sample.hostToken:
                    host = self._sample.hostToken.replace(host, s=self._sample)
            try:
                time_val = int(time.mktime(pivot_timestamp.timetuple()))
            except Exception:
                time_val = int(time.mktime(self._sample.now().timetuple()))
            # Modified temp_event to meet SCP ingest API requited format
            temp_event = {
                'body': event.rstrip(), 
                'sourcetype': targetevent['sourcetype'], 
                'source': targetevent['source'], 
                'host': host,
                'attributes': {
                    '_time': time_val, 
                    'hostRegex': self._sample.hostRegex
                    }
                }

            send_events.append(temp_event)
            
        return send_events

    def gen(self, count, earliest, latest, samplename=None):
        logger.debug("Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'" %
                          (self._sample.name, self._sample.app, count, earliest, latest))
        startTime = datetime.datetime.now()

        # If we're random, fill random events from sampleDict into eventsDict
        if self._sample.randomizeEvents:
            eventsDict = []
            sdlen = len(self._sample.sampleDict)
            logger.debug("Random filling eventsDict for sample '%s' in app '%s' with %d events" %
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
            logger.debug(
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
                logger.debug(
                    "Events fill for sample '%s' in app '%s' less than count (%s vs. %s); continuing fill" %
                    (self._sample.name, self._sample.app, len(eventsDict), count))
                logger.debug("Current eventsDict: %s" % eventsDict)
                # run a modulus on the size of the eventdict to figure out what the last event was.  Populate to count
                # from there.

                while len(eventsDict) < count:
                    if len(self._sample.sampleDict):
                        nextEventToUse = self._sample.sampleDict[len(eventsDict) % len(self._sample.sampleDict)]
                        logger.debug("Next event to add: %s" % nextEventToUse)
                        eventsDict.append(nextEventToUse)
                logger.debug("Events fill complete for sample '%s' in app '%s' length %d" %
                                   (self._sample.name, self._sample.app, len(eventsDict)))

        GeneratorPlugin.build_events(self, eventsDict, startTime, earliest, latest)


def load():
    return SCPGen
