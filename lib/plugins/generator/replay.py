# TODO Add timestamp detection for common timestamp format

from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import math

class ReplayGenerator(GeneratorPlugin):
    queueable = False
    _rpevents = None
    _currentevent = None
    _times = None
    _timeSinceSleep = None
    _lastts = None

    def __init__(self, sample):
        GeneratorPlugin.__init__(self)

        self._sample = sample

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

        self._currentevent = 0
        self._timeSinceSleep = datetime.timedelta()
        self._times = [ ]

        # Load sample from a file, using cache if possible, from superclass GeneratorPlugin
        self.loadSample(sample)
        self._rpevents = self.sampleDict
        self._currentevent = 0

        self.setupBackfill(sample.name)


    def gen(self, count, earliest, latest):
        # For shortness sake, we're going to call the sample s
        s = self._sample

        logger.debug("Generating sample '%s' in app '%s'" % (s.name, s.app))
        startTime = datetime.datetime.now()

        # If we are replaying then we need to set the current sampleLines to the event
        # we're currently on
        self.sampleDict = [ self._rpevents[self._currentevent] ]

        self.setOutputMetadata(self.sampleDict[0])

        logger.debugv("Finding timestamp to compute interval for events")
        if self._lastts == None:
            self._lastts = s.getTSFromEvent(self._rpevents[self._currentevent][s.timeField])
        if (self._currentevent+1) < len(self._rpevents):
            nextts = s.getTSFromEvent(self._rpevents[self._currentevent+1][s.timeField])
        else:
            logger.debugv("At end of _rpevents")
            # At the end of the buffer, we sould wait the average amount of time at the end 
            # return 0
            avgtimes = sum(list(self._times)) / len(self._times) / s.timeMultiple
            interval = datetime.timedelta(seconds=int(math.modf(avgtimes)[1]), microseconds=int(round(math.modf(avgtimes)[0] * 1000000, 0)))
            nextts = self._lastts + interval
            logger.debugv("Setting nextts to '%s' with avgtimes '%d' and interval '%s'" % (nextts, avgtimes, interval))
            self._times = [ ]

        logger.debugv('Computing timeDiff nextts: "%s" lastts: "%s"' % (nextts, self._lastts))

        timeDiff = nextts - self._lastts
        if timeDiff.days >= 0 and timeDiff.seconds >= 0 and timeDiff.microseconds >= 0:
            partialInterval = float("%d.%06d" % (timeDiff.seconds, timeDiff.microseconds))
        else:
            partialInterval = 0

        if s.timeMultiple > 0:
            partialInterval *= s.timeMultiple

        logger.debugv("Setting partialInterval for replay mode with timeMultiple %s: %s %s" % (s.timeMultiple, timeDiff, partialInterval))
        self._lastts = nextts

        for x in range(len(self.sampleDict)):
            event = self.sampleDict[x]['_raw']

            # Maintain state for every token in a given event
            # Hash contains keys for each file name which is assigned a list of values
            # picked from a random line in that file
            mvhash = { }

            ## Iterate tokens
            for token in s.tokens:
                token.mvhash = mvhash
                event = token.replace(event)
            if(s.hostToken):
                # clear the host mvhash every time, because we need to re-randomize it
                s.hostToken.mvhash =  {}

            host = eventsDict[x]['host']
            if (s.hostToken):
                host = s.hostToken.replace(host, s=s)

            l = [ { '_raw': event,
                    'index': eventsDict[x]['index'],
                    'host': host,
                    'hostRegex': s.hostRegex,
                    'source': eventsDict[x]['source'],
                    'sourcetype': eventsDict[x]['sourcetype'],
                    '_time': time.mktime(s.timestamp.timetuple()) } ]

            s.out.bulksend(l)


        # If we roll over the max number of lines, roll over the counter and start over
        if (self._currentevent+1) >= len(self._rpevents):
            logger.debug("At end of the sample file, starting replay from the top")
            self._currentevent = 0
            self._lastts = None
        else:
            self._currentevent += 1


        # Track time we were running and time we need to sleep
        endTime = datetime.datetime.now()
        timeDiff = endTime - startTime
        self._timeSinceSleep += timeDiff

        if partialInterval > 0:
            timeDiffFrac = "%d.%06d" % (self._timeSinceSleep.seconds, self._timeSinceSleep.microseconds)
            logger.info("Generation of sample '%s' in app '%s' completed in %s seconds.  Sleeping for %f seconds" \
                        % (s.name, s.app, timeDiffFrac, partialInterval) )
            self._timeSinceSleep = datetime.timedelta()

            # Add for average sleep time calculation when we're at the end of the events
            self._times.append(partialInterval)

        return partialInterval



def load():
    return ReplayGenerator