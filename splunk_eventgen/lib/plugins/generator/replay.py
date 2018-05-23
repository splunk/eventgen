# TODO Add timestamp detection for common timestamp format

from __future__ import division
from generatorplugin import GeneratorPlugin
import datetime, time
import re


class ReplayGenerator(GeneratorPlugin):
    queueable = False
    _rpevents = None
    _currentevent = None
    _times = None
    _timeSinceSleep = None
    _lastts = None

    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        self._currentevent = 0
        self._timeSinceSleep = datetime.timedelta()
        self._times = [ ]



    def set_time_and_send(self, rpevent, event_time, earliest, latest):
        # temporary time append
        rpevent['_raw'] = rpevent['_raw'][:-1]
        rpevent['_time'] = (event_time - datetime.datetime(1970,1,1)).total_seconds()

        event = rpevent['_raw']

        # Maintain state for every token in a given event
        # Hash contains keys for each file name which is assigned a list of values
        # picked from a random line in that file
        mvhash = {}

        ## Iterate tokens
        for token in self._sample.tokens:
            token.mvhash = mvhash
            # self.logger.debugv("Replacing token '%s' of type '%s' in event '%s'" % (token.token, token.replacementType, event))
            self.logger.debugv("Sending event to token replacement: Event:{0} Token:{1}".format(event, token))
            if token.replacementType in ['timestamp', 'replaytimestamp'] :
                event = token.replace(event, et=event_time, lt=event_time, s=self._sample)
            else:
                event = token.replace(event, s=self._sample)
        self.logger.debugv("finished replacing token")
        if (self._sample.hostToken):
            # clear the host mvhash every time, because we need to re-randomize it
            self._sample.hostToken.mvhash = {}

        host = rpevent['host']
        if (self._sample.hostToken):
            rpevent['host'] = self._sample.hostToken.replace(host, s=self._sample)

        rpevent['_raw'] = event
        self._out.bulksend([rpevent])

    def gen(self, count, earliest, latest, samplename=None):
        # 9/8/15 CS Check to make sure we have events to replay
        self._sample.loadSample()
        previous_event = None
        previous_event_timestamp = None
        self.current_time = self._sample.now()

        # If backfill exists, calculate the start of the backfill time relative to the current time.
        # Otherwise, backfill time equals to the current time
        self.backfill_time = self._sample.get_backfill_time(self.current_time)

        for line in self._sample.get_loaded_sample():
            # Add newline to a raw line if necessary
            try:
                if line['_raw'][-1] != '\n':
                    line['_raw'] += '\n'

                index = line.get('index', self._sample.index)
                host = line.get('host', self._sample.host)
                hostRegex = line.get('hostRegex', self._sample.hostRegex)
                source = line.get('source', self._sample.source)
                sourcetype = line.get('sourcetype', self._sample.sourcetype)
                rpevent = {'_raw': line['_raw'], 'index': index, 'host': host, 'hostRegex': hostRegex,
                           'source': source, 'sourcetype': sourcetype}
            except:
                if line[-1] != '\n':
                    line += '\n'

                rpevent = {'_raw': line, 'index': self._sample.index, 'host': self._sample.host,
                           'hostRegex': self._sample.hostRegex,
                           'source': self._sample.source, 'sourcetype': self._sample.sourcetype}

            # If timestamp doesn't exist, the sample file should be fixed to include timestamp for every event.
            try:
                current_event_timestamp = self._sample.getTSFromEvent(line[self._sample.timeField])
            except ValueError as e:
                try:
                    self.logger.debug("Sample timeField {} failed to locate. Trying to locate _time field.".format(self._sample.timeField))
                    current_event_timestamp = self._sample.getTSFromEvent(line["_time"])
                except ValueError as e:
                    self.logger.exception("Extracting timestamp from an event failed.")
                    continue

            # Always flush the first event
            if previous_event is None:
                previous_event = rpevent
                previous_event_timestamp = current_event_timestamp
                self.set_time_and_send(rpevent, self.backfill_time, earliest, latest)
                continue

            # Refer to the last event to calculate the new backfill time
            time_difference = current_event_timestamp - previous_event_timestamp

            if self.backfill_time + time_difference >= self.current_time:
                current_time_diff = self.current_time - self.backfill_time
                sleep_time = time_difference - current_time_diff
                time.sleep(sleep_time.seconds)
                self.current_time += sleep_time
                self.backfill_time = self.current_time
            else:
                self.backfill_time += time_difference
            previous_event = rpevent
            previous_event_timestamp = current_event_timestamp
            self.set_time_and_send(rpevent, self.backfill_time, earliest, latest)

            # TODO: token replacement

        self._out.flush(endOfInterval=True)
        return

        #
        # # For shortness sake, we're going to call the sample s
        # s = self._sample
        #
        # self.logger.debug("Generating sample '%s' in app '%s'" % (s.name, s.app))
        # startTime = datetime.datetime.now()
        #
        # # If we are replaying then we need to set the current sampleLines to the event
        # # we're currently on
        # print self._rpevents
        # self.sampleDict = [ self._rpevents[self._currentevent] ]
        # print self.sampleDict
        #
        # # 9/2/2015 Commenting out, can't find a use for this anymore.
        # # self.setOutputMetadata(self.sampleDict[0])
        #
        # self.logger.debugv("Finding timestamp to compute interval for events")
        # if self._lastts == None:
        #     self._lastts = s.getTSFromEvent(self._rpevents[self._currentevent][s.timeField])
        # if (self._currentevent+1) < len(self._rpevents):
        #     nextts = s.getTSFromEvent(self._rpevents[self._currentevent+1][s.timeField])
        # else:
        #     self.logger.debugv("At end of _rpevents")
        #     # At the end of the buffer, we sould wait the average amount of time at the end
        #     # return 0
        #     try:
        #         avgtimes = sum(list(self._times)) / len(self._times) / s.timeMultiple
        #     except ZeroDivisionError:
        #         avgtimes = 1
        #     interval = datetime.timedelta(seconds=int(math.modf(avgtimes)[1]), microseconds=int(round(math.modf(avgtimes)[0] * 1000000, 0)))
        #     nextts = self._lastts + interval
        #     self.logger.debugv("Setting nextts to '%s' with avgtimes '%d' and interval '%s'" % (nextts, avgtimes, interval))
        #     self._times = [ ]
        #
        # self.logger.debugv('Computing timeDiff nextts: "%s" lastts: "%s"' % (nextts, self._lastts))
        #
        # timeDiff = nextts - self._lastts
        # if timeDiff.days >= 0 and timeDiff.seconds >= 0 and timeDiff.microseconds >= 0:
        #     partialInterval = float("%d.%06d" % (timeDiff.seconds, timeDiff.microseconds))
        # else:
        #     partialInterval = 0
        #
        # if s.timeMultiple > 0:
        #     partialInterval *= s.timeMultiple
        #
        # self.logger.debugv("Setting partialInterval for replay mode with timeMultiple %s: %s %s" % (s.timeMultiple, timeDiff, partialInterval))
        # self._lastts = nextts
        #
        # for x in range(len(self.sampleDict)):
        #     event = self.sampleDict[x]['_raw']
        #
        #     # Maintain state for every token in a given event
        #     # Hash contains keys for each file name which is assigned a list of values
        #     # picked from a random line in that file
        #     mvhash = { }
        #
        #     ## Iterate tokens
        #     for token in s.tokens:
        #         token.mvhash = mvhash
        #         event = token.replace(event, et=s.earliestTime(), lt=s.latestTime(), s=s)
        #         if token.replacementType == 'timestamp' and s.timeField != '_raw':
        #             # 9/4/15 CS Found this change from 9/29/14 where I fixed a bug with timestamp
        #             # replacement.  Not sure why I set to this value to none other than I would
        #             # want to always use the timestamp from the timeField.  Unfortunately
        #             # what happens is that what if we have multiple timestamps configured for
        #             # the sample (which happens with autotimestamp feature now) and we set
        #             # this to none and future timestamps don't match.  In this case, I believe
        #             # by commenting this out the first timestamp to be replaced for the sample
        #             # will win and every other replacement will use that cached time.
        #             # s.timestamp = None
        #             token.replace(self.sampleDict[x][s.timeField], et=s.earliestTime(), lt=s.latestTime(), s=s)
        #     if(s.hostToken):
        #         # clear the host mvhash every time, because we need to re-randomize it
        #         s.hostToken.mvhash =  {}
        #
        #     host = self.sampleDict[x]['host']
        #     if (s.hostToken):
        #         host = s.hostToken.replace(host, s=s)
        #
        #     l = [ { '_raw': event,
        #             'index': self.sampleDict[x]['index'],
        #             'host': host,
        #             'hostRegex': s.hostRegex,
        #             'source': self.sampleDict[x]['source'],
        #             'sourcetype': self.sampleDict[x]['sourcetype'],
        #             '_time': int(time.mktime(s.timestamp.timetuple())) } ]
        #
        #     self._out.bulksend(l)
        #     s.timestamp = None
        #
        #
        # # If we roll over the max number of lines, roll over the counter and start over
        # if (self._currentevent+1) >= len(self._rpevents):
        #     self.logger.debug("At end of the sample file, starting replay from the top")
        #     self._currentevent = 0
        #     self._lastts = None
        # else:
        #     self._currentevent += 1
        #
        #
        # # Track time we were running and time we need to sleep
        # endTime = datetime.datetime.now()
        # timeDiff = endTime - startTime
        # self._timeSinceSleep += timeDiff
        #
        # if partialInterval > 0:
        #     timeDiffFrac = "%d.%06d" % (self._timeSinceSleep.seconds, self._timeSinceSleep.microseconds)
        #     self.logger.debug("Generation of sample '%s' in app '%s' completed in %s seconds.  Sleeping for %f seconds" \
        #                 % (s.name, s.app, timeDiffFrac, partialInterval) )
        #     self._timeSinceSleep = datetime.timedelta()
        #
        #     # Add for average sleep time calculation when we're at the end of the events
        #     self._times.append(partialInterval)
        #
        # self._out.flush(endOfInterval=True)
        #
        # return partialInterval

def load():
    return ReplayGenerator
