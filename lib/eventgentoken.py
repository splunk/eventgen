from __future__ import division, with_statement
import os
import logging
import pprint
import random
import datetime
import re
import json
import copy
from timeparser import timeParser, timeDelta2secs
import urllib
import uuid

class Token:
    """Contains data and methods for replacing a token in a given sample"""
    token = None
    replacementType = None
    replacement = None
    sample = None
    mvhash = { }
    
    _replaytd = None
    _lastts = None
    _tokenre = None
    _tokenfile = None
    _tokents = None
    _earliestTime = None
    _latestTime = None
    _replacementFile = None
    _replacementColumn = None
    _integerMatch = None
    _floatMatch = None
    _hexMatch = None
    _stringMatch = None
    _listMatch = None
    
    def __init__(self, sample):
        self.sample = sample
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
        
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

    def _findall(self, event):
        """Executes regular expression finditer and returns the re.Match object"""
        if self._tokenre == None:
            self._tokenre = re.compile(self.token)
        return self._tokenre.findall(event)
        
    def replace(self, event):
        """Replaces all instances of this token in provided event and returns event"""
        offset = 0
        tokenMatch = list(self._finditer(event))
        # logger.debug("Checking for match for token: '%s'" % (self.token))

        if len(tokenMatch) > 0:
            # 9/7/13  Trying to determine the logic for doing two regex
            # searches, one to find the list of potential replacements and 
            # another to find the actual string to replace, so commenting 
            # out and recoding... may cause regressions.

            # # 5/28/12 Changing logic to account for needing old to match
            # # the right token we're actually replacing
            # # This will call getReplacement for every match which is more
            # # expensive, but necessary.
            
            # # Find old in case of error
            # oldMatch = self._search(event)

            # if oldMatch:
            #     # old = event[oldMatch.start(group):oldMatch.end(group)]
            #     group = 0 if len(oldMatch.groups()) == 0 else 1
            #     old = oldMatch.group(group)
            # else:
            #     old = ""
            
            # logger.debug("Got match for token: '%s'" % (self.token))
            # replacement = self._getReplacement(old)

            replacement = self._getReplacement(event[tokenMatch[0].start(0):tokenMatch[0].end(0)])
            
            if replacement is not None:
                # logger.debug("Replacement: '%s'" % replacement)
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
                    
    def _getReplacement(self, old=None):
        if self.replacementType == 'static':
            return self.replacement
        elif self.replacementType in ('timestamp', 'replaytimestamp'):
            if self.sample.earliest and self.sample.latest:
                # First optimization, we need only store earliest and latest
                # as an offset of now if they're relative times
                if self.sample._earliestParsed != None:
                    earliestTime = self.sample.now() - self.sample._earliestParsed
                else:
                    if self.sample.earliest.strip()[0:1] == '+' or \
                            self.sample.earliest.strip()[0:1] == '-' or \
                            self.sample.earliest == 'now':
                        self.sample._earliestParsed = self.sample.now() - timeParser(self.sample.earliest, timezone=self.sample.timezone, now=self.sample.now, utcnow=datetime.datetime.utcnow)
                        earliestTime = self.sample.now() - self.sample._earliestParsed
                    else:
                        earliestTime = timeParser(self.sample.earliest, timezone=self.sample.timezone, now=self.sample.now, utcnow=self.sample.utcnow)

                if self.sample._latestParsed != None:
                    latestTime = self.sample.now() - self.sample._latestParsed
                else:
                    if self.sample.latest.strip()[0:1] == '+' or \
                            self.sample.latest.strip()[0:1] == '-' or \
                            self.sample.latest == 'now':
                        self.sample._latestParsed = self.sample.now() - timeParser(self.sample.latest, timezone=self.sample.timezone, now=self.sample.now, utcnow=datetime.datetime.utcnow)
                        latestTime = self.sample.now() - self.sample._latestParsed
                    else:
                        latestTime = timeParser(self.sample.latest, timezone=self.sample.timezone, now=self.sample.now, utcnow=self.sample.utcnow)
                
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

                        # logger.debug("Generating timestamp for sample '%s' with randomDelta %s, minDelta %s, maxDelta %s, earliestTime %s, latestTime %s, earliest: %s, latest: %s" % (self.sample.name, randomDelta, minDelta, maxDelta, earliestTime, latestTime, self.sample.earliest, self.sample.latest))
                        
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
            if self._integerMatch != None:
                integerMatch = self._integerMatch
            else:
                integerRE = re.compile('integer\[([-]?\d+):([-]?\d+)\]', re.I)
                integerMatch = integerRE.match(self.replacement)
                self._integerMatch = integerMatch
            
            if self._floatMatch != None:
                floatMatch = self._floatMatch
            else:
                floatRE = re.compile('float\[(\d+)\.(\d+):(\d+)\.(\d+)\]', re.I)
                floatMatch = floatRE.match(self.replacement)
                self._floatMatch = floatMatch

            if self._stringMatch != None:
                stringMatch = self._stringMatch
            else:
                stringRE = re.compile('string\((\d+)\)', re.I)
                stringMatch = stringRE.match(self.replacement)
                self._stringMatch = stringMatch

            if self._hexMatch != None:
                hexMatch = self._hexMatch
            else:       
                hexRE = re.compile('hex\((\d+)\)', re.I)
                hexMatch = hexRE.match(self.replacement)
                self._hexMatch = hexMatch

            if self._listMatch != None:
                listMatch = self._listMatch
            else:
                listRE = re.compile('list(\[[^\]]+\])', re.I)
                listMatch = listRE.match(self.replacement)
                self._listMatch = listMatch

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
            elif self.replacement.lower() == 'guid':
                return str(uuid.uuid4())
            elif integerMatch:
                startInt = int(integerMatch.group(1))
                endInt = int(integerMatch.group(2))

                if endInt >= startInt:
                    replacementInt = random.randint(startInt, endInt)
                    if self.replacementType == 'rated':
                        rateFactor = 1.0
                        if type(self.sample.hourOfDayRate) == dict:
                            try:
                                rateFactor *= self.sample.hourOfDayRate[str(self.sample.now())]
                            except KeyError:
                                import traceback
                                stack =  traceback.format_exc()
                                logger.error("Hour of day rate failed for token %s.  Stacktrace %s" % stack)
                        if type(self.sample.dayOfWeekRate) == dict:
                            try:
                                weekday = datetime.date.weekday(self.sample.now())
                                if weekday == 6:
                                    weekday = 0
                                else:
                                    weekday += 1
                                rateFactor *= self.sample.dayOfWeekRate[str(weekday)]
                            except KeyError:
                                import traceback
                                stack =  traceback.format_exc()
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
                                    import traceback
                                    stack =  traceback.format_exc()
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
                                    import traceback
                                    stack =  traceback.format_exc()
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
            elif listMatch:
                try:
                    value = json.loads(listMatch.group(1))
                except:
                    logger.error("Could not parse json for '%s' in sample '%s'" % (listMatch.group(1), self.sample.name))
                    return old
                return random.choice(value)

            else:
                logger.error("Unknown replacement value '%s' for replacementType '%s'; will not replace" % (self.replacement, self.replacementType) )
                return old
        elif self.replacementType in ('file', 'mvfile'):
            if self._replacementFile != None:
                replacementFile = self._replacementFile
                replacementColumn = self._replacementColumn
            else:
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
                self._replacementFile = replacementFile
                self._replacementColumn = replacementColumn

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