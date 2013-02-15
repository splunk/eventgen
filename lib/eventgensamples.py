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
from timeparser import timeParser, timeDelta2secs
import httplib2, urllib
from xml.dom import minidom
from xml.parsers.expat import ExpatError

class Sample:
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
    
    # Internal fields
    _c = None
    _out = None
    _sampleLines = None
    _sampleDict = None
    _lockedSettings = None
    _priority = None
    _origName = None
    _lastts = None
    _backfillts = None
    _origEarliest = None
    _origLatest = None
    _timeSinceSleep = None
    
    def __init__(self, name):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
        
        self.name = name
        self.tokens = [ ]
        self._lockedSettings = [ ]

        self._currentevent = 0
        self._rpevents = None
        self._backfilldone = False
        self._timeSinceSleep = datetime.timedelta()
        
        # Import config
        from eventgenconfig import Config
        self._c = Config()
        
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this sample"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c' ])
        return pprint.pformat(temp)
        
    def __repr__(self):
        return self.__str__()
    
    def gen(self):
        logger.debug("Generating sample '%s' in app '%s'" % (self.name, self.app))
        startTime = datetime.datetime.now()
        
        # If this is the first time we're generating, setup out
        if self._out == None:
            logger.debug("Setting up Output class for sample '%s' in app '%s'" % (self.name, self.app))
            self._out = Output(self)
            if self.backfillSearchUrl == None:
                self.backfillSearchUrl = self._out._splunkUrl

        # Setup initial backfillts
        if self._backfillts == None and self.backfill != None and not self._backfilldone:
            try:
                self._backfillts = timeParser(self.backfill, timezone=self.timezone)
                logger.info("Setting up backfill of %s (%s)" % (self.backfill,self._backfillts))
            except Exception as ex:
                logger.error("Failed to parse backfill '%s': %s" % (self.backfill, ex))
                raise

            self._origEarliest = self.earliest
            self._origLatest = self.latest
            if self._out._outputMode == "splunkstream" and self.backfillSearch != None:
                if not self.backfillSearch.startswith('search'):
                    self.backfillSearch = 'search ' + self.backfillSearch
                self.backfillSearch += '| head 1 | table _time'

                logger.debug("Searching Splunk URL '%s/services/search/jobs' with search '%s' with sessionKey '%s'" % (self.backfillSearchUrl, self.backfillSearch, self._out._c.sessionKey))

                results = httplib2.Http(disable_ssl_certificate_validation=True).request(\
                            self.backfillSearchUrl + '/services/search/jobs',
                            'POST', headers={'Authorization': 'Splunk %s' % self._out._c.sessionKey}, \
                            body=urllib.urlencode({'search': self.backfillSearch,
                                                    'earliest_time': self.backfill,
                                                    'exec_mode': 'oneshot'}))[1]
                try:
                    temptime = minidom.parseString(results).getElementsByTagName('text')[0].childNodes[0].nodeValue
                    # logger.debug("Time returned from backfill search: %s" % temptime)
                    # Results returned look like: 2013-01-16T10:59:15.411-08:00
                    # But the offset in time can also be +, so make sure we strip that out first
                    if len(temptime) > 0:
                        if temptime.find('+') > 0:
                            temptime = temptime.split('+')[0]
                        temptime = '-'.join(temptime.split('-')[0:3])
                    self._backfillts = datetime.datetime.strptime(temptime, '%Y-%m-%dT%H:%M:%S.%f')
                    logger.debug("Backfill search results: '%s' value: '%s' time: '%s'" % (pprint.pformat(results), temptime, self._backfillts))
                except (ExpatError, IndexError): 
                    pass

        # Override earliest and latest during backfill until we're at current time
        if self.backfill != None and not self._backfilldone:
            if self._backfillts >= self.now():
                logger.info("Backfill complete")
                self._backfilldone = True
                self.earliest = self._origEarliest
                self.latest = self._origLatest
            else:
                logger.debug("Still backfilling for sample '%s'.  Currently at %s" % (self.name, self._backfillts))
                self.earliest = datetime.datetime.strftime((self._backfillts - datetime.timedelta(seconds=self.interval)), \
                                                            "%Y-%m-%d %H:%M:%S.%f")
                self.latest = datetime.datetime.strftime(self._backfillts, "%Y-%m-%d %H:%M:%S.%f")
                # if not self.mode == 'replay':
                #     self._backfillts += datetime.timedelta(seconds=self.interval)

        
        logger.debug("Opening sample '%s' in app '%s'" % (self.name, self.app) )
        sampleFH = open(self.filePath, 'rU')
        if self.sampletype == 'raw':
            # 5/27/12 CS Added caching of the sample file
            if self._sampleLines == None:
                logger.debug("Reading raw sample '%s' in app '%s'" % (self.name, self.app))
                sampleLines = sampleFH.readlines()
                self._sampleLines = sampleLines
            else:
                sampleLines = self._sampleLines
        elif self.sampletype == 'csv':
            logger.debug("Reading csv sample '%s' in app '%s'" % (self.name, self.app))
            if self._sampleLines == None:
                logger.debug("Reading csv sample '%s' in app '%s'" % (self.name, self.app))
                sampleDict = [ ]
                sampleLines = [ ]
                csvReader = csv.DictReader(sampleFH)
                for line in csvReader:
                    sampleDict.append(line)
                    sampleLines.append(line['_raw'].decode('string_escape'))
                self._sampleDict = copy.deepcopy(sampleDict)
                self._sampleLines = copy.deepcopy(sampleLines)
            else:
                # If we're set to bundlelines, we'll modify sampleLines regularly.
                # Since lists in python are referenced rather than copied, we
                # need to make a fresh copy every time if we're bundlelines.
                # If not, just used the cached copy, we won't mess with it.
                if not self.bundlelines:
                    sampleDict = self._sampleDict
                    sampleLines = self._sampleLines
                else:
                    sampleDict = copy.deepcopy(self._sampleDict)
                    sampleLines = copy.deepcopy(self._sampleLines)


        # Check to see if this is the first time we've run, or if we're at the end of the file
        # and we're running replay.  If so, we need to parse the whole file and/or setup our counters
        if self._rpevents == None and self.mode == 'replay':
            if self.sampletype == 'csv':
                self._rpevents = sampleDict
            else:
                if self.breaker != self._c.breaker:
                    self._rpevents = []
                    lines = '\n'.join(sampleLines)
                    breaker = re.search(self.breaker, lines)
                    currentchar = 0
                    while breaker:
                        self._rpevents.append(lines[currentchar:breaker.start(0)])
                        lines = lines[breaker.end(0):]
                        currentchar += breaker.start(0)
                        breaker = re.search(self.breaker, lines)
                else:
                    self._rpevents = sampleLines
            self._currentevent = 0
        
        # If we are replaying then we need to set the current sampleLines to the event
        # we're currently on
        if self.mode == 'replay':
            if self.sampletype == 'csv':
                sampleDict = [ self._rpevents[self._currentevent] ]
                sampleLines = [ self._rpevents[self._currentevent]['_raw'].decode('string_escape') ]
            else:
                sampleLines = [ self._rpevents[self._currentevent] ]
            self._currentevent += 1
            # If we roll over the max number of lines, roll over the counter and start over
            if self._currentevent >= len(self._rpevents):
                logger.debug("At end of the sample file, starting replay from the top")
                self._currentevent = 0
                self._lastts = None

        # Ensure all lines have a newline
        for i in xrange(0, len(sampleLines)):
            if sampleLines[i][-1] != '\n':
                sampleLines[i] += '\n'

        # If we've set bundlelines, then we want count copies of all of the lines in the file
        # And we'll set breaker to be a weird delimiter so that we'll end up with an events 
        # array that can be rated by the hour of day and day of week rates
        # This is only for weird outside use cases like when we want to include a CSV file as the source
        # so we can't set breaker properly
        if self.bundlelines:
            logger.debug("Bundlelines set.  Creating %s copies of original sample lines and setting breaker." % (self.count-1))
            self.breaker = '\n------\n'
            origSampleLines = copy.deepcopy(sampleLines)
            sampleLines.append(self.breaker)
            for i in range(0, self.count-1):
                sampleLines.extend(origSampleLines)
                sampleLines.append(self.breaker)
            

        if len(sampleLines) > 0:
            count = self.count
            if self.count == 0 and self.mode == 'sample':
                logger.debug("Count %s specified as default for sample '%s' in app '%s'; adjusting count to sample length %s; using default breaker" \
                                % (self.count, self.name, self.app, len(sampleLines)) )
                count = len(sampleLines)
                self.breaker = self._c.breaker
            elif self.count > 0 or self.mode == 'replay':
                
                # 5/8/12 CS We've requested not the whole file, so we should adjust count based on
                # hourOfDay, dayOfWeek and randomizeCount configs
                rateFactor = 1.0
                if self.randomizeCount != 0 and self.randomizeCount != None:
                    try:
                        logger.debug("randomizeCount for sample '%s' in app '%s' is %s" \
                                        % (self.name, self.app, self.randomizeCount))
                        # If we say we're going to be 20% variable, then that means we
                        # can be .1% high or .1% low.  Math below does that.
                        randBound = round(self.randomizeCount * 1000, 0)
                        rand = random.randint(0, randBound)
                        randFactor = 1+((-((randBound / 2) - rand)) / 1000)
                        logger.debug("randFactor for sample '%s' in app '%s' is %s" \
                                        % (self.name, self.app, randFactor))
                        rateFactor *= randFactor
                    except:
                        import traceback
                        stack =  traceback.format_exc()
                        logger.error("Randomize count failed.  Stacktrace %s" % stack)
                if type(self.hourOfDayRate) == dict:
                    try:
                        if self.backfill != None and not self._backfilldone:
                            now = self._backfillts
                        else:
                            now = self.now()
                        rate = self.hourOfDayRate[str(now.hour)]
                        logger.debug("hourOfDayRate for sample '%s' in app '%s' is %s" % (self.name, self.app, rate))
                        rateFactor *= rate
                    except KeyError:
                        import traceback
                        stack =  traceback.format_exc()
                        logger.error("Hour of day rate failed.  Stacktrace %s" % stack)
                if type(self.dayOfWeekRate) == dict:
                    try:
                        if self.backfill != None and not self._backfilldone:
                            now = self._backfillts
                        else:
                            now = self.now()
                        weekday = datetime.date.weekday(now)
                        if weekday == 6:
                            weekday = 0
                        else:
                            weekday += 1
                        rate = self.dayOfWeekRate[str(weekday)]
                        logger.debug("dayOfWeekRate for sample '%s' in app '%s' is %s" % (self.name, self.app, rate))
                        rateFactor *= rate
                    except KeyError:
                        import traceback
                        stack =  traceback.format_exc()
                        logger.error("Hour of day rate failed.  Stacktrace %s" % stack)
                if type(self.minuteOfHourRate) == dict:
                    try:
                        if self.backfill != None and not self._backfilldone:
                            now = self._backfillts
                        else:
                            now = self.now()
                        rate = self.minuteOfHourRate[str(now.minute)]
                        logger.debug("minuteOfHourRate for sample '%s' in app '%s' is %s" % (self.name, self.app, rate))
                        rateFactor *= rate
                    except KeyError:
                        import traceback
                        stack =  traceback.format_exc()
                        logger.error("Minute of hour rate failed.  Stacktrace %s" % stack)
                count = int(round(count * rateFactor, 0))
                if rateFactor != 1.0:
                    logger.info("Original count: %s Rated count: %s Rate factor: %s" % (self.count, count, rateFactor))

            try:
                breakerRE = re.compile(self.breaker)
            except:
                logger.error("Line breaker '%s' for sample '%s' in app '%s' could not be compiled; using default breaker" \
                            % (self.breaker, self.name, self.app) )
                self.breaker = self._c.breaker

            events = []
            event = ''

            if self.breaker == self._c.breaker:
                logger.debug("Default breaker detected for sample '%s' in app '%s'; using simple event fill" \
                                % (self.name, self.app) )
                logger.debug("Filling events array for sample '%s' in app '%s'; count=%s, sampleLines=%s" \
                                % (self.name, self.app, count, len(sampleLines)) )

                # 5/8/12 CS Added randomizeEvents config to randomize items from the file
                # 5/27/12 CS Don't randomize unless we're raw
                try:
                    # 7/30/12 CS Can't remember why I wouldn't allow randomize Events for CSV so commenting
                    # this out and seeing what breaks
                    #if self.randomizeEvents and self.sampletype == 'raw':
                    if self.randomizeEvents:
                        logger.debug("Shuffling events for sample '%s' in app '%s'" \
                                        % (self.name, self.app))
                        random.shuffle(sampleLines)
                except:
                    logger.error("randomizeEvents for sample '%s' in app '%s' unparseable." \
                                    % (self.name, self.app))
                
                if count >= len(sampleLines):
                    events = sampleLines
                else:
                    events = sampleLines[0:count]
            else:
                logger.debug("Non-default breaker '%s' detected for sample '%s' in app '%s'; using advanced event fill" \
                                % (self.breaker, self.name, self.app) ) 

                ## Fill events array from breaker and sampleLines
                breakersFound = 0
                x = 0

                logger.debug("Filling events array for sample '%s' in app '%s'; count=%s, sampleLines=%s" \
                                % (self.name, self.app, count, len(sampleLines)) )
                while len(events) < count and x < len(sampleLines):
                    #logger.debug("Attempting to match regular expression '%s' with line '%s' for sample '%s' in app '%s'" % (breaker, sampleLines[x], sample, app) )
                    breakerMatch = breakerRE.search(sampleLines[x])

                    if breakerMatch:
                        #logger.debug("Match found for regular expression '%s' and line '%s' for sample '%s' in app '%s'" % (breaker, sampleLines[x], sample, app) )
                        ## If not first
                        # 5/28/12 CS This may cause a regression defect, but I can't figure out why
                        # you'd want to ignore the first breaker you find.  It's certainly breaking
                        # my current use case.

                        # 6/25/12 CS Definitely caused a regression defect.  I'm going to add
                        # a check for bundlelines which is where I need this to work every time
                        if breakersFound != 0 or self.bundlelines:
                            events.append(event)
                            event = ''

                        breakersFound += 1
                    # else:
                    #     logger.debug("Match not found for regular expression '%s' and line '%s' for sample '%s' in app '%s'" % (breaker, sampleLines[x], sample, app) )

                    # If we've inserted the breaker with bundlelines, don't insert the line, otherwise insert
                    if not (self.bundlelines and breakerMatch):
                        event += sampleLines[x]
                    x += 1

                ## If events < count append remaining data in samples
                if len(events) < count:
                    events.append(event + '\n')

                ## If breaker wasn't found in sample
                ## events = sample
                if breakersFound == 0:
                    logger.warn("Breaker '%s' not found for sample '%s' in app '%s'; using default breaker" % (self.breaker, self.name, self.app) )

                    if count >= len(sampleLines):
                        events = sampleLines
                    else:
                        events = sampleLines[0:count]
                else:
                    logger.debug("Found '%s' breakers for sample '%s' in app '%s'" % (breakersFound, self.name, self.app) )

            ## Continue to fill events array until len(events) == count
            if len(events) > 0 and len(events) < count:
                logger.debug("Events fill for sample '%s' in app '%s' less than count (%s vs. %s); continuing fill" % (self.name, self.app, len(events), count) )
                tempEvents = events[:]
                while len(events) < count:
                    y = 0
                    while len(events) < count and y < len(tempEvents):
                        events.append(tempEvents[y])
                        y += 1

            # logger.debug("events: %s" % pprint.pformat(events))
            logger.debug("Replacing %s tokens in %s events for sample '%s' in app '%s'" % (len(self.tokens), len(events), self.name, self.app))
            
            if self.sampletype == 'csv':
                self.index = sampleDict[0]['index']
                self.host = sampleDict[0]['host']
                self.source = sampleDict[0]['source']
                self.sourcetype = sampleDict[0]['sourcetype']
                logger.debug("Sampletype CSV.  Setting self._out to CSV parameters. index: '%s' host: '%s' source: '%s' sourcetype: '%s'" \
                            % (self.index, self.host, self.source, self.sourcetype))
                self._out.refreshconfig(self)
                
            # Find interval before we muck with the event but after we've done event breaking
            if self.mode == 'replay':
                logger.debug("Finding timestamp to compute interval for events")
                if self._lastts == None:
                    if self.sampletype == 'csv':
                        self._lastts = self._getTSFromEvent(self._rpevents[self._currentevent]['_raw'])
                    else:
                        self._lastts = self._getTSFromEvent(self._rpevents[self._currentevent])
                if (self._currentevent+1) < len(self._rpevents):
                    if self.sampletype == 'csv':
                        nextts = self._getTSFromEvent(self._rpevents[self._currentevent+1]['_raw'])
                    else:
                        nextts = self._getTSFromEvent(self._rpevents[self._currentevent+1])
                else:
                    logger.debug("At end of _rpevents")
                    return 0

                logger.debug('Computing timeDiff nextts: "%s" lastts: "%s"' % (nextts, self._lastts))

                timeDiff = nextts - self._lastts
                if timeDiff.days >= 0 and timeDiff.seconds >= 0 and timeDiff.microseconds >= 0:
                    partialInterval = float("%d.%06d" % (timeDiff.seconds, timeDiff.microseconds))
                else:
                    partialInterval = 0

                if self.timeMultiple > 0:
                    partialInterval *= self.timeMultiple

                logger.debug("Setting partialInterval for replay mode with timeMultiple %s: %s %s" % (self.timeMultiple, timeDiff, partialInterval))
                self._lastts = nextts

            ## Iterate events
            for x in range(0, len(events)):
                event = events[x]

                # Maintain state for every token in a given event
                # Hash contains keys for each file name which is assigned a list of values
                # picked from a random line in that file
                mvhash = { }

                ## Iterate tokens
                for token in self.tokens:
                    token.mvhash = mvhash
                    event = token.replace(event)
                if(self.hostToken):
                    # clear the host mvhash every time, because we need to re-randomize it
                    self.hostToken.mvhash =  {}

                # Hack for bundle lines to work with sampletype csv
                # Basically, bundlelines allows us to create copies of a bundled set of
                # of events as one event, and this splits those back out so that we properly
                # send each line with the proper sourcetype and source if we're we're sampletype csv
                if self.bundlelines and self.sampletype == 'csv':
                    # Trim last newline so we don't end up with blank at end of the array
                    if event[-1] == '\n':
                        event = event[:-1]
                    lines = event.split('\n')
                    logger.debug("Bundlelines set and sampletype csv, breaking event back apart.  %s lines." % (len(lines)))
                    for lineno in range(0, len(lines)):
                        if self.sampletype == 'csv' and (sampleDict[lineno]['index'] != self.index or \
                                                         sampleDict[lineno]['host'] != self.host or \
                                                         sampleDict[lineno]['source'] != self.source or \
                                                         sampleDict[lineno]['sourcetype'] != self.sourcetype):
                            # Flush events before we change all the various parameters
                            logger.debug("Sampletype CSV with bundlelines, parameters changed at event %s.  Flushing output." % lineno)
                            self._out.flush()
                            self.index = sampleDict[lineno]['index']
                            self.host = sampleDict[lineno]['host']
                            # Allow randomizing the host:
                            if(self.hostToken):
                                self.host = self.hostToken.replace(self.host)

                            self.source = sampleDict[lineno]['source']
                            self.sourcetype = sampleDict[lineno]['sourcetype']
                            logger.debug("Sampletype CSV.  Setting self._out to CSV parameters. index: '%s' host: '%s' source: '%s' sourcetype: '%s'" \
                                         % (self.index, self.host, self.source, self.sourcetype))
                            self._out.refreshconfig(self)
                        self._out.send(lines[lineno])
                    logger.debug("Completed bundlelines event.  Flushing.")
                    self._out.flush()
                else:
                    # logger.debug("Sample Index: %s Host: %s Source: %s Sourcetype: %s" % (self.index, self.host, self.source, self.sourcetype))
                    # logger.debug("Event Index: %s Host: %s Source: %s Sourcetype: %s" % (sampleDict[x]['index'], sampleDict[x]['host'], sampleDict[x]['source'], sampleDict[x]['sourcetype']))
                    if self.sampletype == 'csv' and (sampleDict[x]['index'] != self.index or \
                                                    sampleDict[x]['host'] != self.host or \
                                                    sampleDict[x]['source'] != self.source or \
                                                    sampleDict[x]['sourcetype'] != self.sourcetype):
                        # Flush events before we change all the various parameters
                        logger.debug("Sampletype CSV, parameters changed at event %s.  Flushing output." % x)
                        self._out.flush()
                        self.index = sampleDict[x]['index']
                        self.host = sampleDict[x]['host']
                        # Allow randomizing the host:
                        if(self.hostToken):
                            self.host = self.hostToken.replace(self.host)

                        self.source = sampleDict[x]['source']
                        self.sourcetype = sampleDict[x]['sourcetype']
                        logger.debug("Sampletype CSV.  Setting self._out to CSV parameters. index: '%s' host: '%s' source: '%s' sourcetype: '%s'" \
                                    % (self.index, self.host, self.source, self.sourcetype))
                        self._out.refreshconfig(self)
                    self._out.send(event)

            ## Close file handles
            self._out.flush()
            sampleFH.close()

            endTime = datetime.datetime.now()
            timeDiff = endTime - startTime

            if self.mode == 'sample':
                # timeDiffSecs = timeDelta2secs(timeDiff)
                timeDiffSecs = float("%d.%06d" % (timeDiff.seconds, timeDiff.microseconds))
                wholeIntervals = timeDiffSecs / self.interval
                partialInterval = timeDiffSecs % self.interval

                if wholeIntervals > 1:
                    logger.warn("Generation of sample '%s' in app '%s' took longer than interval (%s seconds vs. %s seconds); consider adjusting interval" \
                                % (self.name, self.app, timeDiff, self.interval) )

                partialInterval = self.interval - partialInterval
            
            # No rest for the wicked!  Or while we're doing backfill
            if self.backfill != None and not self._backfilldone:
                # Since we would be sleeping, increment the timestamp by the amount of time we're sleeping
                incsecs = round(partialInterval / 1, 0)
                incmicrosecs = partialInterval % 1
                self._backfillts += datetime.timedelta(seconds=incsecs, microseconds=incmicrosecs)
                partialInterval = 0

            self._timeSinceSleep += timeDiff
            if partialInterval > 0:
                timeDiffFrac = "%d.%06d" % (self._timeSinceSleep.seconds, self._timeSinceSleep.microseconds)
                logger.info("Generation of sample '%s' in app '%s' completed in %s seconds.  Sleeping for %f seconds" \
                            % (self.name, self.app, timeDiffFrac, partialInterval) )
                self._timeSinceSleep = datetime.timedelta()
            return partialInterval
        else:
            logger.warn("Sample '%s' in app '%s' contains no data" % (self.name, self.app) )
        
    ## Replaces $SPLUNK_HOME w/ correct pathing
    def pathParser(self, path):
        greatgreatgrandparentdir = os.path.dirname(os.path.dirname(self._c.grandparentdir)) 
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

    def _getTSFromEvent(self, event):
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
                        currentTime = datetime.datetime.fromtimestamp(ts)
                    else:
                        currentTime = datetime.datetime.strptime(timeString, timeFormat)
                    logger.debug("Match '%s' Format '%s' result: '%s'" % (timeString, timeFormat, currentTime))
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
        return currentTime
    
    def saveState(self):
        """Saves state of all integer IDs of this sample to a file so when we restart we'll pick them up"""
        for token in self.tokens:
            if token.replacementType == 'integerid':
                stateFile = open(os.path.join(self._c.sampleDir, 'state.'+urllib.pathname2url(token.token)), 'w')
                stateFile.write(token.replacement)
                stateFile.close()

    def now(self):
        logger.info("Getting time (timezone %s)" % (self.timezone))
        if self.timezone.days > 0:
            return datetime.datetime.now()
        else:
            return datetime.datetime.utcnow() + self.timezone

        
class Token:
    """Contains data and methods for replacing a token in a given sample"""
    token = None
    replacementType = None
    replacement = None
    sample = None
    mvhash = { }
    
    _now = None
    _replaytd = None
    _lastts = None
    _tokenre = None
    _tokenfile = None
    _tokents = None
    _earliestTime = None
    _latestTime = None
    
    def __init__(self, sample):
        self.sample = sample
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
        
        self._now = self.sample.now()
        self._earliestTime = (None, None)
        self._latestTime = (None, None)
        
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this token"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != 'sample' ])
        return pprint.pformat(temp)

    def __repr__(self):
        return self.__str__()
    
    def _match(self, event):
        """Executes regular expression match and returns the re.Match object"""
        if self._tokenre == None:
            self._tokenre = re.compile(self.token)
        return self._tokenre.match(event)
        
    def _search(self, event):
        """Executes regular expression search and returns the re.Match object"""
        if self._tokenre == None:
            self._tokenre = re.compile(self.token)
        return self._tokenre.search(event)
        
    def _finditer(self, event):
        """Executes regular expression finditer and returns the re.Match object"""
        if self._tokenre == None:
            self._tokenre = re.compile(self.token)
        return self._tokenre.finditer(event)
        
    def replace(self, event):
        """Replaces all instances of this token in provided event and returns event"""
        offset = 0
        tokenMatch = self._finditer(event)
        # logger.debug("Checking for match for token: '%s'" % (self.token))

        if tokenMatch:
            # 5/28/12 Changing logic to account for needing old to match
            # the right token we're actually replacing
            # This will call getReplacement for every match which is more
            # expensive, but necessary.
            
            # # Find old in case of error
            oldMatch = self._search(event)
            if oldMatch:
                # old = event[oldMatch.start(group):oldMatch.end(group)]
                group = 0 if len(oldMatch.groups()) == 0 else 1
                old = oldMatch.group(group)
            else:
                old = ""
            
            # logger.debug("Got match for token: '%s'" % (self.token))
            replacement = self._getReplacement(old)
            
            if replacement is not None:
                logger.debug("Replacement: '%s'" % replacement)
                ## Iterate matches
                for match in tokenMatch:
                    # logger.debug("Match: %s" % (match))
                    try:
                        matchStart = match.start(1) + offset
                        matchEnd = match.end(1) + offset
                        startEvent = event[:matchStart]
                        endEvent = event[matchEnd:]
                        # In order to not break legacy which might replace the same timestamp
                        # with the same value in multiple matches, here we'll include
                        # ones that need to be replaced for every match
                        if self.replacementType in ('replaytimestamp'):
                            replacement = self._getReplacement(event[matchStart:matchEnd])
                        offset += len(replacement) - len(match.group(1))
                    except:
                        matchStart = match.start(0) + offset
                        matchEnd = match.end(0) + offset
                        startEvent = event[:matchStart]
                        endEvent = event[matchEnd:]
                        # In order to not break legacy which might replace the same timestamp
                        # with the same value in multiple matches, here we'll include
                        # ones that need to be replaced for every match
                        if self.replacementType in ('replaytimestamp'):
                            replacement = self._getReplacement(event[matchStart:matchEnd])
                        offset += len(replacement) - len(match.group(0))
                    # logger.debug("matchStart %d matchEnd %d offset %d" % (matchStart, matchEnd, offset))
                    event = startEvent + replacement + endEvent
                
                # Reset replay internal variables for this token
                self._replaytd = None
                self._lastts = None
        return event
                    
    def _getReplacement(self, old=None, event=None):
        if self.replacementType == 'static':
            return self.replacement
        elif self.replacementType in ('timestamp', 'replaytimestamp'):
            if self.sample.earliest and self.sample.latest:
                # Optimizing for parsing times during mass event generation
                # Cache results to prevent calls to timeParser unless the value changes
                # Because every second, relative times could change, we can only cache
                # results for at maximum one second.  This seems not very effective, but we're
                # we're generating thousands of events per second it optimizes quite a bit.
                if self._tokents == None:
                    self._tokents = self.sample.now()

                # If we've gone more than a second, invalidate results, calculate
                # earliest and latest and cache new values
                if self.sample.now() - self._tokents > datetime.timedelta(seconds=1):
                    # logger.debug("Token Time Cache invalidated, refreshing")
                    self._tokents = self.sample.now()
                    earliestTime = timeParser(self.sample.earliest, timezone=self.sample.timezone)
                    latestTime = timeParser(self.sample.latest, timezone=self.sample.timezone)
                    self._earliestTime = (self.sample.earliest, earliestTime)
                    self._latestTime = (self.sample.latest, latestTime)
                else:
                    # If we match the text of the earliest and latest config value
                    # return cached value    
                    if self.sample.earliest == self._earliestTime[0] \
                            and self.sample.latest == self._latestTime[0]:
                        # logger.debug("Updating time from cache")
                        earliestTime = self._earliestTime[1]
                        latestTime = self._latestTime[1]
                    # Otherwise calculate and update the cache
                    else:
                        # logger.debug("Earliest and Latest Time Cache invalidated for times '%s' & '%s', refreshing" \
                        #                 % (self.sample.earliest, self.sample.latest))
                        earliestTime = timeParser(self.sample.earliest, timezone=self.sample.timezone)
                        self._earlestTime = (self.sample.earliest, earliestTime)
                        latestTime = timeParser(self.sample.latest, timezone=self.sample.timezone)
                        self._latestTime = (self.sample.latest, latestTime)


                # Don't muck with time while we're backfilling
                # if self.sample.backfill != None and not self.sample._backfilldone:
                #     earliestTime = timeParser(self.sample.earliest)
                #     latestTime = timeParser(self.sample.latest)
                # else:
                #     if datetime.datetime.now() - self._tokents > datetime.timedelta(seconds=1):
                #         self._tokents = datetime.datetime.now()
                #         earliestTime = timeParser(self.sample.earliest)
                #         latestTime = timeParser(self.sample.latest)
                #         self._earliestTime = earliestTime
                #         self._latestTime = latestTime
                #     else:
                #         earliestTime = self._earliestTime
                #         latestTime = self._latestTime

                if earliestTime and latestTime:
                    if latestTime>=earliestTime:
                        minDelta = 0

                        ## Compute timeDelta as total_seconds
                        td = latestTime - earliestTime
                        maxDelta = timeDelta2secs(td)

                        ## Get random timeDelta
                        randomDelta = datetime.timedelta(seconds=random.randint(minDelta, maxDelta))

                        ## Compute replacmentTime
                        replacementTime = latestTime - randomDelta
                        
                        if self.replacementType == 'replaytimestamp':
                            if old != None and len(old) > 0:
                                # Determine type of timestamp to use for this token
                                # We can either be a string with one strptime format
                                # or we can be a json formatted list of strptime formats
                                currentts = None
                                try:
                                    strptimelist = json.loads(self.replacement)   
                                    for currentformat in strptimelist:
                                        try:
                                            timeformat = currentformat
                                            if timeformat == "%s":
                                                ts = float(old) if  len(old) < 10 else float(old) / (10**(len(old)-10))
                                                currentts = datetime.datetime.fromtimestamp(ts)
                                            else:
                                                currentts = datetime.datetime.strptime(old, timeformat)
                                            # logger.debug("Old '%s' Timeformat '%s' currentts '%s'" % (old, timeformat, currentts))
                                            if type(currentts) == datetime.datetime:
                                                break
                                        except ValueError:
                                            pass
                                    if type(currentts) != datetime.datetime:
                                        # Total fail
                                        logger.error("Can't find strptime format for this timestamp '%s' in the list of formats.  Returning original value" % old)
                                        return old
                                except ValueError:
                                    # Not JSON, try to read as text
                                    timeformat = self.replacement
                                    try:
                                        if timeformat == "%s":
                                            ts = float(old) if  len(old) < 10 else float(old) / (10**(len(old)-10))
                                            currentts = datetime.datetime.fromtimestamp(ts)
                                        else:
                                            currentts = datetime.datetime.strptime(old, timeformat)
                                        # logger.debug("Timeformat '%s' currentts '%s'" % (timeformat, currentts))
                                    except ValueError:
                                        # Total fail
                                        logger.error("Can't match strptime format ('%s') to this timestamp '%s'.  Returning original value" % (timeformat, old))
                                        return old
                                    
                                    # Can't parse as strptime, try JSON
                                
                                # Check to make sure we parsed a year
                                if currentts.year == 1900:
                                    currentts = currentts.replace(year=self.sample.now().year)
                                # We should now know the timeformat and currentts associated with this event
                                # If we're the first, save those values        
                                if self._replaytd == None:
                                    self._replaytd = replacementTime - currentts
                                
                                # logger.debug("replaytd %s" % self._replaytd)
                                replacementTime = currentts + self._replaytd
                                
                                # Randomize time a bit between last event and this one
                                # Note that we'll always end up shortening the time between
                                # events because we don't know when the next timestamp is going to be
                                if self.sample.bundlelines:
                                    if self._lastts == None:
                                        self._lastts = replacementTime
                                    oldtd = replacementTime - self._lastts
                                    randomsecs = random.randint(0, oldtd.seconds)
                                    if oldtd.seconds > 0:
                                        randommicrosecs = random.randint(0, 1000000)
                                    else:
                                        randommicrosecs = random.randint(0, oldtd.microseconds)
                                    randomtd = datetime.timedelta(seconds=randomsecs, microseconds=randommicrosecs)
                                    replacementTime -= randomtd
                                else:
                                    randomtd = datetime.timedelta()
                                self._lastts = replacementTime
                                replacementTime = replacementTime.strftime(timeformat)
                                # logger.debug("Old '%s' Timeformat '%s' currentts '%s' replacementTime '%s' replaytd '%s' randomtd '%s'" \
                                #             % (old, timeformat, currentts, replacementTime, self._replaytd, randomtd))
                            else:
                                logger.error("Could not find old value, needed for replaytimestamp")
                                return old
                        else:
                            replacementTime = replacementTime.strftime(self.replacement)
                        ## replacementTime == replacement for invalid strptime specifiers
                        if replacementTime != self.replacement.replace('%', ''):
                            return replacementTime
                        else:
                            logger.error("Invalid strptime specifier '%s' detected; will not replace" \
                                        % (self.replacement) )
                            return old
                    ## earliestTime/latestTime not proper
                    else:
                        logger.error("Earliest specifier '%s', value '%s' is greater than latest specifier '%s', value '%s' for sample '%s'; will not replace" \
                                    % (self.sample.earliest, earliestTime, self.sample.latest, latestTime, self.sample.name) )
                        return old
            ## earliest/latest not proper
            else:
                logger.error('Earliest or latest specifier were not set; will not replace')
                return old
        elif self.replacementType in ('random', 'rated'):
            ## Validations:
            integerRE = re.compile('integer\[([-]?\d+):([-]?\d+)\]', re.I)
            integerMatch = integerRE.match(self.replacement)
            
            floatRE = re.compile('float\[(\d+)\.(\d+):(\d+)\.(\d+)\]', re.I)
            floatMatch = floatRE.match(self.replacement)

            stringRE = re.compile('string\((\d+)\)', re.I)
            stringMatch = stringRE.match(self.replacement)

            hexRE = re.compile('hex\((\d+)\)', re.I)
            hexMatch = hexRE.match(self.replacement)

            ## Valid replacements: ipv4 | ipv6 | integer[<start>:<end>] | string(<i>)
            if self.replacement.lower() == 'ipv4':
                x = 0
                replacement = ''

                while x < 4:
                    replacement += str(random.randint(0, 255)) + '.'
                    x += 1

                replacement = replacement.strip('.')
                return replacement
            elif self.replacement.lower() == 'ipv6':
                x = 0
                replacement = ''

                while x < 8:
                    replacement += hex(random.randint(0, 65535))[2:] + ':'
                    x += 1

                replacement = replacement.strip(':')
                return replacement
            elif self.replacement.lower() == 'mac':
                x = 0
                replacement = ''

                ## Give me 6 blocks of 2 hex
                while x < 6:
                    y = 0
                    while y < 2:
                        replacement += hex(random.randint(0, 15))[2:]
                        y += 1
                    replacement += ':'
                    x += 1

                replacement = replacement.strip(':')
                return replacement
            elif integerMatch:
                startInt = int(integerMatch.group(1))
                endInt = int(integerMatch.group(2))

                if endInt >= startInt:
                    replacementInt = random.randint(startInt, endInt)
                    if self.replacementType == 'rated':
                        rateFactor = 1.0
                        if type(self.sample.hourOfDayRate) == dict:
                            try:
                                rateFactor *= self.sample.hourOfDayRate[str(self._now.hour)]
                            except KeyError:
                                logger.error("Hour of day rate failed for token %s.  Stacktrace %s" % stack)
                        if type(self.sample.dayOfWeekRate) == dict:
                            try:
                                weekday = datetime.date.weekday(self._now)
                                if weekday == 6:
                                    weekday = 0
                                else:
                                    weekday += 1
                                rateFactor *= self.sample.dayOfWeekRate[str(weekday)]
                            except KeyError:
                                logger.error("Day of week rate failed.  Stacktrace %s" % stack)
                        replacementInt = int(round(replacementInt * rateFactor, 0))
                    replacement = str(replacementInt)
                    return replacement
                else:
                    logger.error("Start integer %s greater than end integer %s; will not replace" % (startInt, endInt) )
                    return old
            elif floatMatch:
                try:
                    startFloat = float(floatMatch.group(1)+'.'+floatMatch.group(2))
                    endFloat = float(floatMatch.group(3)+'.'+floatMatch.group(4))
                    
                    if endFloat >= startFloat:
                        floatret = round(random.uniform(startFloat,endFloat), len(floatMatch.group(2)))
                        if self.replacementType == 'rated':
                            rateFactor = 1.0
                            now = self.sample.now()
                            if type(self.sample.hourOfDayRate) == dict:
                                try:
                                    rateFactor *= self.sample.hourOfDayRate[str(now.hour)]
                                except KeyError:
                                    logger.error("Hour of day rate failed for token %s.  Stacktrace %s" % stack)
                            if type(self.sample.dayOfWeekRate) == dict:
                                try:
                                    weekday = datetime.date.weekday(now)
                                    if weekday == 6:
                                        weekday = 0
                                    else:
                                        weekday += 1
                                    rateFactor *= self.sample.dayOfWeekRate[str(weekday)]
                                except KeyError:
                                    logger.error("Day of week rate failed.  Stacktrace %s" % stack)
                            floatret = round(floatret * rateFactor, len(floatMatch.group(2)))
                        floatret = str(floatret)
                        return floatret
                    else:
                        logger.error("Start float %s greater than end float %s; will not replace" % (startFloat, endFloat))
                        return old
                except ValueError:
                    logger.error("Could not parse float[%s.%s:%s.%s]" % (floatMatch.group(1), floatMatch.group(2), \
                                floatMatch.group(3), floatMatch.group(4)))
                    return old
            elif stringMatch:
                strLength = int(stringMatch.group(1))
                if strLength == 0:
                    return ''
                elif strLength > 0:
                    replacement = ''
                    while len(replacement) < strLength:
                        ## Generate a random ASCII between dec 33->126
                        replacement += chr(random.randint(33, 126))
                        ## Practice safe strings
                        replacement = re.sub('%[0-9a-fA-F]+', '', urllib.quote(replacement))
                    
                    return replacement
                else:
                    logger.error("Length specifier %s for string replacement must be greater than 0; will not replace" % (strLength) )
                    return old
            elif hexMatch:
                strLength = int(hexMatch.group(1))

                replacement = ''
                hexList = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']
                while len(replacement) < strLength:
                    replacement += hexList[random.randint(0, 15)]

                return replacement
            else:
                logger.error("Unknown replacement value '%s' for replacementType '%s'; will not replace" % (self.replacement, self.replacementType) )
                return old
        elif self.replacementType in ('file', 'mvfile'):
            try:
                paths = self.replacement.split(':')
                if(len(paths) == 1):
                    replacementColumn = 0
                else:
                    try: # When it's not a mvfile, there's no number on the end:
                        replacementColumn = int(paths[-1])
                    except (ValueError):
                        replacementColumn = 0
                if(replacementColumn > 0):
                    # This supports having a drive-letter colon
                    replacementFile = self.sample.pathParser(":".join(paths[0:-1]))
                else:
                    replacementFile = self.sample.pathParser(self.replacement)
            except ValueError, e:
                logger.error("Replacement string '%s' improperly formatted.  Should be /path/to/file or /path/to/file:column" % (self.replacement))
                return old

            # If we've seen this file before, simply return already read results
            # This applies only if we're looking at a multivalue file and we want to
            # return the same random pick on every iteration
            if replacementColumn > 0 and replacementFile in self.mvhash:
                if replacementColumn > len(self.mvhash[replacementFile]):
                    logger.error("Index for column '%s' in replacement file '%s' is out of bounds" % (replacementColumn, replacementFile))
                    return old
                else:
                    # logger.debug("Returning mvhash: %s" % self.mvhash[replacementFile][replacementColumn-1])
                    return self.mvhash[replacementFile][replacementColumn-1]
            else:
                # Adding caching of the token file to avoid reading it every iteration
                if self._tokenfile != None:
                    replacementLines = self._tokenfile
                ## Otherwise, lets read the file and build our cached results, pick a result and return it
                else:
                    # logger.debug("replacementFile: %s replacementColumn: %s" % (replacementFile, replacementColumn))
                    if os.path.exists(replacementFile) and os.path.isfile(replacementFile):
                        replacementFH = open(replacementFile, 'rU')
                        replacementLines = replacementFH.readlines()
                        replacementFH.close()

                        if len(replacementLines) == 0:
                            logger.error("Replacement file '%s' is empty; will not replace" % (replacementFile) )
                            return old
                        else:
                            self._tokenfile = replacementLines
                    else:
                        logger.error("File '%s' does not exist" % (replacementFile))
                        return old

                replacement = replacementLines[random.randint(0, len(replacementLines)-1)].strip()

                if replacementColumn > 0:
                    self.mvhash[replacementFile] = replacement.split(',')

                    if replacementColumn > len(self.mvhash[replacementFile]):
                        logger.error("Index for column '%s' in replacement file '%s' is out of bounds" % (replacementColumn, replacementFile))
                        return old
                    else:
                        return self.mvhash[replacementFile][replacementColumn-1]
                else:
                    return replacement
        elif self.replacementType == 'integerid':
            temp = self.replacement
            self.replacement = str(int(self.replacement) + 1)
            return temp

        else:
            logger.error("Unknown replacementType '%s'; will not replace" % (replacementType) )
            return old

