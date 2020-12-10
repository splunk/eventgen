import datetime
import pprint
import random
import time
from xml.dom import minidom
from xml.parsers.expat import ExpatError

import httplib2
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request

from splunk_eventgen.lib.eventgenoutput import Output
from splunk_eventgen.lib.eventgentimestamp import EventgenTimestamp
from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.timeparser import timeParser


class GeneratorPlugin(object):
    sampleLines = None
    sampleDict = None

    def __init__(self, sample):
        self._sample = sample

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        # temp = dict([(key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def send_events(self, send_objects, startTime):
        """Ready events for output by replacing tokens and updating the output queue"""
        try:
            self._out.bulksend(send_objects)
            self._sample.timestamp = None
        except Exception as e:
            logger.exception("Exception {} happened.".format(type(e)))
            raise e
        try:
            # TODO: Change this logic so that we don't lose all events if an exception is hit (try/except/break?)
            endTime = datetime.datetime.now()
            timeDiff = endTime - startTime
            timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
            logger.debug("Interval complete, flushing feed")
            self._out.flush(endOfInterval=True)
            logger.debug(
                "Generation of sample '%s' in app '%s' completed in %s seconds."
                % (self._sample.name, self._sample.app, timeDiffFrac)
            )
        except Exception as e:
            logger.exception("Exception {} happened.".format(type(e)))
            raise e

    def updateConfig(self, config, outqueue):
        self.config = config
        self.outputQueue = outqueue
        # TODO: Figure out if this maxQueueLength needs to even be set here.  I think this should exist on the output
        # process and the generator shouldn't have anything to do with this.
        self.outputPlugin = self.config.getPlugin(
            "output." + self._sample.outputMode, self._sample
        )
        if self._sample.maxQueueLength == 0:
            self._sample.maxQueueLength = self.outputPlugin.MAXQUEUELENGTH
        # Output = output process, not the plugin.  The plugin is loaded by the output process.
        self._out = Output(self._sample)
        self._out.updateConfig(self.config)
        if self.outputPlugin.useOutputQueue or self.config.useOutputQueue:
            self._out._update_outputqueue(self.outputQueue)

    def updateCounts(self, sample=None, count=None, start_time=None, end_time=None):
        if sample:
            self._sample = sample
        self.count = count
        self.start_time = start_time
        self.end_time = end_time

    def setOutputMetadata(self, event):
        if self._sample.sampletype == "csv" and (
            event["index"] != self._sample.index
            or event["host"] != self._sample.host
            or event["source"] != self._sample.source
            or event["sourcetype"] != self._sample.sourcetype
        ):
            self._sample.index = event["index"]
            self._sample.host = event["host"]
            # Allow randomizing the host:
            if self._sample.hostToken:
                self.host = self._sample.hostToken.replace(self.host)

            self._sample.source = event["source"]
            self._sample.sourcetype = event["sourcetype"]
            logger.debug(
                "Setting CSV parameters. index: '%s' host: '%s' source: '%s' sourcetype: '%s'"
                % (
                    self._sample.index,
                    self._sample.host,
                    self._sample.source,
                    self._sample.sourcetype,
                )
            )

    def setupBackfill(self):
        """
        Called by non-queueable plugins or by the timer to setup backfill times per config or based on a Splunk Search
        """
        s = self._sample

        if s.backfill is not None:
            try:
                s.backfillts = timeParser(s.backfill, timezone=s.timezone)
                logger.info(
                    "Setting up backfill of %s (%s)" % (s.backfill, s.backfillts)
                )
            except Exception as ex:
                logger.error("Failed to parse backfill '%s': %s" % (s.backfill, ex))
                raise

            if s.backfillSearch is not None:
                if s.backfillSearchUrl is None:
                    try:
                        s.backfillSearchUrl = c.getSplunkUrl(s)[0]  # noqa: F821
                    except ValueError:
                        logger.error(
                            "Backfill Search URL not specified for sample '%s', not running backfill search"
                            % s.name
                        )
                if not s.backfillSearch.startswith("search"):
                    s.backfillSearch = "search " + s.backfillSearch
                s.backfillSearch += "| head 1 | table _time"

                if s.backfillSearchUrl is not None:
                    logger.debug(
                        "Searching Splunk URL '%s/services/search/jobs' with search '%s' with sessionKey '%s'"
                        % (s.backfillSearchUrl, s.backfillSearch, s.sessionKey)
                    )

                    results = httplib2.Http(
                        disable_ssl_certificate_validation=True
                    ).request(
                        s.backfillSearchUrl + "/services/search/jobs",
                        "POST",
                        headers={"Authorization": "Splunk %s" % s.sessionKey},
                        body=six.moves.urllib.parse.urlencode(
                            {
                                "search": s.backfillSearch,
                                "earliest_time": s.backfill,
                                "exec_mode": "oneshot",
                            }
                        ),
                    )[
                        1
                    ]
                    try:
                        temptime = (
                            minidom.parseString(results)
                            .getElementsByTagName("text")[0]
                            .childNodes[0]
                            .nodeValue
                        )
                        # logger.debug("Time returned from backfill search: %s" % temptime)
                        # Results returned look like: 2013-01-16T10:59:15.411-08:00
                        # But the offset in time can also be +, so make sure we strip that out first
                        if len(temptime) > 0:
                            if temptime.find("+") > 0:
                                temptime = temptime.split("+")[0]
                            temptime = "-".join(temptime.split("-")[0:3])
                        s.backfillts = datetime.datetime.strptime(
                            temptime, "%Y-%m-%dT%H:%M:%S.%f"
                        )
                        logger.debug(
                            "Backfill search results: '%s' value: '%s' time: '%s'"
                            % (pprint.pformat(results), temptime, s.backfillts)
                        )
                    except (ExpatError, IndexError):
                        pass

        if s.end is not None:
            parsed = False
            try:
                s.end = int(s.end)
                s.endts = None
                parsed = True
            except ValueError:
                logger.debug(
                    "Failed to parse end '%s' for sample '%s', treating as end time"
                    % (s.end, s.name)
                )

            if not parsed:
                try:
                    s.endts = timeParser(s.end, timezone=s.timezone)
                    logger.info("Ending generation at %s (%s)" % (s.end, s.endts))
                except Exception:
                    logger.error(
                        "Failed to parse end '%s' for sample '%s', treating as number of executions"
                        % (s.end, s.name)
                    )
                    raise

    def run(self, output_counter=None):
        if (
            output_counter is not None
            and hasattr(self.config, "outputCounter")
            and self.config.outputCounter
        ):
            # Use output_counter to calculate throughput
            self._out.setOutputCounter(output_counter)
        self.gen(
            count=self.count,
            earliest=self.start_time,
            latest=self.end_time,
            samplename=self._sample.name,
        )
        # TODO: Make this some how handle an output queue and support intervals and a master queue
        # Just double check to see if there's something in queue to flush out at the end of run
        if len(self._out._queue) > 0:
            logger.debug("Queue is not empty, flush out at the end of each run")
            self._out.flush()

    def replace_tokens(self, eventsDict, earliest, latest, ignore_tokens=False):
        """Iterate event tokens and replace them. This will help calculations for event size when tokens are used."""
        eventcount = 0
        send_events = []
        total_count = len(eventsDict)
        index = None
        if total_count > 0:
            index = (
                random.choice(self._sample.index_list)
                if len(self._sample.index_list)
                else eventsDict[0]["index"]
            )
        for targetevent in eventsDict:
            event = targetevent["_raw"]
            # Maintain state for every token in a given event, Hash contains keys for each file name which is
            # assigned a list of values picked from a random line in that file
            mvhash = {}
            host = targetevent["host"]
            if (
                hasattr(self._sample, "sequentialTimestamp")
                and self._sample.sequentialTimestamp
                and self._sample.generator != "perdayvolumegenerator"
            ):
                pivot_timestamp = EventgenTimestamp.get_sequential_timestamp(
                    earliest, latest, eventcount, total_count
                )
            else:
                pivot_timestamp = EventgenTimestamp.get_random_timestamp(
                    earliest, latest
                )
            # Iterate tokens
            if not ignore_tokens:
                for token in self._sample.tokens:
                    token.mvhash = mvhash
                    event = token.replace(
                        event,
                        et=earliest,
                        lt=latest,
                        s=self._sample,
                        pivot_timestamp=pivot_timestamp,
                    )
                    if (
                        token.replacementType == "timestamp"
                        and self._sample.timeField != "_raw"
                    ):
                        self._sample.timestamp = None
                        token.replace(
                            targetevent[self._sample.timeField],
                            et=self._sample.earliestTime(),
                            lt=self._sample.latestTime(),
                            s=self._sample,
                            pivot_timestamp=pivot_timestamp,
                        )
                if self._sample.hostToken:
                    # clear the host mvhash every time, because we need to re-randomize it
                    self._sample.hostToken.mvhash = {}
                if self._sample.hostToken:
                    host = self._sample.hostToken.replace(host, s=self._sample)
            try:
                time_val = int(time.mktime(pivot_timestamp.timetuple()))
            except Exception:
                time_val = int(time.mktime(self._sample.now().timetuple()))
            temp_event = {
                "_raw": event,
                "index": index,
                "host": host,
                "hostRegex": self._sample.hostRegex,
                "source": targetevent["source"],
                "sourcetype": targetevent["sourcetype"],
                "_time": time_val,
            }
            send_events.append(temp_event)
        return send_events


def load():
    return GeneratorPlugin
