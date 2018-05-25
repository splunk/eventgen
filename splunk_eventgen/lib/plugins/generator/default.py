# TODO Sample object now incredibly overloaded and not threadsafe.  Need to make it threadsafe and make it simpler to get a
#       copy of whats needed without the whole object.

from __future__ import division
from generatorplugin import GeneratorPlugin
import datetime, time
import random
from eventgentimestamp import EventgenTimestamp


class DefaultGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def gen(self, count, earliest, latest, samplename=None):
        s = self._sample

        self.logger.debug("Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'" % (self._sample.name, self._sample.app, count, earliest, latest))
        startTime = datetime.datetime.now()

        # If we're random, fill random events from sampleDict into eventsDict
        if self._sample.randomizeEvents:
            eventsDict = [ ]
            sdlen = len(self._sample.sampleDict)
            self.logger.debugv("Random filling eventsDict for sample '%s' in app '%s' with %d events" % (self._sample.name, self._sample.app, count))
            # Count is -1, replay the whole file, but in randomizeEvents I think we'd want it to actually 
            # just put as many events as there are in the file
            if count == -1:
                count = sdlen
            while len(eventsDict) < count:
                eventsDict.append(self._sample.sampleDict[random.randint(0, sdlen-1)])

        # If we're bundlelines, create count copies of the sampleDict
        elif self._sample.bundlelines:
            eventsDict = [ ]
            self.logger.debugv("Bundlelines, filling eventsDict for sample '%s' in app '%s' with %d copies of sampleDict" % (self._sample.name, self._sample.app, count))
            for x in xrange(count):
                eventsDict.extend(self._sample.sampleDict)

        # Otherwise fill count events into eventsDict or keep making copies of events out of sampleDict until
        # eventsDict is as big as count
        else:
            # If count is -1, play the whole file, else grab a subset
            if count == -1:
                count = len(self._sample.sampleDict)
            eventsDict = self._sample.sampleDict[0:count]

            ## Continue to fill events array until len(events) == count
            if len(eventsDict) < count:
                self.logger.debugv("Events fill for sample '%s' in app '%s' less than count (%s vs. %s); continuing fill" % (self._sample.name, self._sample.app, len(eventsDict), count) )
                self.logger.debugv("Current eventsDict: %s" % eventsDict)
                # run a modulus on the size of the eventdict to figure out what the last event was.  Populate to count
                # from there.

                while len(eventsDict) < count:
                    if len(self._sample.sampleDict):
                        nextEventToUse = self._sample.sampleDict[len(eventsDict) % len(self._sample.sampleDict)]
                        self.logger.debugv("Next event to add: %s" % nextEventToUse)
                        eventsDict.append(nextEventToUse)
                self.logger.debugv("Events fill complete for sample '%s' in app '%s' length %d" % (self._sample.name, self._sample.app, len(eventsDict)))

        eventcount=0
        for targetevent in eventsDict:
            try:
                event = targetevent['_raw']
                if event == "\n":
                    continue

                # Maintain state for every token in a given event
                # Hash contains keys for each file name which is assigned a list of values
                # picked from a random line in that file
                mvhash = { }

                pivot_timestamp = EventgenTimestamp.get_random_timestamp(earliest, latest, self._sample.earliest, self._sample.latest)

                ## Iterate tokens
                for token in self._sample.tokens:
                    token.mvhash = mvhash
                    # self.logger.debugv("Replacing token '%s' of type '%s' in event '%s'" % (token.token, token.replacementType, event))
                    self.logger.debugv("Sending event to token replacement: Event:{0} Token:{1}".format(event, token))
                    event = token.replace(event, et=earliest, lt=latest, s=self._sample, pivot_timestamp=pivot_timestamp)
                    self.logger.debugv("finished replacing token")
                    if token.replacementType == 'timestamp' and self._sample.timeField != '_raw':
                        self._sample.timestamp = None
                        token.replace(targetevent[self._sample.timeField], et=self._sample.earliestTime(), lt=self._sample.latestTime(), s=self._sample, pivot_timestamp=pivot_timestamp)
                if(self._sample.hostToken):
                    # clear the host mvhash every time, because we need to re-randomize it
                    self._sample.hostToken.mvhash = {}

                host = targetevent['host']
                if (self._sample.hostToken):
                    host = self._sample.hostToken.replace(host, s=self._sample)

                try:
                    time_val = int(time.mktime(pivot_timestamp.timetuple()))
                except Exception:
                    time_val = int(time.mktime(self._sample.now().timetuple()))

                l = [ { '_raw': event,
                        'index': targetevent['index'],
                        'host': host,
                        'hostRegex': self._sample.hostRegex,
                        'source': targetevent['source'],
                        'sourcetype': targetevent['sourcetype'],
                        '_time': time_val } ]
                self.logger.debugv("Finished Processing event: %s" % eventcount)
                eventcount += 1
                self._out.bulksend(l)
                self._sample.timestamp = None
            except Exception as e:
                self.logger.exception("Exception {} happened.".format(type(e)))
                raise e

        try:
            endTime = datetime.datetime.now()
            timeDiff = endTime - startTime
            timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
            self.logger.debugv("Interval complete, flushing feed")
            self._out.flush(endOfInterval=True)
            self.logger.debug("Generation of sample '%s' in app '%s' completed in %s seconds." % (
            self._sample.name, self._sample.app, timeDiffFrac))
        except Exception as e:
            self.logger.exception("Exception {} happened.".format(type(e)))
            raise e

def load():
    return DefaultGenerator
