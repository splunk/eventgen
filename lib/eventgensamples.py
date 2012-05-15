from __future__ import division
import os
import logging
import pprint
import random
import datetime
import re
from eventgenoutput import Output
from timeparser import timeParser, timeDelta2secs
# Config may get imported multiple times, in that case just ignore it
# try:
#     from eventgenconfig import Config
# except ImportError:
#     pass
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
    interval = None
    count = None
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
    tokens = None
    
    # Internal fields
    _c = None
    _out = None
    
    def __init__(self, name):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
        
        self.name = name
        self.tokens = [ ]
        
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
        
        # If this is the first time we're generating, setup out
        if self._out == None:
            logger.debug("Setting up Output class for sample '%s' in app '%s'" % (self.name, self.app))
            self._out = Output(self)
        
        logger.debug("Opening sample '%s' in app '%s'" % (self.name, self.app) )
        sampleFH = open(self.filePath, 'rU')
        logger.debug("Reading sample '%s' in app '%s'" % (self.name, self.app) )
        sampleLines = sampleFH.readlines()
        
        # Ensure all lines have a newline
        for i in xrange(0, len(sampleLines)):
            if sampleLines[i][-1] != '\n':
                sampleLines[i] += '\n'

        if len(sampleLines) > 0:
            count = self.count
            if self.count == 0:
                logger.debug("Count %s specified as default for sample '%s' in app '%s'; adjusting count to sample length %s; using default breaker" \
                                % (self.count, self.name, self.app, len(sampleLines)) )
                count = len(sampleLines)
            elif self.count > 0:
                
                # 5/8/12 CS We've requested not the whole file, so we should adjust count based on
                # hourOfDay, dayOfWeek and randomizeCount configs
                rateFactor = 1.0
                if self.randomizeCount != 0:
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
                        now = datetime.datetime.now()
                        rate = self.hourOfDayRate[str(now.hour)]
                        logger.debug("hourOfDayRate for sample '%s' in app '%s' is %s" % (self.name, self.app, rate))
                        rateFactor *= rate
                    except:
                        import traceback
                        stack =  traceback.format_exc()
                        logger.error("Hour of day rate failed.  Stacktrace %s" % stack)
                if type(self.dayOfWeekRate) == dict:
                    try:
                        weekday = datetime.date.weekday(datetime.datetime.now())
                        if weekday == 6:
                            weekday = 0
                        else:
                            weekday += 1
                        rate = self.dayOfWeekRate[str(weekday)]
                        logger.debug("dayOfWeekRate for sample '%s' in app '%s' is %s" % (self.name, self.app, rate))
                        rateFactor *= rate
                    except:
                        import traceback
                        stack =  traceback.format_exc()
                        logger.error("Hour of day rate failed.  Stacktrace %s" % stack)
                count = int(round(count * rateFactor, 0))
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
                try:
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
                        if breakersFound != 0:
                            events.append(event)
                            event = ''

                        breakersFound += 1
                    # else:
                    #     logger.debug("Match not found for regular expression '%s' and line '%s' for sample '%s' in app '%s'" % (breaker, sampleLines[x], sample, app) )

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

            logger.debug("Replacing %s tokens in %s events for sample '%s' in app '%s'" % (len(self.tokens), len(events), self.name, self.app))
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
                self._out.send(event)

            ## Close file handles
            logger.debug("Flushing output for sample '%s' in app '%s'" % (self.name, self.app))
            self._out.flush()
            sampleFH.close()
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
        
        
class Token:
    token = None
    replacementType = None
    replacement = None
    sample = None
    mvhash = { }
    
    def __init__(self, sample):
        self.sample = sample
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
        
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this token"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != 'sample' ])
        return pprint.pformat(temp)

    def __repr__(self):
        return self.__str__()
    
    def _match(self, event):
        """Executes regular expression match and returns the re.Match object"""
        return re.match(self.token, event)
        
    def _search(self, event):
        """Executes regular expression search and returns the re.Match object"""
        return re.search(self.token, event)
        
    def _finditer(self, event):
        """Executes regular expression finditer and returns the re.Match object"""
        return re.finditer(self.token, event)
        
    def replace(self, event):
        """Replaces all instances of this token in provided event and returns event"""
        offset = 0
        tokenMatch = self._finditer(event)
        # logger.debug("Checking for match for token: '%s'" % (self.token))

        if tokenMatch:
            # Find old in case of error
            oldMatch = self._search(event)
            if oldMatch:
                old = event[oldMatch.start(0):oldMatch.end(0)]
            else:
                old = ""
            
            # logger.debug("Got match for token: '%s'" % (self.token))
            replacement = self._getReplacement(old)

            if replacement != None:
                # logger.debug("Replacement: '%s'" % (replacement))
                ## Iterate matches
                for match in tokenMatch:
                    # logger.debug("Match: %s" % (match))
                    try:
                        matchStart = match.start(1) + offset
                        matchEnd = match.end(1) + offset
                        startEvent = event[:matchStart]
                        endEvent = event[matchEnd:]
                        offset += len(replacement) - len(match.group(1))

                    except:
                        matchStart = match.start(0) + offset
                        matchEnd = match.end(0) + offset
                        startEvent = event[:matchStart]
                        endEvent = event[matchEnd:]
                        offset += len(replacement) - len(match.group(0))

                    # logger.debug("matchStart %d matchEnd %d offset %d" % (matchStart, matchEnd, offset))
                    event = startEvent + replacement + endEvent
        return event
                    
    def _getReplacement(self, old=None):
        if self.replacementType == 'static':
            return self.replacement
        elif self.replacementType == 'timestamp':
            if self.sample.earliest and self.sample.latest:
                earliestTime = timeParser(self.sample.earliest)
                latestTime = timeParser(self.sample.latest)        

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
                        logger.error("Earliest specifier '%s' is greater than latest specifier '%s'; will not replace" \
                                    % (self.sample.earliest, self.sample.latest) )
                        return old
            ## earliest/latest not proper
            else:
                logger.error('Earliest or latest specifier were not set; will not replace')
                return old    
        elif self.replacementType == 'random':
            ## Validations:
            integerRE = re.compile('integer\[([-]?\d+):([-]?\d+)\]', re.I)
            integerMatch = integerRE.match(self.replacement)

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
                    replacement = str(random.randint(startInt, endInt))
                    return replacement
                else:
                    logger.error("Start integer %s greater than end integer %s; will not replace" % (startInt, endInt) )
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
                logger.error("Unknown replacement value '%s' for replacementType '%s'; will not replace" % (replacement, replacementType) )
                return old
        elif self.replacementType == 'file':
            replacementFile = self.sample.pathParser(self.replacement)
            
            if os.path.exists(replacementFile) and os.path.isfile(replacementFile):
                replacementFH = open(replacementFile, 'rU')
                replacementLines = replacementFH.readlines()

                if len(replacementLines) == 0:
                    logger.error("Replacement file '%s' is empty; will not replace" % (replacementFile) )
                    return old
                else:
                    replacement = replacementLines[random.randint(0, len(replacementLines)-1)].strip()

                replacementFH.close()

                return replacement
            else:
                logger.error("Replacement file '%s' is invalid or does not exist; will not replace" % (replacementFile) )
                return old
        elif self.replacementType == 'mvfile':
            try:
                replacementFile = self.sample.pathParser(self.replacement.split(':')[0])
                replacementColumn = int(self.replacement.split(':')[1])-1
            except ValueError, e:
                logger.error("Replacement string '%s' improperly formatted.  Should be file:column" % (replacement))
                return old

            ## If we've seen this file before, simply return already read results
            if replacementFile in self.mvhash:
                if replacementColumn > len(self.mvhash[replacementFile]):
                    logger.error("Index for column '%s' in replacement file '%s' is out of bounds" % (replacementColumn, replacementFile))
                    return old
                else:
                    return self.mvhash[replacementFile][replacementColumn]
            ## Otherwise, lets read the file and build our cached results, pick a result and return it
            else:
                if os.path.exists(replacementFile) and os.path.isfile(replacementFile):
                    replacementFH = open(replacementFile, 'rU')
                    replacementLines = replacementFH.readlines()

                    if len(replacementLines) == 0:
                        logger.error("Replacement file '%s' is empty; will not replace" % (replacementFile) )
                        return old
                    else:
                        replacement = replacementLines[random.randint(0, len(replacementLines)-1)].strip()

                    replacementFH.close()
                    self.mvhash[replacementFile] = replacement.split(',')

                    if replacementColumn > len(self.mvhash[replacementFile]):
                        logger.error("Index for column '%s' in replacement file '%s' is out of bounds" % (replacementColumn, replacementFile))
                        return old
                    else:
                        return self.mvhash[replacementFile][replacementColumn]
                else:
                    logger.error("File '%s' does not exist" % (replacementFile))
                    return old
        else:
            logger.error("Unknown replacementType '%s'; will not replace" % (replacementType) )
            return old

