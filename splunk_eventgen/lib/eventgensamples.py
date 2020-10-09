# TODO Move config settings to plugins
import csv
import datetime
import os
import pprint
import re
import sys

import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.timeparser import timeParser


class Sample(object):
    """
    The Sample class is the primary configuration holder for Eventgen.  Contains all of our configuration
    information for any given sample, and is passed to most objects in Eventgen and a copy is maintained
    to give that object access to configuration information.  Read and configured at startup, and each
    object maintains a threadsafe copy of Sample.
    """

    # Required fields for Sample
    name = None
    app = None
    filePath = None

    # Options which are all valid for a sample
    disabled = None
    spoolDir = None
    spoolFile = None
    breaker = None
    sampletype = None
    mode = None
    interval = None
    delay = None
    count = None
    bundlelines = None
    earliest = None
    latest = None
    hourOfDayRate = None
    dayOfWeekRate = None
    randomizeEvents = None
    randomizeCount = None
    outputMode = None
    fileName = None
    fileMaxBytes = None
    fileBackupFiles = None
    splunkHost = None
    splunkPort = None
    splunkMethod = None
    splunkUser = None
    splunkPass = None
    index = None
    source = None
    sourcetype = None
    host = None
    hostRegex = None
    hostToken = None
    tokens = None
    projectID = None
    accessToken = None
    backfill = None
    backfillSearch = None
    backfillSearchUrl = None
    minuteOfHourRate = None
    timeMultiple = None
    debug = None
    timezone = datetime.timedelta(days=1)
    dayOfMonthRate = None
    monthOfYearRate = None
    sessionKey = None
    splunkUrl = None
    generator = None
    rater = None
    timeField = None
    timestamp = None
    sampleDir = None
    backfillts = None
    backfilldone = None
    stopping = False
    maxIntervalsBeforeFlush = None
    maxQueueLength = None
    end = None
    queueable = None
    autotimestamp = None
    extendIndexes = None

    # Internal fields
    sampleLines = None
    sampleDict = None
    splunkEmbedded = False
    _lockedSettings = None
    _priority = None
    _origName = None
    _lastts = None
    _earliestParsed = None
    _latestParsed = None

    def __init__(self, name):
        self.name = name
        self.tokens = []
        self._lockedSettings = []
        self.index_list = []
        self.backfilldone = False

    def updateConfig(self, config):
        self.config = config

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this sample"""
        filter_list = ["sampleLines", "sampleDict"]
        temp = dict(
            [
                (key, value)
                for (key, value) in self.__dict__.items()
                if key not in filter_list
            ]
        )
        return pprint.pformat(temp)

    def __repr__(self):
        return self.__str__()

    # Replaces $SPLUNK_HOME w/ correct pathing
    def pathParser(self, path):
        greatgreatgrandparentdir = os.path.dirname(
            os.path.dirname(self.config.grandparentdir)
        )
        sharedStorage = [
            "$SPLUNK_HOME/etc/apps",
            "$SPLUNK_HOME/etc/users/",
            "$SPLUNK_HOME/var/run/splunk",
        ]

        # Replace windows os.sep w/ nix os.sep
        path = path.replace("\\", "/")
        # Normalize path to os.sep
        path = os.path.normpath(path)

        # Iterate special paths
        for x in range(0, len(sharedStorage)):
            sharedPath = os.path.normpath(sharedStorage[x])

            if path.startswith(sharedPath):
                path.replace("$SPLUNK_HOME", greatgreatgrandparentdir)
                break

        # Split path
        path = path.split(os.sep)

        # Iterate path segments
        for x in range(0, len(path)):
            segment = path[x].lstrip("$")
            # If segement is an environment variable then replace
            if segment in os.environ:
                path[x] = os.environ[segment]

        # Join path
        path = os.sep.join(path)

        return path

    # 9/2/15 Adding ability to pass in a token rather than using the tokens from the sample
    def getTSFromEvent(self, event, passed_token=None):
        currentTime = None
        formats = []
        # JB: 2012/11/20 - Can we optimize this by only testing tokens of type = *timestamp?
        # JB: 2012/11/20 - Alternatively, documentation should suggest putting timestamp as token.0.
        if passed_token is not None:
            tokens = [passed_token]
        else:
            tokens = self.tokens
        for token in tokens:
            try:
                formats.append(token.token)
                # logger.debug("Searching for token '%s' in event '%s'" % (token.token, event))
                results = token._search(event)
                if results:
                    timeFormat = token.replacement
                    group = 0 if len(results.groups()) == 0 else 1
                    timeString = results.group(group)
                    # logger.debug("Testing '%s' as a time string against '%s'" % (timeString, timeFormat))
                    if timeFormat == "%s":
                        ts = (
                            float(timeString)
                            if len(timeString) < 10
                            else float(timeString) / (10 ** (len(timeString) - 10))
                        )
                        # logger.debug("Getting time for timestamp '%s'" % ts)
                        currentTime = datetime.datetime.fromtimestamp(ts)
                    else:
                        # logger.debug("Getting time for timeFormat '%s' and timeString '%s'" %
                        #                   (timeFormat, timeString))
                        # Working around Python bug with a non thread-safe strptime. Randomly get AttributeError
                        # when calling strptime, so if we get that, try again
                        while currentTime is None:
                            try:
                                # Checking for timezone adjustment
                                if timeString[-5] == "+":
                                    timeString = timeString[:-5]
                                currentTime = datetime.datetime.strptime(
                                    timeString, timeFormat
                                )
                            except AttributeError:
                                pass
                    logger.debug(
                        "Match '%s' Format '%s' result: '%s'"
                        % (timeString, timeFormat, currentTime)
                    )
                    if type(currentTime) == datetime.datetime:
                        break
            except ValueError:
                logger.warning(
                    "Match found ('%s') but time parse failed. Timeformat '%s' Event '%s'"
                    % (timeString, timeFormat, event)
                )
        if type(currentTime) != datetime.datetime:
            # Total fail
            if (
                passed_token is None
            ):  # If we're running for autotimestamp don't log error
                logger.warning(
                    "Can't find a timestamp (using patterns '%s') in this event: '%s'."
                    % (formats, event)
                )
            raise ValueError(
                "Can't find a timestamp (using patterns '%s') in this event: '%s'."
                % (formats, event)
            )
        # Check to make sure we parsed a year
        if currentTime.year == 1900:
            currentTime = currentTime.replace(year=self.now().year)
        # 11/3/14 CS So, this is breaking replay mode, and getTSFromEvent is only used by replay mode
        #            but I don't remember why I added these two lines of code so it might create a regression.
        #            Found the change on 6/14/14 but no comments as to why I added these two lines.
        # if self.timestamp == None:
        #     self.timestamp = currentTime
        return currentTime

    def saveState(self):
        """Saves state of all integer IDs of this sample to a file so when we restart we'll pick them up"""
        for token in self.tokens:
            if token.replacementType == "integerid":
                stateFile = open(
                    os.path.join(
                        self.sampleDir,
                        "state." + six.moves.urllib.request.pathname2url(token.token),
                    ),
                    "w",
                )
                stateFile.write(token.replacement)
                stateFile.close()

    def now(self, utcnow=False, realnow=False):
        # logger.info("Getting time (timezone %s)" % (self.timezone))
        if not self.backfilldone and self.backfillts is not None and not realnow:
            return self.backfillts
        elif self.timezone.days > 0:
            return datetime.datetime.now()
        else:
            return datetime.datetime.utcnow() + self.timezone

    def get_backfill_time(self, current_time):
        if not current_time:
            current_time = self.now()
        if not self.backfill:
            return current_time
        else:
            if self.backfill[0] == "-":
                backfill_time = self.backfill[1:-1]
                time_unit = self.backfill[-1]
                if self.backfill[-2:] == "ms":
                    time_unit = "ms"
                    backfill_time = self.backfill[1:-2]
                return self.get_time_difference(
                    current_time=current_time,
                    different_time=backfill_time,
                    sign="-",
                    time_unit=time_unit,
                )
            else:
                logger.error("Backfill time is not in the past.")
        return current_time

    def get_time_difference(
        self, current_time, different_time, sign="-", time_unit="ms"
    ):
        if time_unit == "ms":
            return current_time + (
                int(sign + "1") * datetime.timedelta(milliseconds=int(different_time))
            )
        elif time_unit == "s":
            return current_time + (
                int(sign + "1") * datetime.timedelta(seconds=int(different_time))
            )
        elif time_unit == "m":
            return current_time + (
                int(sign + "1") * datetime.timedelta(minutes=int(different_time))
            )
        elif time_unit == "h":
            return current_time + (
                int(sign + "1") * datetime.timedelta(hours=int(different_time))
            )
        elif time_unit == "d":
            return current_time + (
                int(sign + "1") * datetime.timedelta(days=int(different_time))
            )

    def earliestTime(self):
        # First optimization, we need only store earliest and latest
        # as an offset of now if they're relative times
        if self._earliestParsed is not None:
            earliestTime = self.now() - self._earliestParsed
            logger.debug("Using cached earliest time: %s" % earliestTime)
        else:
            if (
                self.earliest.strip()[0:1] == "+"
                or self.earliest.strip()[0:1] == "-"
                or self.earliest == "now"
            ):
                tempearliest = timeParser(self.earliest, timezone=self.timezone)
                temptd = self.now(realnow=True) - tempearliest
                self._earliestParsed = datetime.timedelta(
                    days=temptd.days, seconds=temptd.seconds
                )
                earliestTime = self.now() - self._earliestParsed
                logger.debug(
                    "Calulating earliestParsed as '%s' with earliestTime as '%s' and self.sample.earliest as '%s'"
                    % (self._earliestParsed, earliestTime, tempearliest)
                )
            else:
                earliestTime = timeParser(self.earliest, timezone=self.timezone)
                logger.debug("earliestTime as absolute time '%s'" % earliestTime)
        return earliestTime

    def latestTime(self):
        if self._latestParsed is not None:
            latestTime = self.now() - self._latestParsed
            logger.debug("Using cached latestTime: %s" % latestTime)
        else:
            if (
                self.latest.strip()[0:1] == "+"
                or self.latest.strip()[0:1] == "-"
                or self.latest == "now"
            ):
                templatest = timeParser(self.latest, timezone=self.timezone)
                temptd = self.now(realnow=True) - templatest
                self._latestParsed = datetime.timedelta(
                    days=temptd.days, seconds=temptd.seconds
                )
                latestTime = self.now() - self._latestParsed
                logger.debug(
                    "Calulating latestParsed as '%s' with latestTime as '%s' and self.sample.latest as '%s'"
                    % (self._latestParsed, latestTime, templatest)
                )
            else:
                latestTime = timeParser(self.latest, timezone=self.timezone)
                logger.debug("latstTime as absolute time '%s'" % latestTime)
        return latestTime

    def utcnow(self):
        return self.now(utcnow=True)

    def processSampleLine(self, filehandler):
        """
        Due to a change in python3, utf-8 is now the default trying to read a file.  To get around this we need the
        process loop outside of the filehandler.
        :param filehandler:
        :return:
        """
        sampleLines = []
        if self.breaker == self.config.breaker:
            logger.debug("Reading raw sample '%s' in app '%s'" % (self.name, self.app))
            sampleLines = filehandler.readlines()
        # 1/5/14 CS Moving to using only sampleDict and doing the breaking up into events at load time
        # instead of on every generation
        else:
            logger.debug(
                "Non-default breaker '%s' detected for sample '%s' in app '%s'"
                % (self.breaker, self.name, self.app)
            )
            sampleData = filehandler.read()
            logger.debug(
                "Filling array for sample '%s' in app '%s'; sampleData=%s, breaker=%s"
                % (self.name, self.app, len(sampleData), self.breaker)
            )
            try:
                breakerRE = re.compile(self.breaker, re.M)
            except:
                logger.error(
                    "Line breaker '%s' for sample '%s' in app '%s'"
                    " could not be compiled; using default breaker",
                    self.breaker,
                    self.name,
                    self.app,
                )
                self.breaker = self.config.breaker

            # Loop through data, finding matches of the regular expression and breaking them up into
            # "lines".  Each match includes the breaker itself.
            extractpos = 0
            searchpos = 0
            breakerMatch = breakerRE.search(sampleData, searchpos)
            while breakerMatch:
                logger.debug(
                    "Breaker found at: %d, %d"
                    % (breakerMatch.span()[0], breakerMatch.span()[1])
                )
                # Ignore matches at the beginning of the file
                if breakerMatch.span()[0] != 0:
                    sampleLines.append(sampleData[extractpos : breakerMatch.span()[0]])
                    extractpos = breakerMatch.span()[0]
                searchpos = breakerMatch.span()[1]
                breakerMatch = breakerRE.search(sampleData, searchpos)
            sampleLines.append(sampleData[extractpos:])
        return sampleLines

    def loadSample(self):
        """
        Load sample from disk into self._sample.sampleLines and self._sample.sampleDict, using cached copy if possible
        """
        if self.sampletype == "raw":
            # 5/27/12 CS Added caching of the sample file
            if self.sampleDict is None:
                self.sampleLines = []
                try:
                    with open(self.filePath, "r") as fh:
                        self.sampleLines = self.processSampleLine(fh)
                except UnicodeDecodeError:
                    # incase you can't read it in the default encoding, change over to latin-1
                    with open(self.filePath, "r", encoding="latin-1") as fh:
                        self.sampleLines = self.processSampleLine(fh)
                self.sampleDict = []
                for line in self.sampleLines:
                    if line == "\n":
                        continue
                    if line and line[-1] != "\n":
                        line = line + "\n"
                    self.sampleDict.append(
                        {
                            "_raw": line,
                            "index": self.index,
                            "host": self.host,
                            "source": self.source,
                            "sourcetype": self.sourcetype,
                        }
                    )
                logger.debug(
                    "Finished creating sampleDict & sampleLines.  Len samplesLines: %d Len sampleDict: %d"
                    % (len(self.sampleLines), len(self.sampleDict))
                )
        elif self.sampletype == "csv":
            if self.sampleDict is None:
                with open(self.filePath, "r") as fh:
                    logger.debug(
                        "Reading csv sample '%s' in app '%s'" % (self.name, self.app)
                    )
                    self.sampleDict = []
                    self.sampleLines = []
                    # Fix to load large csv files, work with python 2.5 onwards
                    csv.field_size_limit(sys.maxsize)
                    csvReader = csv.DictReader(fh)
                    for line in csvReader:
                        if "_raw" in line:
                            # Use conf-defined values for these params instead of sample-defined ones
                            current_line_keys = list(line.keys())
                            if "host" not in current_line_keys:
                                line["host"] = self.host
                            if "hostRegex" not in current_line_keys:
                                line["hostRegex"] = self.hostRegex
                            if "source" not in current_line_keys:
                                line["source"] = self.source
                            if "sourcetype" not in current_line_keys:
                                line["sourcetype"] = self.sourcetype
                            if "index" not in current_line_keys:
                                line["index"] = self.index
                            self.sampleDict.append(line)
                            self.sampleLines.append(line["_raw"])
                        else:
                            logger.error(
                                "Missing _raw in line '%s'" % pprint.pformat(line)
                            )

                logger.debug(
                    "Finished creating sampleDict & sampleLines for sample '%s'.  Len sampleDict: %d"
                    % (self.name, len(self.sampleDict))
                )

                for i in range(0, len(self.sampleDict)):
                    if (
                        len(self.sampleDict[i]["_raw"]) < 1
                        or self.sampleDict[i]["_raw"][-1] != "\n"
                    ):
                        self.sampleDict[i]["_raw"] += "\n"
        if self.extendIndexes:
            try:
                for index_item in self.extendIndexes.split(","):
                    index_item = index_item.strip()
                    if ":" in index_item:
                        extend_indexes_count = int(index_item.split(":")[-1])
                        extend_indexes_prefix = index_item.split(":")[0] + "{}"
                        self.index_list.extend(
                            [
                                extend_indexes_prefix.format(_i)
                                for _i in range(extend_indexes_count)
                            ]
                        )
                    elif len(index_item):
                        self.index_list.append(index_item)
            except Exception:
                logger.error(
                    "Failed to parse extendIndexes, using index={} now.".format(
                        self.index
                    )
                )
                self.index_list = []
            finally:
                # only read the extendIndexes configure once.
                self.extendIndexes = None

    def get_loaded_sample(self):
        if self.sampletype == "csv":
            self.loadSample()
            return self.sampleDict
        else:
            self.loadSample()
            return self.sampleLines
