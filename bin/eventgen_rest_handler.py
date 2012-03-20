'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
'''
import datetime
import logging
import logging.handlers
import os
import re
import splunk.admin as admin
import splunk.entity as entity

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
tokenRex = re.compile('^token\.(\d+)\.(.*)$')
validSettings = ['spoolDir', 'spoolFile', 'breaker', 'interval', 'count', 'earliest', 'latest']
validTokenTypes = {'token': 0, 'replacementType': 1, 'replacement': 2}

## Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('eventgen_rest_handler')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/eventgen_rest_handler.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

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
    

class EventGenApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    
    def setup(self):
        #if self.requestedAction == admin.ACTION_EDIT:
        #    for arg in ['field_1', 'field_2_boolean', 'field_3']:
        #        self.supportedArgs.addOptArg(arg)
        pass

    def handleList(self, confInfo):
        
        confDict = self.readConfCtx('eventgen')
        
        if confDict != None: 
            for stanza, settings in confDict.items():
                tokens = {}
             
                for key, val in settings.items():
                    if not key.startswith('eai'):
                        tokenMatch = tokenRex.match(key)
                        
                        ## Do not append this key
                        if key == 'disabled':
                            pass
                            
                        ## If key is LINE_BREAKER
                        elif key == 'breaker':
                            ## If val
                            if val != None:
                                ## Using try/except for PCRE
                                try:
                                    breakerRE = re.compile(val)
                                
                                except:
                                    val = None
                            
                            elif stanza == 'global':
                                val = DEFAULT_BREAKER
                                
                            else:
                                pass
                                
                            if val != None: 
                                confInfo[stanza].append(key, val) 
                            
                        ## If key is interval
                        elif key == 'interval':
                            ## If val
                            if val != None:
                                ## See that val >= 0
                                try:
                                    val = int(val)
                                
                                    if val >= 0:
                                        val = str(val)
                                        
                                    ## If val is not proper
                                    else:
                                        if stanza == 'global':
                                            val = DEFAULT_INTERVAL
                                        
                                        else:
                                            val = None
                            
                                ## If val is not proper
                                except:
                                    if stanza == 'global':
                                        val = DEFAULT_INTERVAL
                                        
                                    else:
                                        val = None
                            
                            elif stanza == 'global':
                                val = DEFAULT_INTERVAL
                                
                            else:
                                pass
                            
                            if val != None: 
                                confInfo[stanza].append(key, val) 
                        
                        ## If key is count
                        elif key == 'count':
                            ## If val
                            if val != None:
                                ## See that val >= 0
                                try:
                                    val = int(val)
                                
                                    if val >= 0:
                                        val = str(val)
                                    
                                    ## If val is not proper
                                    else:
                                        if stanza == 'global':
                                            val = DEFAULT_COUNT
                                            
                                        else:
                                            val = None
                                
                                ## If val is not proper
                                except:
                                    if stanza == 'global':
                                        val = DEFAULT_COUNT
                                
                                    else:
                                        val = None
                                        
                            elif stanza == 'global':
                                val = DEFAULT_COUNT
                                
                            else:
                                pass
                                
                            if val != None:
                                confInfo[stanza].append(key, val)
                        
                        ## If key is spoolDir
                        elif key == 'spoolDir':
                            ## If val
                            if val != None:
                                if os.path.exists(pathParser(val)):
                                    pass
                                
                                else:
                                    val = None
                                                         
                            elif stanza == 'global':
                                val = DEFAULT_SPOOLDIR
                                
                            else:
                                pass
                        
                            if val != None:
                                confInfo[stanza].append(key, val)
                                
                        ## If key is spoolFile
                        elif key == 'spoolFile':
                            ## If val
                            if val != None:
                                pass
                            
                            else:
                                if stanza == 'global':
                                    val = DEFAULT_SPOOLFILE
                            
                            confInfo[stanza].append(key, val)
                                    
                        ## If key is of type token
                        elif tokenMatch:
                            tokenID = tokenMatch.group(1)
                            tokenType = tokenMatch.group(2)
                        
                            ## If token doesn't exist create empty token with valid length
                            if not tokens.has_key(tokenID):
                                tokens[tokenID] = ['']*len(validTokenTypes)
                            
                            ## If tokenType is valid set val based on tokenTypeId
                            if validTokenTypes.has_key(tokenType):
                            
                                ## If tokenType is replacementType then validate
                                if tokenType == 'replacementType':
                                    if val in DEFAULT_REPLACEMENTS:
                                        tokens[tokenID][validTokenTypes[tokenType]] = val
                                
                                else:
                                    tokens[tokenID][validTokenTypes[tokenType]] = val     
                        
                        ## If key in remainding valid settings
                        elif key in validSettings:
                            if val != None:
                                confInfo[stanza].append(key, val)
                        
                        ## If key is not proper
                        else:
                            pass
                    
                    ## Key is eai; userName/appName
                    elif key.startswith('eai') and key != 'eai:acl':
                            confInfo[stanza].append(key, val)
                    
                    ## Key is eai; Set meta    
                    else:
                        confInfo[stanza].setMetadata(key, val)
                    
                ## Validate tokens
                ## We draw the validation line @ making sure all 3 settings exist...
                ## ...Not that the replacement itself is valid
                for tokenID, token in tokens.items():
                    validToken = True

                    for tokenType, tokenTypeID in validTokenTypes.items():
                        ## If token does not have tokenType it's invalid
                        if not token[tokenTypeID]:
                            validToken = False
                            
                        else:
                            pass
                            
                    if validToken:
                        confInfo[stanza].append('token.' + tokenID, token)
                    
# initialize the handler
admin.init(EventGenApp, admin.CONTEXT_APP_AND_USER)