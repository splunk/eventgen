'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''

###########################################################
## SETUP CODE
## All of this junk is poorly organized setup code.  Sorry, but two reasons makes this so messy
## 1) We want to be able to run inside Splunk, which means using Splunk
##    modules to grab the configuration, or outside Splunk using ConfigParser etc
## 2) Running inside of Splunk means we have a lot of stupid pathing hacks to get around Splunk
##    not including setuptools and needing third party modules that don't come with Splunk python
###########################################################

## True division
from __future__ import division

import sys, os
if 'SPLUNK_HOME' in os.environ:
    path_prepend = os.environ['SPLUNK_HOME']+'/etc/apps/SA-Eventgen/lib'
else:
    path_prepend = '../lib'
sys.path.append(path_prepend)


# 5/6/12 CS Moving logging setup before imports so sub-modules can benefit of logger global
# Probably bad practice, but I'm lazy
import logging
import logging.handlers
# Creating as global so we can remove it later if needbe
stream_handler = logging.StreamHandler()

## Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('eventgen')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)

    return logger

logger = setup_logger()


import datetime
import httplib2
import random
import re
import shutil
import threading
import time
import urllib

# Imports added by CSharp
from timeparser import timeParser
from select import select

## Globals
# 5/7/12 CS __file__ doesn't seem to return an absolute path for me in my copy of python
# This seems to be inconsistent amongst implementations.  If we're not an absolute path, use CWD
if __file__.find('/') > 0:
    grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
else:
    grandparent = os.path.dirname(os.path.dirname(os.getcwd()))

## Defaults
DEFAULT_BLACKLIST = '.*\.part'
DEFAULT_SPOOLDIR = '$SPLUNK_HOME/var/spool/splunk'
DEFAULT_SPOOLFILE = '<SAMPLE>'
DEFAULT_BREAKER = '[^\r\n\s]+'
DEFAULT_INTERVAL = 60
DEFAULT_COUNT = 0
DEFAULT_EARLIEST = 'now'
DEFAULT_LATEST = 'now'
DEFAULT_REPLACEMENTS = ['static', 'timestamp', 'random', 'file', 'mvfile']

## Validations
tokenRex = re.compile('^token\.(\d+)$')

# 5/6/12 CS Called if we don't receive anything on stdin for 5 seconds
# This is legacy operations mode, just a little bit obfuscated now
# If we're not Splunk embedded, we operate simpler.  No rest handler for configurations
# we only read configs in our parent app's directory
SPLUNK_EMBEDDED = False
def splunkEmbedded():
    logger.info("Running as Splunk embedded")
    import splunk.auth as auth
    import splunk.bundle as bundle
    import splunk.entity as entity
    import splunk.rest as rest
    import splunk.util as util
    
    # 5/7/12 CS For some reason Splunk will not import the modules into global in its copy of python
    # This is a hacky workaround, but it does fix the problem
    globals()['auth'] = locals()['auth']
    globals()['bundle'] = locals()['bundle']
    globals()['entity'] = locals()['entity']
    globals()['rest'] = locals()['rest']
    globals()['util'] = locals()['util']
    globals()['SPLUNK_EMBEDDED'] = True
    globals()['grandparent'] = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    # import lxml.etree as et
    
    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/eventgen.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.removeHandler(stream_handler)
    
###########################################################
## END SETUP CODE
###########################################################

## Replaces $SPLUNK_HOME w/ correct pathing
def pathParser(path):
    # 5/7/12 CS Use global
    # grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 
    greatgreatgrandparent = os.path.dirname(os.path.dirname(grandparent)) 
    sharedStorage = ['$SPLUNK_HOME/etc/apps', '$SPLUNK_HOME/etc/users/', '$SPLUNK_HOME/var/run/splunk']

    ## Replace windows os.sep w/ nix os.sep
    path = path.replace('\\', '/')
    ## Normalize path to os.sep
    path = os.path.normpath(path)
    
    ## Iterate special paths
    for x in range(0, len(sharedStorage)):
        sharedPath = os.path.normpath(sharedStorage[x])
        
        if path.startswith(sharedPath):
            path.replace('$SPLUNK_HOME', greatgreatgrandparent)
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
    
    
## Get dict of samples
def getSamples(confDict):
    samplesDict = {}
    
    if confDict != None:
        ## Iterate stanzas and settings
        for stanza, settings in confDict.items():
            ## If eai acl's exist
            if settings['eai:acl'] and settings['eai:acl']['app']:
                ## Get app
                app = settings['eai:acl']['app']
            
                if not samplesDict.has_key(app):
                    samplesDict[app] = []
                
                    ## Get sampleDir
                    sampleDir = os.path.join(grandparent, app, 'samples')
            
                    ## If sampleDir exists
                    if os.path.exists(sampleDir):
                        samples = os.listdir(sampleDir)
                
                        ## Iterate each sample
                        for sample in samples:
                            samplePath = os.path.join(sampleDir, sample)
                        
                            ## If sample is a file
                            if os.path.isfile(samplePath):
                                logger.info("Found sample file '%s' for app '%s' using config '%s'; adding to list" % (sample, app, stanza) )
                                samplesDict[app].append(sample)
                            
                            else:
                                logger.warn("Sample '%s' for app '%s' is not a valid file; will not add to list" % (sample, app) )    
                                
                    else:
                        logger.error("Samples directory '%s' for app '%s' does not exist; skipping app" % (sampleDir, app) )
    
            else:
                logger.error("Eventgen configuration '%s' does not have an app defined in eai:acl; skipping app" % (stanza) )
    
    return samplesDict
    
## Sort tokens dictionary
def sortTokens(sample, tokens):
    tokensList = []
    stanzas = []    
    maxWeight = 0

    ## get maxWeight
    for stanza in tokens:
        if len(stanza) > maxWeight:
            maxWeight = len(stanza)

    ## Iterate tokens
    for stanza in tokens:
        ## If stanzas is empty just append
        if len(stanzas) == 0:
            stanzas.append(stanza)
        
        ## If stanzas has length
        else:
            ## default insertKey is append
            insertKey = len(stanzas)
        
            ## If stanza is sample insert @ head
            if stanza == sample:
                insertKey = 0
            
            ## If stanza is global insert @ end
            elif stanza == 'global':
                insertKey = len(stanzas)
            
            ## If stanza is a pattern
            else:
                ## Weight is length of pattern
                weight = len(stanza)
            
                ## Iterate stanzas to find insert loc
                for x in range(0, len(stanzas)):
                    ## Set tempWeight to highest possible if compare is sample
                    if stanzas[x] == sample:
                        tempWeight = maxWeight + 1
                        
                    ## Set tempWeight to lowest possible
                    elif stanzas[x] == 'global':
                        tempWeight = -1
                        
                    ## Set tempWeight to pattern length
                    else:
                        tempWeight = len(stanzas[x])
                        
                    ## If insert stanza higher in weight than existing stanza
                    ## Insert here
                    if weight > tempWeight:
                        insertKey = x
                    
                    ## If insert stanza equal in weight than existing stanza
                    elif weight == tempWeight:
                        ## And is alphanumeric precedent
                        ## Insert here
                        if stanza < stanzas[x]:
                            insertKey = x
                
                    ## Do not insert
                    else:
                        break
        
            ## Perform insert
            stanzas.insert(insertKey, stanza)
    
    ## Make tokensList
    for stanza in stanzas:
        for token in tokens[stanza]:
            tokensList.append(token)
        
    return tokensList


## Flatten confs for each sample
def flattenConf(confDict, samples):
    flatSamples = {}
        
    ## Iterate samples
    for app in samples:
        for sample in samples[app]:
            matchFound = False
            flatSample = {}
            sampleTokens = {}
            
            ## Get blacklist
            blacklistRE = re.compile(DEFAULT_BLACKLIST)
            blacklistMatch = blacklistRE.match(sample)
        
            ## Get globals
            if confDict['global']:
                for key, val in confDict['global'].items():
                    ## Filter eai settings
                    if not key.startswith('eai'):
                        ## Add key-val to sample with weight global
                        flatSample[key] = {}
                        flatSample[key]['val'] = val
                        flatSample[key]['weight'] = -1
                        flatSample[key]['stanza'] = 'global'
                        
            ## Iterate stanzas
            for stanza, settings in confDict.items():
                tokenIDs = []

                ## If stanza is an exact match 
                if stanza == sample and not blacklistMatch:
                    stanzaMatch = True
                    weight = sample
                    
                ## Stanza is a pattern
                else:
                    ## Currently using try/except for PCRE
                    ## Would rather use an endpoint to enable Splunk-style patterns
                    try:
                        stanzaRE = re.compile(stanza)             
                        stanzaMatch = stanzaRE.match(sample)
                        weight = len(stanza)

                    ## Pattern is invalid    
                    except:
                        stanzaMatch = False        

                ## If stanza has acl app settings
                if (settings['eai:acl'] and settings['eai:acl']['app']):
                
                    ## If stanza and app match
                    if stanzaMatch and not blacklistMatch and app == settings['eai:acl']['app']:
                        matchFound = True
                        
                        ## Iterate settings
                        for key, val in settings.items():
                         
                         ## spoolFile only valid for weight == sample
                            if key == 'spoolFile' and weight != sample:
                                val = None
                                
                            ## If key is token    
                            elif key.startswith('token'):
                                tokenMatch = tokenRex.match(key)
                                
                                if tokenMatch:
                                    tokenIDs.append(int(tokenMatch.group(1)))

                            ## If exists in sample and not eai
                            elif flatSample.has_key(key) and not key.startswith('eai:'):
                                                    
                                ## If a key alread exists...
                                ## Precedence is defined in the following order
                                
                                ## If weight == sample
                                if weight == sample:
                                    flatSample[key]['val'] = val
                                    flatSample[key]['weight'] = weight
                                    flatSample[key]['stanza'] = stanza
                                        
                                ## If weight >
                                elif weight > flatSample[key]['weight']:
                                    flatSample[key]['val'] = val
                                    flatSample[key]['weight'] = weight
                                    flatSample[key]['stanza'] = stanza
                                
                                ## If patterns are identical; favor alphanumeric
                                elif weight == flatSample[key]['weight']:
                                    ## If stanza comes before stored key
                                    if stanza < flatSample[key]['stanza']:
                                        flatSample[key]['val'] = val
                                        flatSample[key]['weight'] = weight
                                        flatSample[key]['stanza'] = stanza                                     
                                
                                else:
                                    pass
                                
                            ## If key is new and not eai
                            elif not key.startswith('eai:'):
                                flatSample[key] = {}
                                flatSample[key]['val'] = val
                                flatSample[key]['weight'] = weight
                                flatSample[key]['stanza'] = stanza
                                
                            ## If key eai
                            else:
                                pass
                                
                if len(tokenIDs) > 0:
                    sampleTokens[stanza] = []
                    tokenIDs.sort()

                    for tokenID in tokenIDs:
                        sampleTokens[stanza].append(settings['token.' + str(tokenID)])

            ## If at least one stanza matches
            if matchFound:
                        
                ## Clean samples
                for key in flatSample:
                    flatSample[key] = flatSample[key]['val']
                    
                ## If sample is enabled
                if flatSample.has_key('interval') and int(flatSample['interval']) > 0:
                    ## If flatSamples hasn't been initialized
                    if not flatSamples.has_key(app):
                        flatSamples[app] = {}
                        
                    if len(sampleTokens) > 0:
                        flatSample['tokens'] = sortTokens(sample, sampleTokens)
                    
                    ## Add sample
                    flatSamples[app][sample] = flatSample

    return flatSamples
                            
                            
## Parses time strings using /search/timeparser endpoint
# def timeParser(ts='now', sessionKey=None):
#     getargs = {}
#     getargs['time'] = ts
#     
#     tsStatus, tsResp = rest.simpleRequest('/search/timeparser', sessionKey=sessionKey, getargs=getargs)
#                 
#     root = et.fromstring(tsResp)    
#         
#     ts = root.find('dict/key')
#     if ts != None:
#         return util.parseISO(ts.text, strict=True)
#     
#     else:
#         logger.error("Could not retrieve timestamp for specifier '%s' from /search/timeparser" % (ts) )
#         return False
        

## Converts Time Delta object to number of seconds in delta
def timeDelta2secs(timeDiff):
    deltaSecs = (timeDiff.microseconds + (timeDiff.seconds + timeDiff.days * 24 * 3600) * 10**6) / 10**6
    return int(deltaSecs)

## sessionKey required for timestamp replacement
def getReplacement(old, tokenArr, earliest=DEFAULT_EARLIEST, latest=DEFAULT_LATEST, sessionKey=None, mvhash={ }):
    ## If token array is proper
    if len(tokenArr) == 3:

        replacementType = tokenArr[1]
        replacement = tokenArr[2]
        
        ## Valid replacementTypes: static | timestamp | random | file
        
        ## If replacement is of type static
        if replacementType == 'static':
            ## Replace and return string using re.sub
            return replacement
            
        ## If replacement is of type timestamp
        elif replacementType == 'timestamp':
            ## If earliest and latest are avail
            if earliest and latest:
                ## Create earliest/latestTime ISO8601 values
                earliestTime = timeParser(earliest, sessionKey=sessionKey)
                latestTime = timeParser(latest, sessionKey=sessionKey)        
                
                ## If earliest/latestTime are proper
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
                        replacementTime = replacementTime.strftime(replacement)
                    
                        ## replacementTime == replacement for invalid strptime specifiers
                        if replacementTime != replacement.replace('%', ''):
                            return replacementTime
                    
                        else:
                            logger.error("Invalid strptime specifier '%s' detected; will not replace" % (replacement) )
                            return old
                
                    ## earliestTime/latestTime not proper
                    else:
                        logger.error("Earliest specifier '%s' is greater than latest specifier '%s'; will not replace" % (earliest, latest) )
                        return old
            
            ## earliest/latest not proper
            else:
                logger.error('Earliest or latest specifier were not set; will not replace')
                return old    

        ## If replacement is of type random
        elif replacementType == 'random':
            
            #print replacement
            
            ## Validations:
            integerRE = re.compile('integer\[([-]?\d+):([-]?\d+)\]', re.I)
            integerMatch = integerRE.match(replacement)
            
            stringRE = re.compile('string\((\d+)\)', re.I)
            stringMatch = stringRE.match(replacement)
            
            hexRE = re.compile('hex\((\d+)\)', re.I)
            hexMatch = hexRE.match(replacement)
            
            ## Valid replacements: ipv4 | ipv6 | integer[<start>:<end>] | string(<i>)
            
            ## If replacement is of type ipv4
            if replacement.lower() == 'ipv4':
                x = 0
                replacement = ''
                
                while x < 4:
                    replacement += str(random.randint(0, 255)) + '.'
                    x += 1
                
                replacement = replacement.strip('.')
                return replacement
            
            ## If replacement is of type ipv6
            elif replacement.lower() == 'ipv6':
                x = 0
                replacement = ''
                
                while x < 8:
                    replacement += hex(random.randint(0, 65535))[2:] + ':'
                    x += 1
                    
                replacement = replacement.strip(':')
                return replacement
                
            elif replacement.lower() == 'mac':
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
            
            ## If replacement is of type integer
            elif integerMatch:
                startInt = int(integerMatch.group(1))
                endInt = int(integerMatch.group(2))
                
                ## If range is proper
                if endInt >= startInt:
                    ## Replace and return string using re.sub
                    replacement = str(random.randint(startInt, endInt))
                    return replacement
                    
                ## If range is not proper simply return string untouched
                else:
                    logger.error("Start integer %s greater than end integer %s; will not replace" % (startInt, endInt) )
                    return old
                    
            ## If replacement is of type string
            elif stringMatch:
                strLength = int(stringMatch.group(1))
                
                ## If length is 0 replace with empty string
                if strLength == 0:
                    return ''
                
                ## If length > 0 replace with random string of equal length
                elif strLength > 0:
                    replacement = ''
                    while len(replacement) < strLength:
                        ## Generate a random ASCII between dec 33->126
                        replacement += chr(random.randint(33, 126))
                        ## Practice safe strings
                        replacement = re.sub('%[0-9a-fA-F]+', '', urllib.quote(replacement))
                    
                    return replacement
                
                ## If length is not proper simply return string untouched
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
            
            ## If replacement type is not proper simply return string untouched
            else:
                logger.error("Unknown replacement value '%s' for replacementType '%s'; will not replace" % (replacement, replacementType) )
                return old
            
        ## If replacement is of type file
        elif replacementType == 'file':
            ## Build file path
            replacementFile = pathParser(replacement)
            
            ## If file exists
            if os.path.exists(replacementFile) and os.path.isfile(replacementFile):
                ## Open file and read random line
                replacementFH = open(replacementFile, 'rU')
                replacementLines = replacementFH.readlines()
                
                ## If file is empty
                if len(replacementLines) == 0:
                    logger.error("Replacement file '%s' is empty; will not replace" % (replacementFile) )
                    return old
                
                ## If file has at least 1 entry
                else:
                    replacement = replacementLines[random.randint(0, len(replacementLines)-1)].strip()
                
                replacementFH.close()
                
                ## Replace and return string using re.sub
                return replacement
            
            ## If file doesn't exist simply return string untouched
            else:
                logger.error("Replacement file '%s' is invalid or does not exist; will not replace" % (replacementFile) )
                return old
                
        elif replacementType == 'mvfile':
            try:
                replacementFile = pathParser(replacement.split(':')[0])
                replacementColumn = int(replacement.split(':')[1])-1
            except ValueError, e:
                logger.error("Replacement string '%s' improperly formatted.  Should be file:column" % (replacement))
                return old
            
            ## If we've seen this file before, simply return already read results
            if replacementFile in mvhash:
                if replacementColumn > len(mvhash[replacementFile]):
                    logger.error("Index for column '%s' in replacement file '%s' is out of bounds" % (replacementColumn, replacementFile))
                    return old
                else:
                    return mvhash[replacementFile][replacementColumn]
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
                    mvhash[replacementFile] = replacement.split(',')
                    
                    if replacementColumn > len(mvhash[replacementFile]):
                        logger.error("Index for column '%s' in replacement file '%s' is out of bounds" % (replacementColumn, replacementFile))
                        return old
                    else:
                        return mvhash[replacementFile][replacementColumn]
                else:
                    logger.error("File '%s' does not exist" % (replacementFile))
                    return old
        
        else:
            logger.error("Unknown replacementType '%s'; will not replace" % (replacementType) )
            return old
                
    ## If token is not proper simply return string untouched
    else:
        logger.error('Invalid token array; will not replace')
        return old


def genSample(app, sample, sessionKey=None):
        
    logger.info("Generating sample '%s' in app '%s'" % (sample, app))
        
    ## Verify sample still exists
    sampleFile = os.path.join(grandparent, app, 'samples', sample)
    spoolDir = pathParser(samples[app][sample]['spoolDir'])
    
    if os.path.exists(sampleFile) and os.path.exists(spoolDir):
        ## Create sampleFH
        logger.info("Opening sample '%s' in app '%s'" % (sample, app) )
        sampleFH = open(sampleFile, 'rU')
        
        ## Read sample
        logger.info("Reading sample '%s' in app '%s'" % (sample, app) )
        sampleLines = sampleFH.readlines()
        
        ## If sampleData has stuff
        if len(sampleLines) > 0:
        
            ## Create epoch time
            nowTime = int(time.mktime(time.gmtime()))
            ## Formulate working file
            workingFile = str(nowTime) + '-' + sample + '.part'
            workingFilePath = os.path.join(grandparent, app, 'samples', workingFile)
            logger.info("Creating working file '%s' for sample '%s' in app '%s'" % (workingFile, sample, app) )
            workingFH = open(workingFilePath, 'w')
            
            ## Set up spool file
            spoolFile = samples[app][sample]['spoolFile']
            if spoolFile == DEFAULT_SPOOLFILE:
                spoolFile = sample
            spoolFilePath = os.path.join(spoolDir, spoolFile)
            
            ## Set up count
            count = int(samples[app][sample]['count'])
            if count == 0:
                logger.info("Count %s specified as default for sample '%s' in app '%s'; adjusting count to sample length %s; using default breaker" % (count, sample, app, len(sampleLines)) )
                count = len(sampleLines)
                breaker = DEFAULT_BREAKER
                    
            elif count > 0:
                breaker = samples[app][sample]['breaker']
                logger.info("Count %s specified is non-default for sample '%s' in app '%s'; setting up line breaker '%s'" % (count, sample, app, breaker) )
                
            else:
                logger.error("Count %s is not proper for sample '%s' in app '%s'; reverting to default %s" % (count, sample, app, DEFAULT_COUNT) )
                count = DEFAULT_COUNT
            
            ## Set up breaker
            try:
                breakerRE = re.compile(breaker)
            except:
                logger.error("Line breaker '%s' for sample '%s' in app '%s' could not be compiled; using default breaker" % (breaker, sample, app) )
                breakerRE = re.compile(DEFAULT_BREAKER)
        
            ## Set up tokens
            earliest = samples[app][sample]['earliest']
            latest = samples[app][sample]['latest']
            tokens = []
                                
            if samples[app][sample].has_key('tokens'):
                tokens = samples[app][sample]['tokens']
            
            ## Create events array
            events = []
            event = ''
            
            if breaker == DEFAULT_BREAKER:
                logger.info("Default breaker detected for sample '%s' in app '%s'; using simple event fill" % (sample, app) )
                logger.info("Filling events array for sample '%s' in app '%s'; count=%s, sampleLines=%s" % (sample, app, count, len(sampleLines)) )
                
                if count >= len(sampleLines):
                    events = sampleLines
                    
                else:
                    events = sampleLines[0:count]
                            
            else:
                logger.info("Non-default breaker '%s' detected for sample '%s' in app '%s'; using advanced event fill" % (breaker, sample, app) ) 
            
                ## Fill events array from breaker and sampleLines
                breakersFound = 0
                x = 0
                
                logger.info("Filling events array for sample '%s' in app '%s'; count=%s, sampleLines=%s" % (sample, app, count, len(sampleLines)) )
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
                    
                    #else:
                    #    logger.debug("Match not found for regular expression '%s' and line '%s' for sample '%s' in app '%s'" % (breaker, sampleLines[x], sample, app) )
                    
                    event += sampleLines[x]
                    x += 1
                        
                ## If events < count append remaining data in samples
                if len(events) < count:
                    events.append(event + '\n')
                
                ## If breaker wasn't found in sample
                ## events = sample
                if breakersFound == 0:
                    logger.warn("Breaker '%s' not found for sample '%s' in app '%s'; using default breaker" % (breaker, sample, app) )
                    
                    if count >= len(sampleLines):
                        events = sampleLines
                    
                    else:
                        events = sampleLines[0:count]
        
                else:
                    logger.info("Found '%s' breakers for sample '%s' in app '%s'" % (breakersFound, sample, app) )
            
            ## Continue to fill events array until len(events) == count
            if len(events) > 0 and len(events) < count:
                logger.info("Events fill for sample '%s' in app '%s' less than count (%s vs. %s); continuing fill" % (sample, app, len(events), count) )
                tempEvents = events[:]
                while len(events) < count:
                    y = 0
                    while len(events) < count and y < len(tempEvents):
                        events.append(tempEvents[y])
                        y += 1
                    
            ## Iterate events
            for x in range(0, len(events)):
                event = events[x]
                
                ## Maintain state for every token in a given event
                ## Hash contains keys for each file name which is assigned a list of values
                ## picked from a random line in that file
                mvhash = { }
                
                ## Iterate tokens
                for token in tokens:
                    offset = 0
                    tokenRE = re.compile(token[0])
                    tokenMatch = tokenRE.finditer(event)
                    
                    # logger.debug("Checking for match for token: '%s'" % (token[0]))
                    
                    ## If tokenMatch
                    if tokenMatch:
                        # logger.debug("Got match for token: '%s'" % (token[0]))
                        ## Set up replacement
                        replacement = getReplacement(old=None, tokenArr=token, earliest=earliest, latest=latest, sessionKey=sessionKey, mvhash=mvhash)

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
                    
                workingFH.write(event)
                                     
            ## Close file handles
            logger.info("Closing file handles for working file '%s' and sample '%s' in app '%s'" % (workingFile, sample, app) )
            sampleFH.close()
            workingFH.close()
            
            ## Move file to spool
            logger.info("Moving '%s' to '%s' for sample '%s' in app '%s'" % (workingFilePath, spoolFilePath, sample, app) )
            shutil.move(workingFilePath, spoolFilePath)
            
        else:
            logger.warn("Sample '%s' in app '%s' contains no data" % (sample, app) )
            
    else:
        logger.error("Sample '%s' in app '%s' or Spool directory '%s' does not exist" % (sample, app, spoolDir) )


        # 5/7/12 Working around poor signal handling by python Threads (mainly on BSD implementations
        # it seems).  This hopefully handles signals properly and allows us to terminate.
        # Copied from http://code.activestate.com/recipes/496960/
        import ctypes

def _async_raise(tid, excobj):
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(excobj))
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # """if it returns a number greater than one, you're in trouble, 
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
        raise SystemError("PyThreadState_SetAsyncExc failed")

class Timer(threading.Thread):
    def raise_exc(self, excobj):
        assert self.isAlive(), "thread must be started"
        for tid, tobj in threading._active.items():
            if tobj is self:
                _async_raise(tid, excobj)
                return

        # the thread was alive when we entered the loop, but was not found 
        # in the dict, hence it must have been already terminated. should we raise
        # an exception here? silently ignore?

    def terminate(self):
        # must raise the SystemExit type, instead of a SystemExit() instance
        # due to a bug in PyThreadState_SetAsyncExc
        self.raise_exc(SystemExit)

    # Added by CS 5/7/12 to emulate threading.Timer
    def __init__(self, time, app, sample, interval, sessionKey=None):
        self.time = time
        self.stopping = False
        
        self.app = app
        self.sample = sample
        self.interval = interval
        self.sessionKey = sessionKey
        threading.Thread.__init__(self)

    def run(self):
        while (1):
            if not self.stopping:
                ## Compute starting time    
                startTime = datetime.datetime.now()

                ## Generate sample
                genSample(self.app, self.sample, sessionKey=self.sessionKey)

                ## Compute ending time
                endTime = datetime.datetime.now()

                ## Compute timeDiff
                timeDiff = endTime - startTime

                ## Compute timeDiff in secs
                timeDiff = timeDelta2secs(timeDiff)
                logger.info("Generation of sample '%s' in app '%s' completed in %s seconds" % (sample, app, timeDiff) )

                ## Compute number of intervals that last generation sequence spanned
                wholeIntervals = timeDiff / self.interval
                ## Computer partial interval that last generation sequence spanned
                partialInterval = timeDiff % self.interval

                if wholeIntervals > 1:
                    logger.warn("Generation of sample '%s' in app '%s' took longer than interval (%s seconds vs. %s seconds); consider adjusting interval" % (sample, app, timeDiff, interval) )

                ## Compute sleep as the difference between interval and partial interval
                partialInterval = self.interval - partialInterval
                logger.info("Generation of sample '%s' in app '%s' sleeping for %s seconds" % (sample, app, partialInterval) )

                ## Sleep for partial interval
                time.sleep(partialInterval)
            else:
                sys.exit(0)

    def stop(self):
        self.stopping = True



# def genSampleWrapper(app, sample, interval, sessionKey=None):
#         
#     while(1):
                     
            
if __name__ == '__main__':
    logger.info('Starting eventgen')
    debug = False
    
    # 5/6/12 CS use select to listen for input on stdin
    # if we timeout, assume we're not splunk embedded
    rlist, _, _ = select([sys.stdin], [], [], 5)
    if rlist:
        sessionKey = sys.stdin.readline().strip()
    else:
        sessionKey = ''
    
    if sessionKey == 'debug':
        debug = True
        splunkEmbedded()
        sessionKey = auth.getSessionKey('admin', 'changeme')
    elif len(sessionKey) > 0:
        splunkEmbedded()

    ## Get eventgen configurations
    if SPLUNK_EMBEDDED:
        logger.info('Retrieving eventgen configurations from /configs/eventgen')
        confDict = entity.getEntities('configs/eventgen', count=-1, sessionKey=sessionKey)
    else:
        from eventgenconfig import configParser
        confDict = configParser()
    
    samples = {}
    if confDict != None:
        logger.info('Finished retrieving %s eventgen configurations from /configs/eventgen' % (len(confDict)) )

        ## Get samples
        logger.info('Retrieving sample files from $SPLUNK_HOME/etc/apps/<app>/samples directories')
        samples = getSamples(confDict)
        sampleCount = 0
        for app in samples:
            for sample in samples[app]:
                sampleCount += 1     
        logger.info("Finished retrieving %s files from %s app samples directories" % (sampleCount, len(samples)) )
    
        ## Flatten configs
        logger.info("Matching files to eventgen configurations and flattening")
        samples = flattenConf(confDict, samples)
        sampleCount = 0
        for app in samples:
            for sample in samples[app]:
                    sampleCount += 1         
        logger.info("Matched %s samples with eventgen configurations" % (sampleCount) )

        ## Print configs
        #for app in samples:
        #    for sample in samples[app]:
        #        print '\n[' + sample + ']'
        #        for k, v in samples[app][sample].items():
        #            print k + ': ' 
        #            print v
 
        ## Initialize timer objects arr
        sampleTimers = []
        
        if debug:
            logger.info('Entering debug (single iteration) mode')

        ## Iterate samples
        for app in samples:
            for sample in samples[app]:
                ## Set up interval
                interval = int(samples[app][sample]['interval'])
                
                ## If sample is enabled
                if interval > 0:
                        
                    ## If debug call genSample
                    if debug:
                        genSample(app, sample, sessionKey=sessionKey)
                
                    ## If not debug initialize timer object
                    else:
                        logger.info("Creating timer object for sample '%s' in app '%s'" % (sample, app) )    
                        t = Timer(0.1, app, sample, interval, sessionKey)
                    
                        if t:
                            logger.info("Timer object for sample '%s' in app '%s' successfully created" % (sample, app) )    
                            sampleTimers.append(t)
                            
                        else:
                            logger.error("Failed to create timer object for sample '%s' in app '%s'" % (sample, app) )
                                
                else:
                    logger.info("Event generation for sample '%s' in app '%s' is disabled" % (sample, app) )
        
        ## Start the timers
        if not debug:                
            first = True
            while (1):
                try:
                    ## Only need to start timers once
                    if first:
                        logger.info('Starting timers')
                        for sampleTimer in sampleTimers:
                            sampleTimer.start()
                        first = False
                    time.sleep(600)
                except KeyboardInterrupt:
                    for sampleTimer in sampleTimers:
                        sampleTimer.stop()
                    sys.exit(0)