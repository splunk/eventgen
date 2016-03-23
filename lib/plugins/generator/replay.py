# TODO Add timestamp detection for common timestamp format

from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import math
import re
from eventgentoken import Token
from eventgenoutput import Output

class ReplayGenerator(GeneratorPlugin):
    queueable = False
    _rpevents = None
    _currentevent = None
    _times = None
    _timeSinceSleep = None
    _lastts = None

    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        self._sample = sample

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'ReplayGenerator', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

        self._currentevent = 0
        self._timeSinceSleep = datetime.timedelta()
        self._times = [ ]

        s = self._sample

        # Load sample from a file, using cache if possible, from superclass GeneratorPlugin
        s.loadSample()
        self._rpevents = s.sampleDict
        self._currentevent = 0

        # 8/18/15 CS Because this is not a queueable plugin, we can in a threadsafe way modify these data structures at init
        # Iterate through events and remove any events which do not match a configured timestamp,
        # log it and then continue on
        for e in self._rpevents:
            try:
                s.getTSFromEvent(e[s.timeField])
            except ValueError:
                self._rpevents = [x for x in self._rpevents if x['_raw'] != e['_raw']]

        # Quick check to see if we're sorted in time order, if not reverse
        if len(self._rpevents) > 1:
            ts1 = s.getTSFromEvent(self._rpevents[0][s.timeField])
            ts2 = s.getTSFromEvent(self._rpevents[1][s.timeField])
            td = ts2 - ts1
            x = 2
            # Make sure we're not all zero
            while td.days == 0 and td.seconds == 0 and td.microseconds == 0 and x < len(self._rpevents):
                ts2 = s.getTSFromEvent(self._rpevents[x][s.timeField])
                td = ts2 - ts1
                x += 1

            self.logger.debug("Testing timestamps ts1: %s ts2: %s" % (ts1.strftime('%Y-%m-%d %H:%M:%S'), ts2.strftime('%Y-%m-%d %H:%M:%S')))

            if td.days < 0:
                self.logger.debug("Timestamp order seems to be reverse chronological, reversing")
                self._rpevents.reverse()

        try:
            self.setupBackfill()
        except ValueError as e:
            self.logger.error("Exception during backfill for sample '%s': '%s'" % (s.name, str(e)))


    def gen(self, count, earliest, latest):
        # 9/8/15 CS Check to make sure we have events to replay
        if len(self._rpevents) == 0:
            # Return insanely large sleep time
            return 10000
            
        # For shortness sake, we're going to call the sample s
        s = self._sample

        logger.debug("Generating sample '%s' in app '%s'" % (s.name, s.app))
        startTime = datetime.datetime.now()

        # If we are replaying then we need to set the current sampleLines to the event
        # we're currently on
        self.sampleDict = [ self._rpevents[self._currentevent] ]

        # 9/2/2015 Commenting out, can't find a use for this anymore.
        # self.setOutputMetadata(self.sampleDict[0])

        logger.debugv("Finding timestamp to compute interval for events")
        if self._lastts == None:
            self._lastts = s.getTSFromEvent(self._rpevents[self._currentevent][s.timeField])
        if (self._currentevent+1) < len(self._rpevents):
            nextts = s.getTSFromEvent(self._rpevents[self._currentevent+1][s.timeField])
        else:
            logger.debugv("At end of _rpevents")
            # At the end of the buffer, we sould wait the average amount of time at the end 
            # return 0
            try:
                avgtimes = sum(list(self._times)) / len(self._times) / s.timeMultiple
            except ZeroDivisionError:
                avgtimes = 1
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
                event = token.replace(event, et=s.earliestTime(), lt=s.latestTime(), s=s)
                if token.replacementType == 'timestamp' and s.timeField != '_raw':
                    # 9/4/15 CS Found this change from 9/29/14 where I fixed a bug with timestamp
                    # replacement.  Not sure why I set to this value to none other than I would
                    # want to always use the timestamp from the timeField.  Unfortunately 
                    # what happens is that what if we have multiple timestamps configured for
                    # the sample (which happens with autotimestamp feature now) and we set 
                    # this to none and future timestamps don't match.  In this case, I believe
                    # by commenting this out the first timestamp to be replaced for the sample
                    # will win and every other replacement will use that cached time.
                    # s.timestamp = None
                    token.replace(self.sampleDict[x][s.timeField], et=s.earliestTime(), lt=s.latestTime(), s=s)
            if(s.hostToken):
                # clear the host mvhash every time, because we need to re-randomize it
                s.hostToken.mvhash =  {}

            host = self.sampleDict[x]['host']
            if (s.hostToken):
                host = s.hostToken.replace(host, s=s)

            l = [ { '_raw': event,
                    'index': self.sampleDict[x]['index'],
                    'host': host,
                    'hostRegex': s.hostRegex,
                    'source': self.sampleDict[x]['source'],
                    'sourcetype': self.sampleDict[x]['sourcetype'],
                    '_time': int(time.mktime(s.timestamp.timetuple())) } ]

            self._out.bulksend(l)
            s.timestamp = None


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
            logger.debug("Generation of sample '%s' in app '%s' completed in %s seconds.  Sleeping for %f seconds" \
                        % (s.name, s.app, timeDiffFrac, partialInterval) )
            self._timeSinceSleep = datetime.timedelta()

            # Add for average sleep time calculation when we're at the end of the events
            self._times.append(partialInterval)

        self._out.flush(endOfInterval=True)

        return partialInterval



def load():
    return ReplayGenerator