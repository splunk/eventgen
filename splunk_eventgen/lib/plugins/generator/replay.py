# TODO Add timestamp detection for common timestamp format
import datetime
import time

from splunk_eventgen.lib.generatorplugin import GeneratorPlugin
from splunk_eventgen.lib.logging_config import logger


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
        self.replayLock = None

    def updateConfig(self, config, outqueue, replayLock=None):
        super(ReplayGenerator, self).updateConfig(config, outqueue)
        self.replayLock = replayLock

    def set_time_and_tokens(self, replayed_event, event_time, earliest, latest):
        send_event = {}
        # temporary time append
        send_event["_raw"] = replayed_event["_raw"][:-1]
        send_event["host"] = replayed_event["host"]
        send_event["source"] = replayed_event["source"]
        send_event["sourcetype"] = replayed_event["sourcetype"]
        send_event["index"] = replayed_event["index"]
        send_event["_time"] = (
            event_time - datetime.datetime(1970, 1, 1)
        ).total_seconds()

        # Maintain state for every token in a given event
        # Hash contains keys for each file name which is assigned a list of values
        # picked from a random line in that file
        mvhash = dict()

        # Iterate tokens
        eventraw = replayed_event["_raw"]
        for token in self._sample.tokens:
            token.mvhash = mvhash
            if token.replacementType in ["timestamp", "replaytimestamp"]:
                eventraw = token.replace(
                    eventraw, et=event_time, lt=event_time, s=self._sample
                )
            else:
                eventraw = token.replace(eventraw, s=self._sample)
        if self._sample.hostToken:
            # clear the host mvhash every time, because we need to re-randomize it
            self._sample.hostToken.mvhash = {}

        host = replayed_event["host"]
        if self._sample.hostToken:
            send_event["host"] = self._sample.hostToken.replace(host, s=self._sample)

        send_event["_raw"] = eventraw
        return send_event

    def load_sample_file(self):
        line_list = []
        for line in self._sample.get_loaded_sample():
            # Add newline to a raw line if necessary
            try:
                if line["_raw"][-1] != "\n":
                    line["_raw"] += "\n"
                current_event_timestamp = False
                index = line.get("index", self._sample.index)
                host = line.get("host", self._sample.host)
                hostRegex = line.get("hostRegex", self._sample.hostRegex)
                source = line.get("source", self._sample.source)
                sourcetype = line.get("sourcetype", self._sample.sourcetype)
                rpevent = {
                    "_raw": line["_raw"],
                    "index": index,
                    "host": host,
                    "hostRegex": hostRegex,
                    "source": source,
                    "sourcetype": sourcetype,
                }
            except:
                if line[-1] != "\n":
                    line += "\n"

                rpevent = {
                    "_raw": line,
                    "index": self._sample.index,
                    "host": self._sample.host,
                    "hostRegex": self._sample.hostRegex,
                    "source": self._sample.source,
                    "sourcetype": self._sample.sourcetype,
                }
            try:
                current_event_timestamp = self._sample.getTSFromEvent(
                    rpevent[self._sample.timeField]
                )
                rpevent["base_time"] = current_event_timestamp
            except Exception:
                try:
                    current_event_timestamp = self._sample.getTSFromEvent(
                        line[self._sample.timeField]
                    )
                    rpevent["base_time"] = current_event_timestamp
                except Exception:
                    try:
                        logger.error(
                            "Sample timeField {} failed to locate. Trying to locate _time field.".format(
                                self._sample.timeField
                            )
                        )
                        current_event_timestamp = self._sample.getTSFromEvent(
                            line["_time"]
                        )
                    except Exception:
                        logger.exception("Extracting timestamp from an event failed.")
                        continue
            line_list.append(rpevent)
        # now interate the list 1 time and figure out the time delta of every event
        current_event = None
        previous_event = None
        for index, line in enumerate(line_list):
            current_event = line
            # if it's the first event, there is no previous event.
            if index == 0:
                previous_event = current_event
            else:
                previous_event = line_list[index - 1]
            # Refer to the last event to calculate the new backfill time
            time_difference = (
                current_event["base_time"] - previous_event["base_time"]
            ) * self._sample.timeMultiple
            current_event["timediff"] = time_difference
        return line_list

    def gen(self, count, earliest, latest, samplename=None):
        # 9/8/15 CS Check to make sure we have events to replay
        self._sample.loadSample()
        self.current_time = self._sample.now()
        line_list = self.load_sample_file()
        # If backfill exists, calculate the start of the backfill time relative to the current time.
        # Otherwise, backfill time equals to the current time
        self.backfill_time = self._sample.get_backfill_time(self.current_time)
        # if we have backfill, replay the events backwards until we hit the backfill
        if self.backfill_time != self.current_time and not self._sample.backfilldone:
            backfill_count_time = self.current_time
            current_backfill_index = len(line_list) - 1
            backfill_events = []
            while backfill_count_time >= self.backfill_time:
                rpevent = line_list[current_backfill_index]
                backfill_count_time = backfill_count_time - rpevent["timediff"]
                backfill_events.append(
                    self.set_time_and_tokens(
                        rpevent, backfill_count_time, earliest, latest
                    )
                )
                current_backfill_index -= 1
                if current_backfill_index < 0:
                    current_backfill_index = len(line_list) - 1
            backfill_events.reverse()
            self._out.bulksend(backfill_events)
            self._sample.backfilldone = True
        previous_event = None
        for index, rpevent in enumerate(line_list):
            if previous_event is None:
                current_event = self.set_time_and_tokens(
                    rpevent, self.backfill_time, earliest, latest
                )
                previous_event = current_event
                previous_event_timediff = rpevent["timediff"]
                self._out.bulksend([current_event])
                continue
            try:
                time.sleep(previous_event_timediff.total_seconds())
            except ValueError:
                logger.error(
                    "Can't sleep for negative time, please make sure your events are in time order."
                    "see line Number{0}".format(index)
                )
                logger.error("Event: {0}".format(rpevent))
                pass
            current_time = datetime.datetime.now()
            previous_event = rpevent
            previous_event_timediff = rpevent["timediff"]
            send_event = self.set_time_and_tokens(
                rpevent, current_time, earliest, latest
            )
            self._out.bulksend([send_event])
        self._out.flush(endOfInterval=True)
        return


def load():
    return ReplayGenerator
