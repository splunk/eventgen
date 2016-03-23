# TODO Handle timestamp generation for modular input output where we set sample.timestamp properly when we do a timestamp replacement

from __future__ import division, with_statement
import os
import logging
import pprint
import random
import datetime, time
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
    
    def __init__(self, sample=None):
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        if sample == None:
            name = "None"
        else:
            name = sample.name
        adapter = EventgenAdapter(logger, {'module': 'Token', 'sample': name})
        globals()['logger'] = adapter
        
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
        return re.match(self.token, event)
        
    def _search(self, event):
        """Executes regular expression search and returns the re.Match object"""
        return re.search(self.token, event)
        
    def _finditer(self, event):
        """Executes regular expression finditer and returns the re.Match object"""
        return re.finditer(self.token, event)

    def _findall(self, event):
        """Executes regular expression finditer and returns the re.Match object"""
        return re.findall(self.token, event)
        
    def replace(self, event, et=None, lt=None, s=None):
        """Replaces all instances of this token in provided event and returns event"""
        offset = 0
        tokenMatch = list(self._finditer(event))
        logger.debugv("Found %d matches for token: '%s' of type '%s' in sample '%s'" % (len(tokenMatch), self.token, self.replacementType, s.name))
        if self.replacementType == 'timestamp':
            logger.debugv("Timestamp replacement with et '%s' and lt '%s'" % (et, lt))

        if len(tokenMatch) > 0:
            replacement = self._getReplacement(event[tokenMatch[0].start(0):tokenMatch[0].end(0)], et, lt, s)
            
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
                        if self.replacementType == 'replaytimestamp':
                            replacement = self._getReplacement(event[matchStart:matchEnd], et, lt, s)
                        offset += len(replacement) - len(match.group(1))
                    except:
                        matchStart = match.start(0) + offset
                        matchEnd = match.end(0) + offset
                        startEvent = event[:matchStart]
                        endEvent = event[matchEnd:]
                        # In order to not break legacy which might replace the same timestamp
                        # with the same value in multiple matches, here we'll include
                        # ones that need to be replaced for every match
                        if self.replacementType == 'replaytimestamp':
                            replacement = self._getReplacement(event[matchStart:matchEnd], et, lt, s)
                        offset += len(replacement) - len(match.group(0))
                    # logger.debug("matchStart %d matchEnd %d offset %d" % (matchStart, matchEnd, offset))
                    event = startEvent + replacement + endEvent
                
                # Reset replay internal variables for this token
                self._replaytd = None
                self._lastts = None
        return event
                    
    def _getReplacement(self, old=None, earliestTime=None, latestTime=None, s=None):
        if self.replacementType == 'static':
            return self.replacement
        elif self.replacementType in ('timestamp', 'replaytimestamp'):
            if s.earliest and s.latest:
                if earliestTime and latestTime:
                    if latestTime>=earliestTime:
                        if s.timestamp == None:
                            minDelta = 0

                            ## Compute timeDelta as total_seconds
                            td = latestTime - earliestTime
                            maxDelta = timeDelta2secs(td)

                            ## Get random timeDelta
                            randomDelta = datetime.timedelta(seconds=random.randint(minDelta, maxDelta), microseconds=random.randint(0, latestTime.microsecond if latestTime.microsecond > 0 else 999999))

                            ## Compute replacmentTime
                            replacementTime = latestTime - randomDelta
                            s.timestamp = replacementTime
                        else:
                            replacementTime = s.timestamp

                        # logger.debug("Generating timestamp for sample '%s' with randomDelta %s, minDelta %s, maxDelta %s, earliestTime %s, latestTime %s, earliest: %s, latest: %s" % (s.name, randomDelta, minDelta, maxDelta, earliestTime, latestTime, s.earliest, s.latest))
                        
                        if self.replacementType == 'replaytimestamp':
                            if old != None and len(old) > 0:
                                # Determine type of timestamp to use for this token
                                # We can either be a string with one strptime format
                                # or we can be a json formatted list of strptime formats
                                currentts = None
                                try:
                                    strptimelist = json.loads(self.replacement)   
                                    # logger.debugv("Replaytimestamp formats: %s" % json.dumps(strptimelist))  
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
                                    # logger.debugv("Currentts: %s" % currentts)
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
                                    currentts = currentts.replace(year=s.now().year)
                                # We should now know the timeformat and currentts associated with this event
                                # If we're the first, save those values        
                                if self._replaytd == None:
                                    self._replaytd = replacementTime - currentts
                                
                                # logger.debug("replaytd %s" % self._replaytd)
                                replacementTime = currentts + self._replaytd
                                
                                # Randomize time a bit between last event and this one
                                # Note that we'll always end up shortening the time between
                                # events because we don't know when the next timestamp is going to be
                                if s.bundlelines:
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
                                replacement = timeformat.replace('%s', str(round(time.mktime(replacementTime.timetuple()))).rstrip('0').rstrip('.'))
                                replacementTime = replacementTime.strftime(replacement)
                                # logger.debugv("ReplacementTime: %s" % replacementTime)
                                # logger.debug("Old '%s' Timeformat '%s' currentts '%s' replacementTime '%s' replaytd '%s' randomtd '%s'" \
                                #             % (old, timeformat, currentts, replacementTime, self._replaytd, randomtd))
                            else:
                                logger.error("Could not find old value, needed for replaytimestamp")
                                return old
                        else:
                            replacement = self.replacement.replace('%s', str(round(time.mktime(replacementTime.timetuple()))).rstrip('0').rstrip('.'))
                            replacementTime = replacementTime.strftime(replacement)
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
                                    % (s.earliest, earliestTime, s.latest, latestTime, s.name) )
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
                        if type(s.hourOfDayRate) == dict:
                            try:
                                rateFactor *= s.hourOfDayRate[str(s.now())]
                            except KeyError:
                                import traceback
                                stack =  traceback.format_exc()
                                logger.error("Hour of day rate failed for token %s.  Stacktrace %s" % stack)
                        if type(s.dayOfWeekRate) == dict:
                            try:
                                weekday = datetime.date.weekday(s.now())
                                if weekday == 6:
                                    weekday = 0
                                else:
                                    weekday += 1
                                rateFactor *= s.dayOfWeekRate[str(weekday)]
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
                            now = s.now()
                            if type(s.hourOfDayRate) == dict:
                                try:
                                    rateFactor *= s.hourOfDayRate[str(now.hour)]
                                except KeyError:
                                    import traceback
                                    stack =  traceback.format_exc()
                                    logger.error("Hour of day rate failed for token %s.  Stacktrace %s" % stack)
                            if type(s.dayOfWeekRate) == dict:
                                try:
                                    weekday = datetime.date.weekday(now)
                                    if weekday == 6:
                                        weekday = 0
                                    else:
                                        weekday += 1
                                    rateFactor *= s.dayOfWeekRate[str(weekday)]
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
                    logger.error("Could not parse json for '%s' in sample '%s'" % (listMatch.group(1), s.name))
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
                        replacementFile = s.pathParser(":".join(paths[0:-1]))
                    else:
                        replacementFile = s.pathParser(self.replacement)
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
                    replacementFile = os.path.abspath(replacementFile)
                    logger.debug("Normalized replacement file %s" % replacementFile)
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