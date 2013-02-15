from __future__ import division
from ConfigParser import ConfigParser
import os
import datetime
import sys
import re
import __main__
import logging, logging.handlers
import json
import pprint
import copy
from eventgensamples import Sample, Token
import urllib

# 5/10/12 CS Some people consider Singleton to be lazy.  Dunno, I like it for convenience.
# My general thought on that sort of stuff is if you don't like it, reimplement it.  I'll consider
# your patch.
class Config:
    """Reads configuration from files or Splunk REST endpoint and stores them in a 'Borg' global.
    Borg is a variation on the Singleton design pattern which allows us to continually instantiate
    the configuration object throughout the application and maintain state."""
    # Stolen from http://code.activestate.com/recipes/66531/
    # This implements a Borg patterns, similar to Singleton
    # It allows numerous instantiations but always shared state
    __sharedState = {}
    
    # Internal vars
    _firsttime = True
    _confDict = None
    _isOwnApp = False
    
    # Externally used vars
    debug = False
    runOnce = False
    splunkEmbedded = False
    sessionKey = None
    grandparentdir = None
    greatgrandparentdir = None
    samples = [ ]
    sampleDir = None
    
    # Config file options.  We do not define defaults here, rather we pull them in
    # from either the eventgen.conf in the SA-Eventgen app (embedded)
    # or the eventgen_defaults file in the lib directory (standalone)
    # These are only options which are valid in the 'global' stanza
    # 5/22 CS Except for blacklist, we define that in code, since splunk complains about it in
    # the config files
    disabled = None
    blacklist = ".*\.part"
    spoolDir = None
    spoolFile = None
    breaker = None
    sampletype = None
    interval = None
    delay = None
    count = None
    bundlelines = None
    earliest = None
    latest = None
    hourOfDayRate = None
    dayOfWeekRate = None
    randomizeCount = None
    randomizeEvents = None
    outputMode = None
    fileName = None
    fileMaxBytes = None
    fileBackupFiles = None
    splunkPort = None
    splunkMethod = None
    index = None
    source = None
    host = None
    hostRegex = None
    sourcetype = None
    projectID = None
    accessToken = None
    mode = None
    backfill = None
    backfillSearch = None
    backfillSearchUrl = None
    minuteOfHourRate = None
    timezone = datetime.timedelta(days=1)

    ## Validations
    _validSettings = ['disabled', 'blacklist', 'spoolDir', 'spoolFile', 'breaker', 'sampletype' , 'interval',
                    'delay', 'count', 'bundlelines', 'earliest', 'latest', 'eai:acl', 'hourOfDayRate', 
                    'dayOfWeekRate', 'randomizeCount', 'randomizeEvents', 'outputMode', 'fileName', 'fileMaxBytes', 
                    'fileBackupFiles', 'splunkHost', 'splunkPort', 'splunkMethod', 'splunkUser', 'splunkPass',
                    'index', 'source', 'sourcetype', 'host', 'hostRegex', 'projectID', 'accessToken', 'mode',
                    'backfill', 'backfillSearch', 'eai:userName', 'eai:appName', 'timeMultiple', 'debug', 
                    'minuteOfHourRate', 'timezone']
    _validTokenTypes = {'token': 0, 'replacementType': 1, 'replacement': 2}
    _validHostTokens = {'token': 0, 'replacement': 1}
    _validReplacementTypes = ['static', 'timestamp', 'replaytimestamp', 'random', 'rated', 'file', 'mvfile', 'integerid']
    _validOutputModes = ['spool', 'file', 'splunkstream', 'stormstream']
    _validSplunkMethods = ['http', 'https']
    _validSampleTypes = ['raw', 'csv']
    _validModes = ['sample', 'replay']
    _intSettings = ['interval', 'count', 'fileMaxBytes', 'fileBackupFiles', 'splunkPort']
    _floatSettings = ['randomizeCount', 'delay', 'timeMultiple']
    _boolSettings = ['disabled', 'randomizeEvents', 'bundlelines']
    _jsonSettings = ['hourOfDayRate', 'dayOfWeekRate', 'minuteOfHourRate']
    _defaultableSettings = ['disabled', 'spoolDir', 'spoolFile', 'breaker', 'sampletype', 'interval', 'delay', 
                            'count', 'bundlelines', 'earliest', 'latest', 'hourOfDayRate', 'dayOfWeekRate', 
                            'randomizeCount', 'randomizeEvents', 'outputMode', 'fileMaxBytes', 'fileBackupFiles',
                            'splunkPort', 'splunkMethod', 'index', 'source', 'sourcetype', 'host', 'hostRegex',
                            'projectID', 'accessToken', 'mode', 'minuteOfHourRate', 'timeMultiple']
    
    def __init__(self):
        """Setup Config object.  Sets up Logging and path related variables."""
        # Rebind the internal datastore of the class to an Instance variable
        self.__dict__ = self.__sharedState
        if self._firsttime:
            # Setup logger
            logger = logging.getLogger('eventgen')
            logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
            logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            streamHandler = logging.StreamHandler(sys.stdout)
            streamHandler.setFormatter(formatter)
            logger.addHandler(streamHandler)
        
            # Having logger as a global is just damned convenient
            globals()['logger'] = logger
        
            # Determine some path names in our environment
            self.grandparentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.greatgrandparentdir = os.path.dirname(self.grandparentdir)
            
            # Determine if we're running as our own Splunk app or embedded in another
            appName = self.grandparentdir.split(os.sep)[-1]
            if appName == 'SA-Eventgen' or appName == 'eventgen':
                self._isOwnApp = True
            self._firsttime = False
            
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of our Config"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != 'samples' ])
        return 'Config:'+pprint.pformat(temp)+'\nSamples:\n'+pprint.pformat(self.samples)
        
    def __repr__(self):
        return self.__str__()
        
    def makeSplunkEmbedded(self, sessionKey=None, runOnce=False):
        """Setup operations for being Splunk Embedded.  This is legacy operations mode, just a little bit obfuscated now.
        We wait 5 seconds for a sessionKey or 'debug' on stdin, and if we time out then we run in standalone mode.
        If we're not Splunk embedded, we operate simpler.  No rest handler for configurations. We only read configs 
        in our parent app's directory.  In standalone mode, we read eventgen-standalone.conf and will skip eventgen.conf if
        we detect SA-Eventgen is installed. """

        fileHandler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/eventgen.log', maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fileHandler.setFormatter(formatter)
        # fileHandler.setLevel(logging.DEBUG)
        logger.handlers = [ ] # Remove existing StreamHandler if we're embedded
        logger.addHandler(fileHandler)
        logger.info("Running as Splunk embedded")
        import splunk.auth as auth
        import splunk.entity as entity
        # 5/7/12 CS For some reason Splunk will not import the modules into global in its copy of python
        # This is a hacky workaround, but it does fix the problem
        globals()['auth'] = locals()['auth']
        # globals()['bundle'] = locals()['bundle']
        globals()['entity'] = locals()['entity']
        # globals()['rest'] = locals()['rest']
        # globals()['util'] = locals()['util']

        if sessionKey == None or runOnce == True:
            self.runOnce = True
            self.sessionKey = auth.getSessionKey('admin', 'changeme')
        else:
            self.sessionKey = sessionKey
        
        self.splunkEmbedded = True
        

    def parse(self):
        """Parse configs from Splunk REST Handler or from files.
        We get called manually instead of in __init__ because we need find out if we're Splunk embedded before
        we figure out how to configure ourselves.    
        """
        logger.debug("Parsing configuration files.")
        self._buildConfDict()
        # Set defaults config instance variables to 'global' section
        # This establishes defaults for other stanza settings
        for key, value in self._confDict['global'].items():
            value = self._validateSetting('global', key, value)
            setattr(self, key, value)
            
        del self._confDict['global']
        if 'default' in self._confDict:
            del self._confDict['default']
        
        tempsamples = [ ]
        tempsamples2 = [ ]
        
        # Now iterate for the rest of the samples we've found
        # We'll create Sample objects for each of them
        for stanza, settings in self._confDict.items():
            sampleexists = False
            for sample in self.samples:
                if sample.name == stanza:
                    sampleexists = True
            
            # If we see the sample in two places, use the first and ignore the second     
            if not sampleexists:
                s = Sample(stanza)
                for key, value in settings.items():
                    oldvalue = value
                    try:
                        value = self._validateSetting(stanza, key, value)
                    except ValueError:
                        # If we're improperly formatted, skip to the next item
                        continue
                    # If we're a tuple, then this must be a token
                    if type(value) == tuple:
                        # Token indices could be out of order, so we must check to
                        # see whether we have enough items in the list to update the token
                        # In general this will keep growing the list by whatever length we need
                        if(key.find("host.") > -1):
                            # logger.info("hostToken.{} = {}".format(value[1],oldvalue))
                            if not isinstance(s.hostToken, Token):
                                s.hostToken = Token(s)
                                # default hard-coded for host replacement
                                s.hostToken.replacementType = 'file'
                            setattr(s.hostToken, value[0], oldvalue)
                        else:
                            if len(s.tokens) <= value[0]:
                                x = (value[0]+1) - len(s.tokens)
                                s.tokens.extend([None for i in xrange(0, x)])
                            if not isinstance(s.tokens[value[0]], Token):
                                s.tokens[value[0]] = Token(s)
                            # logger.info("token[{}].{} = {}".format(value[0],value[1],oldvalue))
                            setattr(s.tokens[value[0]], value[1], oldvalue)
                    elif key == 'eai:acl':
                        setattr(s, 'app', value['app'])         
                    else:
                        setattr(s, key, value)
                        # 6/22/12 CS Need a way to show a setting was set by the original
                        # config read
                        s._lockedSettings.append(key)
                        # logger.debug("Appending '%s' to locked settings for sample '%s'" % (key, s.name))
                        
                        
                # Validate all the tokens are fully setup, can't do this in _validateSettings
                # because they come over multiple lines
                # Don't error out at this point, just log it and remove the token and move on
                deleteidx = [ ]
                for i in xrange(0, len(s.tokens)):
                    t = s.tokens[i]
                    # If the index doesn't exist at all
                    if t == None:
                        logger.info("Token at index %s invalid" % i)
                        # Can't modify list in place while we're looping through it
                        # so create a list to remove later
                        deleteidx.append(i)
                    elif t.token == None or t.replacementType == None or t.replacement == None:
                        logger.info("Token at index %s invalid" % i)
                        deleteidx.append(i)
                newtokens = [ ]
                for i in xrange(0, len(s.tokens)):
                    if i not in deleteidx:
                        newtokens.append(s.tokens[i])
                s.tokens = newtokens
                
                # Must have eai:acl key to determine app name which determines where actual files are
                if s.app == None:
                    logger.error("App not set for sample '%s' in stanza '%s'" % (s.name, stanza))
                    raise ValueError("App not set for sample '%s' in stanza '%s'" % (s.name, stanza))
                
                # Set defaults for items not included in the config file
                for setting in self._defaultableSettings:
                    if getattr(s, setting) == None:
                        setattr(s, setting, getattr(self, setting))
                
                # Append to temporary holding list
                if not s.disabled:
                    s._priority = len(tempsamples)+1
                    tempsamples.append(s)
        
        # 6/22/12 CS Rewriting the config matching code yet again to handling flattening better.
        # In this case, we're now going to match all the files first, create a sample for each of them
        # and then take the match from the sample seen last in the config file, and apply settings from
        # every other match to that one.
        for s in tempsamples:
            # Now we need to match this up to real files.  May generate multiple copies of the sample.
            foundFiles = [ ]
            
            if self.splunkEmbedded and self._isOwnApp:
                self.sampleDir = os.path.join(self.greatgrandparentdir, s.app, 'samples')
            else:
                self.sampleDir = os.path.join(os.getcwd(), 'samples')
                if not os.path.exists(self.sampleDir):
                    newSampleDir = os.path.join(os.sep.join(os.getcwd().split(os.sep)[:-1]), 'samples')
                    logger.error("Path not found for samples '%s', trying '%s'" % (self.sampleDir, newSampleDir))
                    self.sampleDir = newSampleDir

                    if not os.path.exists(self.sampleDir):
                        newSampleDir = self.sampleDir = os.path.join(self.grandparentdir, 'samples')
                        logger.error("Path not found for samples '%s', trying '%s'" % (self.sampleDir, newSampleDir))
                        self.sampleDir = newSampleDir

            # Now that we know where samples will be written, 
            # Loop through tokens and load state for any that are integerid replacementType
            for token in s.tokens:
                if token.replacementType == 'integerid':
                    try:
                        stateFile = open(os.path.join(self.sampleDir, 'state.'+urllib.pathname2url(token.token)), 'rU')
                        token.replacement = stateFile.read()
                        stateFile.close()
                    # The file doesn't exist, use the default value in the config
                    except (IOError, ValueError):
                        token.replacement = token.replacement


            if os.path.exists(self.sampleDir):
                sampleFiles = os.listdir(self.sampleDir)
                for sample in sampleFiles:
                    results = re.match(s.name, sample)
                    if results != None:
                        samplePath = os.path.join(self.sampleDir, sample)
                        if os.path.isfile(samplePath):
                            logger.debug("Found sample file '%s' for app '%s' using config '%s' with priority '%s'; adding to list" \
                                % (sample, s.app, s.name, s._priority) )
                            foundFiles.append(samplePath)
            # If we didn't find any files, log about it
            if len(foundFiles) == 0:
                logger.error("Sample '%s' in config but no matching files" % s.name)
            for f in foundFiles:
                news = copy.deepcopy(s)
                news.filePath = f
                # Override <SAMPLE> with real name
                if s.outputMode == 'spool' and s.spoolFile == self.spoolFile:
                    news.spoolFile = f.split(os.sep)[-1]
                if s.outputMode == 'file' and s.fileName == None and s.spoolFile == self.spoolFile:
                    news.fileName = os.path.join(s.spoolDir, f.split(os.sep)[-1])
                elif s.outputMode == 'file' and s.fileName == None and s.spoolFile != None:
                    news.fileName = os.path.join(s.spoolDir, s.spoolFile)
                # Override s.name with file name.  Usually they'll match unless we've been a regex
                # 6/22/12 CS Save original name for later matching
                news._origName = news.name
                news.name = f.split(os.sep)[-1]
                if not news.disabled:
                    tempsamples2.append(news)
                else:
                    logger.info("Sample '%s' for app '%s' is marked disabled." % (news.name, news.app))

        # Clear tempsamples, we're going to reuse it
        tempsamples = [ ]

        # We're now going go through the samples and attempt to apply any matches from other stanzas
        # This allows us to specify a wildcard at the beginning of the file and get more specific as we go on
        
        # Loop through all samples, create a list of the master samples
        for s in tempsamples2:
            foundHigherPriority = False
            othermatches = [ ]
            # If we're an exact match, don't go looking for higher priorities
            if not s.name == s._origName:
                for matchs in tempsamples2:
                    if matchs.filePath == s.filePath and s._origName != matchs._origName:
                        # We have a match, now determine if we're higher priority or not
                            # If this is a longer pattern or our match is an exact match
                            # then we're a higher priority match
                        if len(matchs._origName) > len(s._origName) or matchs.name == matchs._origName:     
                            # if s._priority < matchs._priority:
                            logger.debug("Found higher priority for sample '%s' with priority '%s' from sample '%s' with priority '%s'" \
                                        % (s._origName, s._priority, matchs._origName, matchs._priority))
                            foundHigherPriority = True
                            break
                        else:
                            othermatches.append(matchs._origName)
            if not foundHigherPriority:
                logger.debug("Chose sample '%s' from samples '%s' for file '%s'" \
                            % (s._origName, othermatches, s.name))
                tempsamples.append(s)

        # Now we have two lists, tempsamples which contains only the highest priority matches, and
        # tempsamples2 which contains all matches.  We need to now flatten the config in order to
        # take all the configs which might match.

        # Reversing tempsamples2 in order to look from the bottom of the file towards the top
        # We want entries lower in the file to override entries higher in the file

        tempsamples2.reverse()

        # Loop through all samples
        for s in tempsamples:
            # Now loop through the samples we've matched with files to see if we apply to any of them
            for overridesample in tempsamples2:
                if s.filePath == overridesample.filePath and s._origName != overridesample._origName:
                    # Now we're going to loop through all valid settings and set them assuming
                    # the more specific object that we've matched doesn't already have them set
                    for settingname in self._validSettings:
                        if settingname not in ['eai:acl', 'blacklist', 'disabled', 'name']:
                            sourcesetting = getattr(overridesample, settingname)
                            destsetting = getattr(s, settingname)
                            # We want to check that the setting we're copying to hasn't been
                            # set, otherwise keep the more specific value
                            # 6/22/12 CS Added support for non-overrideable (locked) settings
                            # logger.debug("Locked settings: %s" % pprint.pformat(matchs._lockedSettings))
                            # if settingname in matchs._lockedSettings:
                            #     logger.debug("Matched setting '%s' in sample '%s' lockedSettings" \
                            #         % (settingname, matchs.name))
                            if (destsetting == None or destsetting == getattr(self, settingname)) \
                                    and sourcesetting != None and sourcesetting != getattr(self, settingname) \
                                    and not settingname in s._lockedSettings:
                                logger.debug("Overriding setting '%s' with value '%s' from sample '%s' to sample '%s' in app '%s'" \
                                                % (settingname, sourcesetting, overridesample._origName, s.name, s.app))
                                setattr(s, settingname, sourcesetting)
                    
                    # Now prepend all the tokens to the beginning of the list so they'll be sure to match first
                    newtokens = copy.deepcopy(s.tokens)
                    # logger.debug("Prepending tokens from sample '%s' to sample '%s' in app '%s': %s" \
                    #             % (overridesample._origName, s.name, s.app, pprint.pformat(newtokens)))
                    newtokens.extend(copy.deepcopy(overridesample.tokens))
                    s.tokens = newtokens
        
        # We've added replay mode, so lets loop through the samples again and set the earliest and latest
        # settings for any samples that were set to replay mode
        for s in tempsamples:
            if s.mode == 'replay':
                logger.debug("Setting defaults for replay samples")
                s.earliest = 'now'
                s.latest = 'now'
                s.count = 1
                s.randomizeCount = None
                s.hourOfDayRate = None
                s.dayOfWeekRate = None
                s.minuteOfHourRate = None
                s.interval = 0

        self.samples = tempsamples
        self._confDict = None

        logger.debug("Finished parsing.  Config str:\n%s" % self)
                
            
        
    def _validateSetting(self, stanza, key, value):
        """Validates settings to ensure they won't cause errors further down the line.
        Returns a parsed value (if the value is something other than a string).
        If we've read a token, which is a complex config, returns a tuple of parsed values."""
        logger.debug("Validating setting for '%s' with value '%s' in stanza '%s'" % (key, value, stanza))
        if key.find('token.') > -1:
            results = re.match('token\.(\d+)\.(\w+)', key)
            if results != None:
                groups = results.groups()
                if groups[1] not in self._validTokenTypes:
                    logger.error("Could not parse token index '%s' token type '%s' in stanza '%s'" % \
                                    (groups[0], groups[1], stanza))
                    raise ValueError("Could not parse token index '%s' token type '%s' in stanza '%s'" % \
                                    (groups[0], groups[1], stanza))
                if groups[1] == 'replacementType':
                    if value not in self._validReplacementTypes:
                        logger.error("Invalid replacementType '%s' for token index '%s' in stanza '%s'" % \
                                    (value, groups[0], stanza))
                        raise ValueError("Could not parse token index '%s' token type '%s' in stanza '%s'" % \
                                    (groups[0], groups[1], stanza))
                return (int(groups[0]), groups[1])
        elif key.find('host.') > -1:
            results = re.match('host\.(\w+)', key)
            if results != None:
                groups = results.groups()
                if groups[0] not in self._validHostTokens:
                    logger.error("Could not parse host token type '%s' in stanza '%s'" % (groups[0], stanza))
                    raise ValueError("Could not parse host token type '%s' in stanza '%s'" % (groups[0], stanza))
                return (groups[0], value)
        elif key in self._validSettings:
            if key in self._intSettings:
                try:
                    value = int(value)
                except:
                    logger.error("Could not parse int for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse int for '%s' in stanza '%s'" % (key, stanza))
            elif key in self._floatSettings:
                try:
                    value = float(value)
                except:
                    logger.error("Could not parse float for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse float for '%s' in stanza '%s'" % (key, stanza))
            elif key in self._boolSettings:
                try:
                    # Splunk gives these to us as a string '0' which bool thinks is True
                    # ConfigParser gives 'false', so adding more strings
                    if value in ('0', 'false', 'False'):
                        value = 0
                    value = bool(value)
                except:
                    logger.error("Could not parse bool for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse bool for '%s' in stanza '%s'" % (key, stanza))
            elif key in self._jsonSettings:
                try:
                    value = json.loads(value)
                except:
                    logger.error("Could not parse json for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse json for '%s' in stanza '%s'" % (key, stanza))
            elif key == 'outputMode':
                if not value in self._validOutputModes:
                    logger.error("outputMode invalid in stanza '%s'" % stanza)
                    raise ValueError("outputMode invalid in stanza '%s'" % stanza)
            elif key == 'splunkMethod':
                if not value in self._validSplunkMethods:
                    logger.error("splunkMethod invalid in stanza '%s'" % stanza)
                    raise ValueError("splunkMethod invalid in stanza '%s'" % stanza)
            elif key == 'sampletype':
                if not value in self._validSampleTypes:
                    logger.error("sampletype is invalid in stanza '%s'" % stanza)
                    raise ValueError("sampletype is invalid in stanza '%s'" % stanza)
            elif key == 'mode':
                if not value in self._validModes:
                    logger.error("mode is invalid in stanza '%s'" % stanza)
                    raise ValueError("mode is invalid in stanza '%s'" % stanza)
            elif key == 'timezone':
                logger.info("Parsing timezone '%s' for stanza '%s'" % (value, stanza))
                if value.find('local') >= 0:
                    value = datetime.timedelta(days=1)
                else:
                    try:
                        # Separate the hours and minutes (note: minutes = the int value - the hour portion)
                        if int(value) > 0:
                            mod = 100
                        else:
                            mod = -100
                        value = datetime.timedelta(hours=int(int(value) / 100.0), minutes=int(value) % mod )
                    except:
                        logger.error("Could not parse timezone '%s' for '%s' in stanza '%s'" % (value, key, stanza))
                        raise ValueError("Could not parse timezone '%s' for '%s' in stanza '%s'" % (value, key, stanza))
                logger.info("Parsed timezone '%s' for stanza '%s'" % (value, stanza))
        else:
            # Notifying only if the setting isn't valid and continuing on
            # This will allow future settings to be added and be backwards compatible
            logger.warn("Key '%s' in stanza '%s' is not a valid setting" % (key, stanza))
        return value
    
    def _buildConfDict(self):
        """Build configuration dictionary that we will use """
        if self.splunkEmbedded and self._isOwnApp:
            logger.info('Retrieving eventgen configurations from /configs/eventgen')
            self._confDict = entity.getEntities('configs/eventgen', count=-1, sessionKey=self.sessionKey)
        else:
            logger.info('Retrieving eventgen configurations with ConfigParser()')
            # We assume we're in a bin directory and that there are default and local directories
            conf = ConfigParser()
            # Make case sensitive
            conf.optionxform = str
            currentdir = os.getcwd()
    
            # If we're running standalone (and thusly using configParser)
            # only pick up eventgen-standalone.conf.
            conffiles = [ ]
            if len(sys.argv) > 1:
                if len(sys.argv[1]) > 0:
                    if os.path.exists(sys.argv[1]):
                        conffiles = [os.path.join(self.grandparentdir, 'default', 'eventgen.conf'),
                                    sys.argv[1]]
            if len(conffiles) == 0:
                conffiles = [os.path.join(self.grandparentdir, 'default', 'eventgen.conf'),
                            os.path.join(self.grandparentdir, 'local', 'eventgen.conf')]

            logger.debug('Reading configuration files for non-splunkembedded: %s' % conffiles)
            conf.read(conffiles)
                
            sections = conf.sections()
            ret = { }
            orig = { }
            for section in sections:
                ret[section] = dict(conf.items(section))
                # For compatibility with Splunk's configs, need to add the app name to an eai:acl key
                ret[section]['eai:acl'] = { 'app': self.grandparentdir.split(os.sep)[-1] }
                # orig[section] = dict(conf.items(section))
                # ret[section] = { }
                # for item in orig[section]:
                #     results = re.match('(token\.\d+)\.(\w+)', item)
                #     if results != None:
                #         ret[section][item] = orig[section][item]
                #     else:
                #         if item.lower() in [x.lower() for x in self._validSettings]:
                #             newitem = self._validSettings[[x.lower() for x in self._validSettings].index(item.lower())]
                #         ret[section][newitem] = orig[section][item]
            self._confDict = ret

        # Have to look in the data structure before normalization between what Splunk returns
        # versus what ConfigParser returns.
        if self._confDict['global']['debug'].lower() == 'true' \
                or self._confDict['global']['debug'].lower() == '1':
            logger.setLevel(logging.DEBUG)
        logger.debug("ConfDict returned %s" % pprint.pformat(dict(self._confDict)))
            