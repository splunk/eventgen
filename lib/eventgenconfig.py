from __future__ import division
from ConfigParser import ConfigParser
import os
import re
import __main__
import logging, logging.handlers
import json
import pprint
import copy
from eventgensamples import Sample, Token

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
    splunkEmbedded = False
    sessionKey = None
    grandparentdir = None
    greatgrandparentdir = None
    samples = [ ]
    
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
    interval = None
    count = None
    earliest = None
    latest = None
    hourOfDayRate = None
    dayOfWeekRate = None
    randomizeCount = None
    outputMode = None
    fileMaxBytes = None
    fileBackupFiles = None
    splunkPort = None
    splunkMethod = None
    index = None
    source = None
    sourcetype = None

    ## Validations
    _validSettings = ['disabled', 'blacklist', 'spoolDir', 'spoolFile', 'breaker', 'interval', 'count', 'earliest', 
                    'latest', 'eai:acl', 'hourOfDayRate', 'dayOfWeekRate', 'randomizeCount', 'randomizeEvents',
                    'outputMode', 'fileName', 'fileMaxBytes', 'fileBackupFiles', 'splunkHost', 'splunkPort',
                    'splunkMethod', 'splunkUser', 'splunkPass', 'index', 'source', 'sourcetype']
    _validTokenTypes = {'token': 0, 'replacementType': 1, 'replacement': 2}
    _validReplacementTypes = ['static', 'timestamp', 'random', 'file', 'mvfile']
    _validOutputModes = ['spool', 'file', 'splunkstream']
    _validSplunkMethods = ['http', 'https']
    _intSettings = ['interval', 'count', 'fileMaxBytes', 'fileBackupFiles', 'splunkPort']
    _floatSettings = ['randomizeCount']
    _boolSettings = ['disabled', 'randomizeEvents']
    _jsonSettings = ['hourOfDayRate', 'dayOfWeekRate']
    _defaultableSettings = ['disabled', 'spoolDir', 'spoolFile', 'breaker', 'interval', 'count', 'earliest',
                            'latest', 'hourOfDayRate', 'dayOfWeekRate', 'randomizeCount', 'randomizeEvents',
                            'outputMode', 'fileMaxBytes', 'fileBackupFiles', 'splunkPort', 'splunkMethod',
                            'index', 'source', 'sourcetype']
    
    def __init__(self):
        # Rebind the internal datastore of the class to an Instance variable
        self.__dict__ = self.__sharedState
        if self._firsttime:
            # Setup logger
            logger = logging.getLogger('eventgen')
            logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
            logger.setLevel(logging.WARN)
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(formatter)
            logger.addHandler(streamHandler)
        
            # Having logger as a global is just damned convenient
            globals()['logger'] = logger
        
            self.grandparentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.greatgrandparentdir = os.path.dirname(self.grandparentdir)
            
            appName = self.grandparentdir.split(os.sep)[-1]
            if appName == 'SA-Eventgen' or appName == 'eventgen':
                self._isOwnApp = True
            self._firsttime = False
            
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of our Config"""
        return 'Config:'+pprint.pformat(self.__dict__)+'\nSamples:\n'+pprint.pformat(self.samples)
        
    def __repr__(self):
        return self.__str__()
        
    def makeSplunkEmbedded(self, sessionKey=None, debug=False):
        """Setup operations for being Splunk Embedded.  This is legacy operations mode, just a little bit obfuscated now.
        We wait 5 seconds for a sessionKey or 'debug' on stdin, and if we time out then we run in standalone mode.
        If we're not Splunk embedded, we operate simpler.  No rest handler for configurations. We only read configs 
        in our parent app's directory.  In standalone mode, we read eventgen-standalone.conf and will skip eventgen.conf if
        we detect SA-Eventgen is installed. """
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
        
        fileHandler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/eventgen.log', maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fileHandler.setFormatter(formatter)
        logger.handlers = [ ] # Remove existing StreamHandler if we're embedded
        logger.addHandler(fileHandler)
        
        if sessionKey == None or debug == True:
            self.debug = True
            self.sessionKey = auth.getSessionKey('admin', 'changeme')
        else:
            self.sessionKey = sessionKey
        
        self.splunkEmbedded = True
        

    def parse(self):
        """Parse configs from Splunk REST Handler or from files.
        We get called manually instead of in __init__ because we need find out if we're Splunk embedded before
        we figure out how to configure ourselves.
        
        Note if running as standalone (not splunk embedded) there are the following caveats:
        * Will by default read eventgen-standalone.conf in the default and local directories and not eventgen.conf
        * If we we do not see a SA-Eventgen or eventgen directory in the greatgrandparent directory
                $SPLUNK_HOME/etc/apps/<yourapp>/bin/eventgen.py
                                 ^^^^  - Great Grandparent dir       
        """
        logger.debug("Parsing configuration files.")
        self._buildConfDict()
        # Set defaults config instance variables to 'global' section
        # This establishes defaults for other stanza settings
        for key, value in self._confDict['global'].items():
            value = self._validateSetting('global', key, value)
            setattr(self, key, value)
            
        del self._confDict['global']
        
        tempsamples = [ ]
        
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
                        if len(s.tokens) <= value[0]:
                            x = (value[0]+1) - len(s.tokens)
                            s.tokens.extend([None for i in xrange(0, x)])
                        if not isinstance(s.tokens[value[0]], Token):
                            s.tokens[value[0]] = Token(s)
                        setattr(s.tokens[value[0]], value[1], oldvalue)
                    elif key == 'eai:acl':
                        setattr(s, 'app', value['app'])         
                    else:
                        setattr(s, key, value)
                        
                        
                # Validate all the tokens are fully setup, can't do this in _validateSettings
                # because they come over multiple lines
                # Don't error out at this point, just log it and remove the token and move on
                deleteidx = [ ]
                for i in xrange(0, len(s.tokens)):
                    t = s.tokens[i]
                    if t.token == None or t.replacementType == None or t.replacement == None:
                        logger.info("Token at index %s invalid" % i)
                        # Can't modify list in place while we're looping through it
                        # so create a list to remove later
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
                    tempsamples.append(s)
        
        # We're now going go through the samples and attempt to apply any matches from other stanzas
        # This allows us to specify a wildcard at the beginning of the file and get more specific as we go on
        # We're going to reverse the list and work from the bottom up.  Working in reverse also helps us later
        # as we're going to want to match at the end of the file first (because it should be the most specific)
        tempsamples.reverse()
        
        # Loop through all samples
        for s in tempsamples:
            # Now loop through the samples we've matched with files to see if we apply to any of them
            for matchs in self.samples:
                if re.match(s.name, matchs.name) != None and s.name != matchs.name:
                    # Now we're going to loop through all valid settings and set them assuming
                    # the more specific object that we've matched doesn't already have them set
                    # There's really no penalty for setting defaults again, so don't check if they're
                    # already default
                    for settingname in self._validSettings:
                        if settingname not in ['eai:acl', 'blacklist', 'disabled', 'name']:
                            sourcesetting = getattr(s, settingname)
                            destsetting = getattr(matchs, settingname)
                            # We want to check that the setting we're copying to hasn't been
                            # set, otherwise keep the more specific value
                            if (destsetting == None or destsetting == getattr(self, settingname)) \
                                    and sourcesetting != None and sourcesetting != getattr(self, settingname):
                                logger.debug("Overriding setting '%s' with value '%s' from sample '%s' to sample '%s' in app '%s'" \
                                                % (settingname, destsetting, s.name, matchs.name, s.app))
                                setattr(matchs, settingname, sourcesetting)
                    
                    # Now prepend all the tokens to the beginning of the list so they'll be sure to match first
                    newtokens = copy.deepcopy(s.tokens)
                    logger.debug("Prepending tokens from sample '%s' to sample '%s' in app '%s': %s" \
                                % (s.name, matchs.name, s.app, pprint.pformat(newtokens)))
                    newtokens.extend(matchs.tokens)
                    matchs.tokens = newtokens
                    
            # Now we need to match this up to real files.  May generate multiple copies of the sample.
            foundFiles = [ ]
            
            if self.splunkEmbedded and self._isOwnApp:
                sampleDir = os.path.join(self.greatgrandparentdir, s.app, 'samples')
            else:
                sampleDir = os.path.join(self.grandparentdir, 'samples')
                print sampleDir
            if os.path.exists(sampleDir):
                sampleFiles = os.listdir(sampleDir)
                for sample in sampleFiles:
                    results = re.match(s.name, sample)
                    if results != None:
                        samplePath = os.path.join(sampleDir, sample)
                        if os.path.isfile(samplePath):
                            logger.debug("Found sample file '%s' for app '%s' using config '%s'; adding to list" % (sample, s.app, stanza) )
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
                # Override s.name with file name.  Usually they'll match unless we've been a regex
                news.name = f.split(os.sep)[-1]
                if not s.disabled:
                    # Search to make sure we haven't already matched this file
                    sExists = False
                    for scheck in self.samples:
                        if scheck.name == news.name:
                            sExists = True
                    if not sExists:
                        self.samples.append(news)
                else:
                    logger.info("Sample '%s' for app '%s' is marked disabled." % (news.name, news.app))
        
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
            conffiles = [os.path.join(self.grandparentdir, 'lib', 'eventgen_defaults'),
                        os.path.join(self.grandparentdir, 'default', 'eventgen-standalone.conf'),
                        os.path.join(self.grandparentdir, 'local', 'eventgen-standalone.conf')]
            # If we don't see SA-Eventgen, then pick up eventgen.conf as well
            if not os.path.exists(os.path.join(self.greatgrandparentdir, 'SA-Eventgen')) \
                    and not os.path.exists(os.path.join(self.greatgrandparentdir, 'eventgen')):
                conffiles.append(os.path.join(self.grandparentdir, 'default', 'eventgen.conf'))
                conffiles.append(os.path.join(self.grandparentdir, 'local', 'eventgen.conf'))
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
        logger.debug("ConfDict returned %s" % pprint.pformat(dict(self._confDict)))
            