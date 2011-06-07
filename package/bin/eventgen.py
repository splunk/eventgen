'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''
## True division
from __future__ import division

import datetime
import httplib2
import os
import random
import re
import shutil
import splunk.auth as auth
import splunk.bundle as bundle
import splunk.entity as entity
import splunk.rest as rest
import splunk.util as util
import sys
import threading
import time
import lxml.etree as et
import urllib

## Globals
grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 

## Defaults
DEFAULT_BLACKLIST = '.*\.part'
DEFAULT_SPOOLDIR = '$SPLUNK_HOME/var/spool/splunk'
DEFAULT_SPOOLFILE = '<SAMPLE>'
DEFAULT_BREAKER = '[^\r\n\s]+'
DEFAULT_INTERVAL = 60
DEFAULT_COUNT = 0
DEFAULT_EARLIEST = 'now'
DEFAULT_LATEST = 'now'
DEFAULT_REPLACEMENTS = ['static', 'timestamp', 'random', 'file']

## Validations
tokenRex = re.compile('^token\.(\d+)$')

  
## Replaces $SPLUNK_HOME w/ correct pathing
def pathParser(path):
  grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 
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
                samplesDict[app].append(sample)
  
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
def timeParser(ts='now', sessionKey=None):
  getargs = {}
  getargs['time'] = ts

  tsStatus, tsResp = rest.simpleRequest('/search/timeparser', sessionKey=sessionKey, getargs=getargs)
        
  root = et.fromstring(tsResp)  
    
  ts = root.find('dict/key')
  if ts != None:
    return util.parseISO(ts.text, strict=True)
  
  else:
    return False
  

## sessionKey required for timestamp replacement
def getReplacement(old, tokenArr, earliest=DEFAULT_EARLIEST, latest=DEFAULT_LATEST, sessionKey=None):
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
        if earliestTime and latestTime and latestTime>=earliestTime:
          minDelta = 0
        
          ## Compute timeDelta as total_seconds
          td = latestTime - earliestTime
          maxDelta = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
          maxDelta = int(maxDelta)
          
          ## Get random timeDelta
          randomDelta = datetime.timedelta(seconds=random.randint(minDelta, maxDelta))
          
          ## Compute replacmentTime
          replacementTime = latestTime - randomDelta
          replacementTime = replacementTime.strftime(replacement)
          
          ## replacementTime == replacement for invalid strptime specifiers
          if replacementTime != replacement.replace('%', ''):
            return replacementTime
          
          else:
            return old
        
        ## earliestTime/latestTime not proper
        else:
          return old
      
      ## earliest/latest not proper
      else:
        return old  

    ## If replacement is of type random
    elif replacementType == 'random':
      
      #print replacement
      
      ## Validations:
      integerRE = re.compile('integer\[([-]?\d+):([-]?\d+)\]', re.I)
      integerMatch = integerRE.match(replacement)
      
      stringRE = re.compile('string\((\d+)\)', re.I)
      stringMatch = stringRE.match(replacement)
      
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
          return old
      
      ## If replacement type is not proper simply return string untouched
      else:
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
          return old
        
        ## If file has at least 1 entry
        else:
          replacement = replacementLines[random.randint(0, len(replacementLines)-1)].strip()
        
        replacementFH.close()
        
        ## Replace and return string using re.sub
        return replacement
      
      ## If file doesn't exist simply return string untouched
      else:
        return old
        
  ## If token is not proper simply return string untouched
  else:
    return old


def genSample(app, sample, sessionKey=None):
  ## Verify sample still exists
  sampleFile = os.path.join(grandparent, app, 'samples', sample)
  spoolDir = pathParser(samples[app][sample]['spoolDir'])
  
  if os.path.exists(sampleFile) and os.path.exists(spoolDir):
    ## Create sampleFH
    sampleFH = open(sampleFile, 'rU')
    ## Read sample
    sampleData = sampleFH.read()
    
    ## If sampleData has stuff
    if len(sampleData) > 0:
    
      ## Create epoch time
      nowTime = util.mktimegm(time.gmtime())
      ## Formulate working file
      workingFilePath = os.path.join(grandparent, app, 'samples', str(nowTime) + '-' + sample + '.part')
      workingFH = open(workingFilePath, 'w')
      
      ## Set up spool file
      spoolFile = samples[app][sample]['spoolFile']
      if spoolFile == DEFAULT_SPOOLFILE:
        spoolFile = sample
      spoolFilePath = os.path.join(spoolDir, spoolFile)
      
      ## Set up breaker
      breaker = samples[app][sample]['breaker']
      try:
        breakerRE = re.compile(breaker)
      except:
        breakerRE = re.compile(DEFAULT_BREAKER)
      
      ## Set up count
      count = int(samples[app][sample]['count'])

          ## Set up tokens
      earliest = samples[app][sample]['earliest']
      latest = samples[app][sample]['latest']
      tokens = []
                
      if samples[app][sample].has_key('tokens'):
        tokens = samples[app][sample]['tokens']
      
      ## Create sampleLines
      sampleFH.seek(0)
      sampleLines = sampleFH.readlines()
      
      ## Create events array
      events = []
      event = ''
      
      ##  Fill events array from breaker and sampleLines
      breakersFound = 0
      x = 0
      while len(events) < count and x < len(sampleLines):
        breakerMatch = breakerRE.search(sampleLines[x])
        
        if breakerMatch:
          ## If not first
          if breakersFound != 0:
            events.append(event)
            event = ''
          breakersFound += 1
          
        event += sampleLines[x]
        x += 1
        
      ## If events < count append remaining data in samples
      if len(events) < count:
        events.append(event + '\n')
        
      ## If breaker wasn't found in sample
      ## events = sample
      if breakersFound == 0:
        sampleFH.seek(0)
        events = sampleFH.readlines()
      
      ## If count != DEFAULT_COUNT and events < count; fill events up to count
      if count != DEFAULT_COUNT:
        x = len(events)
        while len(events) < count:
          y = 0
          while len(events) < count and y < x:
            events.append(events[y])
            y += 1
      
      ## Iterate events
      for x in range(0, len(events)):
        event = events[x]
        
        ## Iterate tokens
        for token in tokens:
          offset = 0
          tokenRE = re.compile(token[0])
          tokenMatch = tokenRE.finditer(event)
          
          ## If tokenMatch
          if tokenMatch:
            ## Set up replacement
            replacement = getReplacement(old=None, tokenArr=token, earliest=earliest, latest=latest, sessionKey=sessionKey)
            
            if replacement != None:    
              ## Iterate matches
              for match in tokenMatch:
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
                
                event = startEvent + replacement + endEvent
        
        workingFH.write(event)
                   
      ## Close file handles
      sampleFH.close()
      workingFH.close()
      
      ## Move file to spool
      shutil.move(workingFilePath, spoolFilePath)
      
      
if __name__ == '__main__':
  debug = False
  
  ## Get session key sent from splunkd
  sessionKey = sys.stdin.readline().strip()
          
  if len(sessionKey) == 0:
    sys.stderr.write("Did not receive a session key from splunkd. " +
            "Please enable passAuth in inputs.conf for this " +
            "script\n")
    exit(2)
    
  elif sessionKey == 'debug':
    debug = True
    sessionKey = auth.getSessionKey('admin', 'changeme')

  ## Get eventgen configurations
  confDict = entity.getEntities('configs/eventgen', count=-1, sessionKey=sessionKey)
  
  samples = {}
  if confDict != None:
    ## Get samples
    samples = getSamples(confDict)
  
    ## Flatten configs
    samples = flattenConf(confDict, samples)

    ## Print configs
    #for app in samples:
    #  for sample in samples[app]:
    #    print '\n[' + sample + ']'
    #    for k, v in samples[app][sample].items():
    #      print k + ': ' 
    #      print v
 
    ## Initialize timer objects arr
    sampleTimers = []
 
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
            t = threading.Timer(interval, genSample(app, sample, sessionKey=sessionKey))
          
            if t:
              sampleTimers.append(t)
    
    ## Start the timers
    if not debug:        
      first = True
      while (1):
        if first:
          for sampleTimer in sampleTimers:
            sampleTimer.start()
          first = False
        wait(600)