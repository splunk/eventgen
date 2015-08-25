# TODO Move config settings to plugins

from __future__ import division, with_statement
import os, sys
import logging
import pprint
import random
import datetime
import re
import csv
import json
import copy
from eventgenoutput import Output
from eventgentoken import Token
from timeparser import timeParser, timeDelta2secs
from eventgencounter import Counter

class Sample:
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
    out = None
    timeField = None
    timestamp = None
    sampleDir = None
    backfillts = None
    backfilldone = None
    stopping = False
    maxIntervalsBeforeFlush = None
    maxQueueLength = None
    end = None

    
    # Internal fields
    _sampleLines = None
    sampleLines = None
    _sampleDict = None
    sampleDict = None
    _lockedSettings = None
    _priority = None
    _origName = None
    _lastts = None
    _timeSinceSleep = None
    _earliestParsed = None
    _latestParsed = None
    
    def __init__(self, name):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'Sample', 'sample': name})
        globals()['logger'] = adapter
        
        self.name = name
        self.tokens = [ ]
        self._lockedSettings = [ ]

        self._currentevent = 0
        self._rpevents = None
        self.backfilldone = False
        self._timeSinceSleep = datetime.timedelta()
        
        # Import config
        from eventgenconfig import Config
        globals()['c'] = Config()
        
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this sample"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c' ])
        return pprint.pformat(temp)
        
    def __repr__(self):
        return self.__str__()
        
    ## Replaces $SPLUNK_HOME w/ correct pathing
    def pathParser(self, path):
        greatgreatgrandparentdir = os.path.dirname(os.path.dirname(c.grandparentdir)) 
        sharedStorage = ['$SPLUNK_HOME/etc/apps', '$SPLUNK_HOME/etc/users/', '$SPLUNK_HOME/var/run/splunk']

        ## Replace windows os.sep w/ nix os.sep
        path = path.replace('\\', '/')
        ## Normalize path to os.sep
        path = os.path.normpath(path)

        ## Iterate special paths
        for x in range(0, len(sharedStorage)):
            sharedPath = os.path.normpath(sharedStorage[x])

            if path.startswith(sharedPath):
                path.replace('$SPLUNK_HOME', greatgreatgrandparentdir)
                break

        ## Split path
        path = path.split(os.sep)

        ## Iterate path segments
        for x in range(0, len(path)):
            segment = path[x].lstrip('$')
            ## If segement is an environment variable then replace
            if os.environ.has_key(segment):
                path[x] = os.environ[segment]

        ## Join path
        path = os.sep.join(path)

        return path

    def getTSFromEvent(self, event):
        currentTime = None
        formats = [ ]
        # JB: 2012/11/20 - Can we optimize this by only testing tokens of type = *timestamp?
        # JB: 2012/11/20 - Alternatively, documentation should suggest putting timestamp as token.0.
        for token in self.tokens:
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
                        ts = float(timeString) if len(timeString) < 10 else float(timeString) / (10**(len(timeString)-10))
                        logger.debugv("Getting time for timestamp '%s'" % ts)
                        currentTime = datetime.datetime.fromtimestamp(ts)
                    else:
                        logger.debugv("Getting time for timeFormat '%s' and timeString '%s'" % (timeFormat, timeString))
                        # Working around Python bug with a non thread-safe strptime.  Randomly get AttributeError
                        # when calling strptime, so if we get that, try again
                        while currentTime == None:
                            try:
                                currentTime = datetime.datetime.strptime(timeString, timeFormat)
                            except AttributeError:
                                pass
                    logger.debugv("Match '%s' Format '%s' result: '%s'" % (timeString, timeFormat, currentTime))
                    if type(currentTime) == datetime.datetime:
                        break
            except ValueError:
                logger.debug("Match found ('%s') but time parse failed. Timeformat '%s' Event '%s'" % (timeString, timeFormat, event))
        if type(currentTime) != datetime.datetime:
            # Total fail
            logger.error("Can't find a timestamp (using patterns '%s') in this event: '%s'." % (formats, event))
            raise ValueError("Can't find a timestamp (using patterns '%s') in this event: '%s'." % (formats, event))
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
            if token.replacementType == 'integerid':
                stateFile = open(os.path.join(c.sampleDir, 'state.'+urllib.pathname2url(token.token)), 'w')
                stateFile.write(token.replacement)
                stateFile.close()

    def now(self, utcnow=False, realnow=False):
        # logger.info("Getting time (timezone %s)" % (self.timezone))
        if not self.backfilldone and not self.backfillts == None and not realnow:
            return self.backfillts
        elif self.timezone.days > 0:
            return datetime.datetime.now()
        else:
            return datetime.datetime.utcnow() + self.timezone

    def earliestTime(self):
        # First optimization, we need only store earliest and latest
        # as an offset of now if they're relative times
        if self._earliestParsed != None:
            earliestTime = self.now() - self._earliestParsed
            logger.debugv("Using cached earliest time: %s" % earliestTime)
        else:
            if self.earliest.strip()[0:1] == '+' or \
                    self.earliest.strip()[0:1] == '-' or \
                    self.earliest == 'now':
                tempearliest = timeParser(self.earliest, timezone=self.timezone)
                temptd = self.now(realnow=True) - tempearliest
                self._earliestParsed = datetime.timedelta(days=temptd.days, seconds=temptd.seconds)
                earliestTime = self.now() - self._earliestParsed
                logger.debugv("Calulating earliestParsed as '%s' with earliestTime as '%s' and self.sample.earliest as '%s'" % (self._earliestParsed, earliestTime, tempearliest))
            else:
                earliestTime = timeParser(self.earliest, timezone=self.timezone)
                logger.debugv("earliestTime as absolute time '%s'" % earliestTime)

        return earliestTime


    def latestTime(self):
        if self._latestParsed != None:
            latestTime = self.now() - self._latestParsed
            logger.debugv("Using cached latestTime: %s" % latestTime)
        else:
            if self.latest.strip()[0:1] == '+' or \
                    self.latest.strip()[0:1] == '-' or \
                    self.latest == 'now':
                templatest = timeParser(self.latest, timezone=self.timezone)
                temptd = self.now(realnow=True) - templatest
                self._latestParsed = datetime.timedelta(days=temptd.days, seconds=temptd.seconds)
                latestTime = self.now() - self._latestParsed
                logger.debugv("Calulating latestParsed as '%s' with latestTime as '%s' and self.sample.latest as '%s'" % (self._latestParsed, latestTime, templatest))
            else:
                latestTime = timeParser(self.latest, timezone=self.timezone)
                logger.debugv("latstTime as absolute time '%s'" % latestTime)

        return latestTime

    def utcnow(self):
        return self.now(utcnow=True)