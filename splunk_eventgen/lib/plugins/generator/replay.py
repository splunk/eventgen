# TODO Add timestamp detection for common timestamp format

from __future__ import division

import datetime
import time

from eventgentimestamp import EventgenTimestamp
from generatorplugin import GeneratorPlugin
from logging_config import logger


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
        self._times = []

    def set_time_and_send(self, rpevent, event_time, earliest, latest):
        # temporary time append
        rpevent['_raw'] = rpevent['_raw'][:-1]
        rpevent['_time'] = (event_time - datetime.datetime(1970, 1, 1)).total_seconds()

        event = rpevent['_raw']

        # Maintain state for every token in a given event
        # Hash contains keys for each file name which is assigned a list of values
        # picked from a random line in that file
        mvhash = {}

        # Iterate tokens
        for token in self._sample.tokens:
            token.mvhash = mvhash
            if token.replacementType in ['timestamp', 'replaytimestamp']:
                event = token.replace(event, et=event_time, lt=event_time, s=self._sample)
            else:
                event = token.replace(event, s=self._sample)
        if self._sample.hostToken:
            # clear the host mvhash every time, because we need to re-randomize it
            self._sample.hostToken.mvhash = {}

        host = rpevent['host']
        if self._sample.hostToken:
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

        if not self._sample.backfill or self._sample.backfilldone:
            self.backfill_time = EventgenTimestamp.get_random_timestamp_backfill(
                earliest, latest, self._sample.earliest, self._sample.latest)

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
                rpevent = {
                    '_raw': line['_raw'], 'index': index, 'host': host, 'hostRegex': hostRegex, 'source': source,
                    'sourcetype': sourcetype}
            except:
                if line[-1] != '\n':
                    line += '\n'

                rpevent = {
                    '_raw': line, 'index': self._sample.index, 'host': self._sample.host, 'hostRegex':
                    self._sample.hostRegex, 'source': self._sample.source, 'sourcetype': self._sample.sourcetype}

            # If timestamp doesn't exist, the sample file should be fixed to include timestamp for every event.
            try:
                current_event_timestamp = self._sample.getTSFromEvent(rpevent[self._sample.timeField])
            except Exception:
                try:
                    current_event_timestamp = self._sample.getTSFromEvent(line[self._sample.timeField])
                except Exception:
                    try:
                        logger.error("Sample timeField {} failed to locate. Trying to locate _time field.".format(
                            self._sample.timeField))
                        current_event_timestamp = self._sample.getTSFromEvent(line["_time"])
                    except Exception:
                        logger.exception("Extracting timestamp from an event failed.")
                        continue

            # Always flush the first event
            if previous_event is None:
                previous_event = rpevent
                previous_event_timestamp = current_event_timestamp
                self.set_time_and_send(rpevent, self.backfill_time, earliest, latest)
                continue

            # Refer to the last event to calculate the new backfill time
            time_difference = datetime.timedelta(seconds=(current_event_timestamp - previous_event_timestamp) .total_seconds() * self._sample.timeMultiple)

            if self.backfill_time + time_difference >= self.current_time:
                sleep_time = time_difference - (self.current_time - self.backfill_time)
                if self._sample.backfill and not self._sample.backfilldone:
                    time.sleep(sleep_time.seconds)
                self.current_time += sleep_time
                self.backfill_time = self.current_time
            else:
                self.backfill_time += time_difference
            previous_event = rpevent
            previous_event_timestamp = current_event_timestamp
            self.set_time_and_send(rpevent, self.backfill_time, earliest, latest)

        self._out.flush(endOfInterval=True)
        return


def load():
    return ReplayGenerator
