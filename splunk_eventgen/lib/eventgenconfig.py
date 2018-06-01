from __future__ import division
from ConfigParser import ConfigParser
import os
import datetime
import re
import logging, logging.handlers
import json
import pprint
from eventgensamples import Sample
from eventgentoken import Token
from eventgenexceptions import PluginNotLoaded, FailedLoadingPlugin
import urllib
import types
import random

# 4/21/14 CS  Adding a defined constant whether we're running in standalone mode or not
#             Standalone mode is when we know we're Splunk embedded but we want to force
#             configs to be read from a file instead of via Splunk's REST endpoint.
#             This is used in the OIDemo and others for embedding the eventgen into an
#             application.  We want to ensure we're reading from files.  It is the app's
#             responsibility to ensure eventgen.conf settings are not exported to where
#             SA-Eventgen can see them.
#
#             The reason this is a constant instead of a config setting is we must know
#             this before we read any config and we cannot use a command line parameter
#             because we interpret all those as config overrides.

STANDALONE = False

# 5/10/12 CS Some people consider Singleton to be lazy.  Dunno, I like it for convenience.
# My general thought on that sort of stuff is if you don't like it, reimplement it.  I'll consider
# your patch.
class Config(object):
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

    # Externally used vars
    debug = False
    verbose = False
    splunkEmbedded = False
    sessionKey = None
    grandparentdir = None
    greatgrandparentdir = None
    samples = [ ]
    sampleDir = None
    outputWorkers = None
    generatorWorkers = None
    sampleTimers = [ ]

    # Config file options.  We do not define defaults here, rather we pull them in
    # from eventgen.conf.
    # These are only options which are valid in the 'global' stanza
    # 5/22 CS Except for blacklist, we define that in code, since splunk complains about it in
    # the config files
    threading = None
    disabled = None
    blacklist = ".*\.part"

    __generatorworkers = [ ]
    __outputworkers = [ ]
    outputPlugins = { }
    plugins = { }
    outputQueue = None
    generatorQueue = None
    args = None

    ## Validations
    _validSettings = ['disabled', 'blacklist', 'spoolDir', 'spoolFile', 'breaker', 'sampletype' , 'interval',
                    'delay', 'count', 'bundlelines', 'earliest', 'latest', 'eai:acl', 'hourOfDayRate',
                    'dayOfWeekRate', 'randomizeCount', 'randomizeEvents', 'outputMode', 'fileName', 'fileMaxBytes',
                    'fileBackupFiles', 'index', 'source', 'sourcetype', 'host', 'hostRegex', 'projectID', 'accessToken',
                    'mode', 'backfill', 'backfillSearch', 'eai:userName', 'eai:appName', 'timeMultiple', 'debug',
                    'minuteOfHourRate', 'timezone', 'dayOfMonthRate', 'monthOfYearRate', 'perDayVolume',
                    'outputWorkers', 'generator', 'rater', 'generatorWorkers', 'timeField', 'sampleDir', 'threading',
                    'profiler', 'maxIntervalsBeforeFlush', 'maxQueueLength', 'splunkMethod', 'splunkPort',
                    'verbose', 'useOutputQueue', 'seed','end', 'autotimestamps', 'autotimestamp', 'httpeventWaitResponse']
    _validTokenTypes = {'token': 0, 'replacementType': 1, 'replacement': 2}
    _validHostTokens = {'token': 0, 'replacement': 1}
    _validReplacementTypes = ['static', 'timestamp', 'replaytimestamp', 'random', 'rated', 'file', 'mvfile', 'integerid']
    validOutputModes = [ ]
    _intSettings = ['interval', 'outputWorkers', 'generatorWorkers', 'maxIntervalsBeforeFlush', 'maxQueueLength']
    _floatSettings = ['randomizeCount', 'delay', 'timeMultiple']
    _boolSettings = ['disabled', 'randomizeEvents', 'bundlelines', 'profiler', 'useOutputQueue', 'autotimestamp', 'httpeventWaitResponse']
    _jsonSettings = ['hourOfDayRate', 'dayOfWeekRate', 'minuteOfHourRate', 'dayOfMonthRate', 'monthOfYearRate', 'autotimestamps']
    _defaultableSettings = ['disabled', 'spoolDir', 'spoolFile', 'breaker', 'sampletype', 'interval', 'delay',
                            'count', 'bundlelines', 'earliest', 'latest', 'hourOfDayRate', 'dayOfWeekRate',
                            'randomizeCount', 'randomizeEvents', 'outputMode', 'fileMaxBytes', 'fileBackupFiles',
                            'splunkHost', 'splunkPort', 'splunkMethod', 'index', 'source', 'sourcetype', 'host', 'hostRegex',
                            'projectID', 'accessToken', 'mode', 'minuteOfHourRate', 'timeMultiple', 'dayOfMonthRate',
                            'monthOfYearRate', 'perDayVolume', 'sessionKey', 'generator', 'rater', 'timeField', 'maxQueueLength',
                            'maxIntervalsBeforeFlush', 'autotimestamp']
    _complexSettings = { 'sampletype': ['raw', 'csv'],
                         'mode': ['sample', 'replay'],
                         'threading': ['thread', 'process']}

    def __init__(self, configfile=None, sample=None, override_outputter=False, override_count=False,
                 override_interval=False, override_backfill=False, override_end=False,
                 threading="thread", override_generators=None, override_outputqueue=False,
                 profiler=False):
        """Setup Config object.  Sets up Logging and path related variables."""
        # Rebind the internal datastore of the class to an Instance variable
        self.__dict__ = self.__sharedState
        self.configfile = configfile
        self.sample = sample
        self.threading = threading
        self.extraplugins = []
        self.profiler = profiler
        self.override_outputter = override_outputter
        self.override_count = override_count
        self.override_interval = override_interval
        self.override_backfill = override_backfill
        self.override_end = override_end
        self._setup_logging()
        if override_generators >= 0:
            self.generatorWorkers = override_generators
        if override_outputqueue:
            self.useOutputQueue = False

        if self._firsttime:
            # Determine some path names in our environment
            self.grandparentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.greatgrandparentdir = os.path.dirname(self.grandparentdir)

            # 1/11/14 CS Adding a initial config parsing step (this does this twice now, oh well, just runs once
            # per execution) so that I can get config before calling parse()

            c = ConfigParser()
            c.optionxform = str
            c.read([os.path.join(self.grandparentdir, 'default', 'eventgen.conf')])

            self._complexSettings['timezone'] = self._validateTimezone

            self._complexSettings['count'] = self._validateCount

            self._complexSettings['seed'] = self._validateSeed

            self.stopping = False

            #self.copyLock = threading.Lock() if self.threading == 'thread' else multiprocessing.Lock()

            self._firsttime = False

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of our Config"""
        # Filter items from config we don't want to pretty print
        filter_list = [ 'samples', 'sampleTimers', '__generatorworkers', '__outputworkers' ]
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key not in filter_list ])

        return 'Config:'+pprint.pformat(temp)+'\nSamples:\n'+pprint.pformat(self.samples)

    # loggers can't be pickled due to the lock object, remove them before we try to pickle anything.
    def __getstate__(self):
        temp = self.__dict__
        if getattr(self, 'logger', None):
            temp.pop('logger', None)
        return temp

    def __setstate__(self, d):
        self.__dict__ = d
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')

    def getPlugin(self, name, s=None):
        """Return a reference to a Python object (not an instance) referenced by passed name"""

        '''
        APPPERF-263:
        make sure we look in __outputPlugins as well. For some reason we
        keep 2 separate dicts of plugins.
        '''
        if not name in self.plugins and not name in self.outputPlugins:
            # 2/1/15 CS If we haven't already seen the plugin, try to load it
            # Note, this will only work for plugins which do not specify config validation
            # parameters.  If they do, configs may not validate for user provided plugins.
            if s:
                for plugintype in ['generator', 'rater', 'output']:
                    if plugintype in ('generator', 'rater'):
                        plugin = getattr(s, plugintype)
                    else:
                        plugin = getattr(s, 'outputMode')
                    if plugin != None:
                        self.logger.debug("Attempting to dynamically load plugintype '%s' named '%s' for sample '%s'"
                                     % (plugintype, plugin, s.name))
                        bindir = os.path.join(s.sampleDir, os.pardir, 'bin')
                        libdir = os.path.join(s.sampleDir, os.pardir, 'lib')
                        plugindir = os.path.join(libdir, 'plugins', plugintype)
                        targetplugin = PluginNotLoaded(bindir=bindir, libdir=libdir,
                                                       plugindir=plugindir, name=plugin, type=plugintype)
                        if targetplugin.name not in self.extraplugins:
                            self.extraplugins.append(targetplugin.name)
                            raise targetplugin
                        else:
                            raise FailedLoadingPlugin(name=plugin)

        # APPPERF-263: consult both __outputPlugins and __plugins
        if not name in self.plugins and not name in self.outputPlugins:
            raise KeyError('Plugin ' + name + ' not found')

        # return in order of precedence:  __plugins, __outputPlugins, None
        # Note: because of the above KeyError Exception we should never return
        # None, but it is the sane behavior for a getter method
        return self.plugins.get(name, self.outputPlugins.get(name, None))

    def makeSplunkEmbedded(self, sessionKey):
        self.sessionKey = sessionKey
        self.splunkEmbedded = True

    def getSplunkUrl(self, s):
        """
        Get Splunk URL.  If we're embedded in Splunk, get it from Splunk's Python libraries, otherwise get it from config.

        Returns a tuple of ( splunkUrl, splunkMethod, splunkHost, splunkPort )
        """
        if self.splunkEmbedded:
            try:
                import splunk.auth
                splunkUrl = splunk.auth.splunk.getLocalServerInfo()
                results = re.match('(http|https)://([^:/]+):(\d+).*', splunkUrl)
                splunkMethod = results.groups()[0]
                splunkHost = results.groups()[1]
                splunkPort = results.groups()[2]
            except:
                import traceback
                trace = traceback.format_exc()
                self.logger.error('Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s.  Stacktrace: %s' % (s.name, trace))
                raise ValueError('Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s' % s.name)
        else:
            # splunkMethod and splunkPort are defaulted so only check for splunkHost
            if s.splunkHost == None:
                self.logger.error("Splunk URL Requested but splunkHost not set for sample '%s'" % s.name)
                raise ValueError("Splunk URL Requested but splunkHost not set for sample '%s'" % s.name)

            splunkUrl = '%s://%s:%s' % (s.splunkMethod, s.splunkHost, s.splunkPort)
            splunkMethod = s.splunkMethod
            splunkHost = s.splunkHost
            splunkPort = s.splunkPort

        self.logger.debug("Getting Splunk URL: %s Method: %s Host: %s Port: %s" % (splunkUrl, splunkMethod, splunkHost, splunkPort))
        return (splunkUrl, splunkMethod, splunkHost, splunkPort)


    def parse(self):
        """Parse configs from Splunk REST Handler or from files.
        We get called manually instead of in __init__ because we need find out if we're Splunk embedded before
        we figure out how to configure ourselves.
        """
        self.samples = []
        self.logger.debug("Parsing configuration files.")
        self._buildConfDict()
        # Set defaults config instance variables to 'global' section
        # This establishes defaults for other stanza settings
        if 'global' in self._confDict:
            for key, value in self._confDict['global'].items():
                value = self._validateSetting('global', key, value)
                setattr(self, key, value)

            del self._confDict['global']
            if 'default' in self._confDict:
                del self._confDict['default']

        tempsamples = [ ]
        tempsamples2 = [ ]

        # 1/16/16 CS Trying to clean up the need to have attributes hard coded into the Config object
        # and instead go off the list of valid settings that could be set
        for setting in self._validSettings:
            if not hasattr(self, setting):
                setattr(self, setting, None)

        # Now iterate for the rest of the samples we've found
        # We'll create Sample objects for each of them
        for stanza, settings in self._confDict.items():
            if self.sample is not None and self.sample != stanza:
                self.logger.info("Skipping sample '%s' because of command line override", stanza)
                continue

            sampleexists = False
            for sample in self.samples:
                if sample.name == stanza:
                    sampleexists = True

            # If we see the sample in two places, use the first and ignore the second
            if not sampleexists:
                s = Sample(stanza)

                s.updateConfig(self)
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
                            # self.logger.info("hostToken.{} = {}".format(value[1],oldvalue))
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
                        # self.logger.debug("Appending '%s' to locked settings for sample '%s'" % (key, s.name))



                # Validate all the tokens are fully setup, can't do this in _validateSettings
                # because they come over multiple lines
                # Don't error out at this point, just log it and remove the token and move on
                deleteidx = [ ]
                for i in xrange(0, len(s.tokens)):
                    t = s.tokens[i]
                    # If the index doesn't exist at all
                    if t == None:
                        self.logger.info("Token at index %s invalid" % i)
                        # Can't modify list in place while we're looping through it
                        # so create a list to remove later
                        deleteidx.append(i)
                    elif t.token == None or t.replacementType == None or t.replacement == None:
                        self.logger.info("Token at index %s invalid" % i)
                        deleteidx.append(i)
                newtokens = [ ]
                for i in xrange(0, len(s.tokens)):
                    if i not in deleteidx:
                        newtokens.append(s.tokens[i])
                s.tokens = newtokens


                # Must have eai:acl key to determine app name which determines where actual files are
                if s.app == None:
                    self.logger.error("App not set for sample '%s' in stanza '%s'" % (s.name, stanza))
                    raise ValueError("App not set for sample '%s' in stanza '%s'" % (s.name, stanza))
                # Set defaults for items not included in the config file
                for setting in self._defaultableSettings:
                    if not hasattr(s, setting) or getattr(s, setting) == None:
                        setattr(s, setting, getattr(self, setting, None))

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

            # 1/5/14 Adding a config setting to override sample directory, primarily so I can put tests in their own
            # directories
            if s.sampleDir == None:
                self.logger.debug("Sample directory not specified in config, setting based on standard")
                if self.splunkEmbedded and not STANDALONE:
                    s.sampleDir = os.path.normpath(os.path.join(self.grandparentdir, '..', '..', '..', s.app, 'samples'))
                else:
                    # 2/1/15 CS  Adding support for looking for samples based on the config file specified on
                    # the command line.
                    if self.configfile:
                        if os.path.isdir(self.configfile):
                            s.sampleDir = os.path.join(self.configfile, 'samples')
                        else:
                            s.sampleDir = os.path.join(os.getcwd(), 'samples')
                    else:
                        s.sampleDir = os.path.join(os.getcwd(), 'samples')
                    if not os.path.exists(s.sampleDir):
                        newSampleDir = os.path.join(os.sep.join(os.getcwd().split(os.sep)[:-1]), 'samples')
                        self.logger.error("Path not found for samples '%s', trying '%s'" % (s.sampleDir, newSampleDir))
                        s.sampleDir = newSampleDir

                        if not os.path.exists(s.sampleDir):
                            newSampleDir = os.path.join(self.grandparentdir, 'samples')
                            self.logger.error("Path not found for samples '%s', trying '%s'" % (s.sampleDir, newSampleDir))
                            s.sampleDir = newSampleDir
            else:
                self.logger.debug("Sample directory specified in config, checking for relative")
                # Allow for relative paths to the base directory
                if not os.path.exists(s.sampleDir):
                    temp_sampleDir = os.path.join(self.grandparentdir, s.sampleDir)
                    # check the greatgrandparent just incase for the sample file.
                    if not os.path.exists(temp_sampleDir):
                        temp_sampleDir = os.path.join(self.greatgrandparentdir, s.sampleDir)
                    s.sampleDir = temp_sampleDir
                else:
                    s.sampleDir = s.sampleDir

            # 2/1/15 CS Adding support for command line options, specifically running a single sample
            # from the command line
                self.run_sample = True
                if self.run_sample:
                    # Name doesn't match, disable
                    # if s.name != self.run_sample:
                    #     self.logger.debug("Disabling sample '%s' because of command line override" % s.name)
                    #     s.disabled = True
                    # # Name matches
                    # else:
                    #     self.logger.debug("Sample '%s' selected from command line" % s.name)
                    # Also, can't backfill search if we don't know how to talk to Splunk
                    s.backfillSearch = None
                    s.backfillSearchUrl = None
                    # Since the user is running this for debug output, lets assume that they
                    # always want to see output
                    self.maxIntervalsBeforeFlush = 1
                    s.maxIntervalsBeforeFlush = 1
                    s.maxQueueLength = s.maxQueueLength or 1
                    self.logger.debug("Sample '%s' setting maxQueueLength to '%s' from command line" % (s.name, s.maxQueueLength))

                    if self.override_outputter:
                        self.logger.debug("Sample '%s' setting output to '%s' from command line" % (s.name, self.override_outputter))
                        s.outputMode = self.override_outputter

                    if self.override_count:
                        self.logger.debug("Overriding count to '%d' for sample '%s'" % (self.override_count, s.name))
                        s.count = self.override_count
                        # If we're specifying a count, turn off backfill
                        s.backfill = None

                    if self.override_interval:
                        self.logger.debug("Overriding interval to '%d' for sample '%s'" % (self.override_interval, s.name))
                        s.interval = self.override_interval

                    if self.override_backfill:
                        self.logger.debug("Overriding backfill to '%s' for sample '%s'" % (self.override_backfill, s.name))
                        s.backfill = self.override_backfill.lstrip()

                    if self.override_end:
                        self.logger.debug("Overriding end to '%s' for sample '%s'" % (self.override_end, s.name))
                        s.end = self.override_end.lstrip()

                    if s.mode == 'replay' and not s.end:
                        s.end = 1

            # Now that we know where samples will be written,
            # Loop through tokens and load state for any that are integerid replacementType
            for token in s.tokens:
                if token.replacementType == 'integerid':
                    try:
                        stateFile = open(os.path.join(s.sampleDir, 'state.'+urllib.pathname2url(token.token)), 'rU')
                        token.replacement = stateFile.read()
                        stateFile.close()
                    # The file doesn't exist, use the default value in the config
                    except (IOError, ValueError):
                        token.replacement = token.replacement


            if os.path.exists(s.sampleDir):
                sampleFiles = os.listdir(s.sampleDir)
                for sample in sampleFiles:
                    results = re.match(s.name, sample)
                    if results != None:
                        samplePath = os.path.join(s.sampleDir, sample)
                        if os.path.isfile(samplePath):
                            self.logger.debug("Found sample file '%s' for app '%s' using config '%s' with priority '%s'; adding to list" \
                                % (sample, s.app, s.name, s._priority) )
                            foundFiles.append(samplePath)
            # If we didn't find any files, log about it
            if len(foundFiles) == 0:
                self.logger.warning("Sample '%s' in config but no matching files" % s.name)
                # 1/23/14 Change in behavior, go ahead and add the sample even if we don't find a file
                # 9/16/15 Change bit us, now only append if we're a generator other than the two stock generators
                if not s.disabled and not (s.generator == "default" or s.generator == "replay"):
                    tempsamples2.append(s)
            for f in foundFiles:
                # TODO: Not sure why we use deepcopy here, seems point less.
                #news = copy.deepcopy(s)
                news = s
                news.filePath = f
                # 12/3/13 CS TODO These are hard coded but should be handled via the modular config system
                # Maybe a generic callback for all plugins which will modify sample based on the filename
                # found?
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
                    self.logger.info("Sample '%s' for app '%s' is marked disabled." % (news.name, news.app))

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
                            self.logger.debug("Found higher priority for sample '%s' with priority '%s' from sample '%s' with priority '%s'" \
                                        % (s._origName, s._priority, matchs._origName, matchs._priority))
                            foundHigherPriority = True
                            break
                        else:
                            othermatches.append(matchs._origName)
            if not foundHigherPriority:
                self.logger.debug("Chose sample '%s' from samples '%s' for file '%s'" \
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
                            # 7/16/14 CS For some reason default settings are suddenly erroring
                            # not sure why, but lets just move on
                            try:
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
                                    self.logger.debug("Overriding setting '%s' with value '%s' from sample '%s' to sample '%s' in app '%s'" \
                                                    % (settingname, sourcesetting, overridesample._origName, s.name, s.app))
                                    setattr(s, settingname, sourcesetting)
                            except AttributeError:
                                pass

                    # Now prepend all the tokens to the beginning of the list so they'll be sure to match first
                    newtokens = s.tokens
                    # self.logger.debug("Prepending tokens from sample '%s' to sample '%s' in app '%s': %s" \
                    #             % (overridesample._origName, s.name, s.app, pprint.pformat(newtokens)))
                    newtokens.extend(overridesample.tokens)
                    s.tokens = newtokens

        # We've added replay mode, so lets loop through the samples again and set the earliest and latest
        # settings for any samples that were set to replay mode
        for s in tempsamples:
            # We've added replay mode, so lets loop through the samples again and set the earliest and latest
            # settings for any samples that were set to replay mode
            if s.perDayVolume:
                self.logger.info("Stanza contains per day volume, changing rater and generator to perdayvolume instead of count")
                s.rater = 'perdayvolume'
                s.count = 1
                s.generator = 'perdayvolumegenerator'
            elif s.mode == 'replay':
                self.logger.debug("Setting defaults for replay samples")
                s.earliest = 'now'
                s.latest = 'now'
                s.count = 1
                s.randomizeCount = None
                s.hourOfDayRate = None
                s.dayOfWeekRate = None
                s.minuteOfHourRate = None
                s.interval = 0
                # 12/29/13 CS Moved replay generation to a new replay generator plugin
                s.generator = 'replay'

        self.samples = tempsamples
        self._confDict = None

        # 9/2/15 Try autotimestamp values, add a timestamp if we find one
        for s in self.samples:
            if s.generator == 'default':
                s.loadSample()

                if s.autotimestamp:
                    at = self.autotimestamps
                    line_puncts = [ ]

                    # Check for _time field, if it exists, add a timestamp to support it
                    if len(s.sampleDict) > 0:
                        if '_time' in s.sampleDict[0]:
                            self.logger.debugv("Found _time field, checking if default timestamp exists")
                            t = Token()
                            t.token = "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}"
                            t.replacementType = "timestamp"
                            t.replacement = "%Y-%m-%dT%H:%M:%S.%f"

                            found_token = False
                            # Check to see if we're already a token
                            for st in s.tokens:
                                if st.token == t.token and st.replacement == t.replacement:
                                    found_token = True
                                    break
                            if not found_token:
                                self.logger.debugv("Found _time adding timestamp to support")
                                s.tokens.append(t)
                            else:
                                self.logger.debugv("_time field exists and timestamp already configured")

                    for e in s.sampleDict:
                        # Run punct against the line, make sure we haven't seen this same pattern
                        # Not totally exact but good enough for Rock'N'Roll
                        p = self._punct(e['_raw'])
                        # self.logger.debugv("Got punct of '%s' for event '%s'" % (p, e[s.timeField]))
                        if p not in line_puncts:
                            for x in at:
                                t = Token()
                                t.token = x[0]
                                t.replacementType = "timestamp"
                                t.replacement = x[1]

                                try:
                                    # self.logger.debugv("Trying regex '%s' for format '%s' on '%s'" % (x[0], x[1], e[s.timeField]))
                                    ts = s.getTSFromEvent(e['_raw'], t)
                                    if type(ts) == datetime.datetime:
                                        found_token = False
                                        # Check to see if we're already a token
                                        for st in s.tokens:
                                            if st.token == t.token and st.replacement == t.replacement:
                                                found_token = True
                                                break
                                        if not found_token:
                                            self.logger.debugv("Found timestamp '%s', extending token with format '%s'" % (x[0], x[1]))
                                            s.tokens.append(t)
                                            # Drop this pattern from ones we try in the future
                                            at = [ z for z in at if z[0] != x[0] ]
                                        break
                                except ValueError:
                                    pass
                        line_puncts.append(p)
        self.logger.debug("Finished parsing")


    def _punct(self, string):
        """Quick method of attempting to normalize like events"""
        string = string.replace('\\', '\\\\')
        string = string.replace('"', '\\"')
        string = string.replace("'", "\\'")
        string = string.replace(" ", "_")
        string = string.replace("\t", "t")
        string = re.sub("[^,;\-#\$%&+./:=\?@\\\'|*\n\r\"(){}<>\[\]\^!]", "", string, flags=re.M)
        return string


    def _validateSetting(self, stanza, key, value):
        """Validates settings to ensure they won't cause errors further down the line.
        Returns a parsed value (if the value is something other than a string).
        If we've read a token, which is a complex config, returns a tuple of parsed values."""
        self.logger.debugv("Validating setting for '%s' with value '%s' in stanza '%s'" % (key, value, stanza))
        if key.find('token.') > -1:
            results = re.match('token\.(\d+)\.(\w+)', key)
            if results != None:
                groups = results.groups()
                if groups[1] not in self._validTokenTypes:
                    self.logger.error("Could not parse token index '%s' token type '%s' in stanza '%s'" % \
                                    (groups[0], groups[1], stanza))
                    raise ValueError("Could not parse token index '%s' token type '%s' in stanza '%s'" % \
                                    (groups[0], groups[1], stanza))
                if groups[1] == 'replacementType':
                    if value not in self._validReplacementTypes:
                        self.logger.error("Invalid replacementType '%s' for token index '%s' in stanza '%s'" % \
                                    (value, groups[0], stanza))
                        raise ValueError("Could not parse token index '%s' token type '%s' in stanza '%s'" % \
                                    (groups[0], groups[1], stanza))
                return (int(groups[0]), groups[1])
        elif key.find('host.') > -1:
            results = re.match('host\.(\w+)', key)
            if results != None:
                groups = results.groups()
                if groups[0] not in self._validHostTokens:
                    self.logger.error("Could not parse host token type '%s' in stanza '%s'" % (groups[0], stanza))
                    raise ValueError("Could not parse host token type '%s' in stanza '%s'" % (groups[0], stanza))
                return (groups[0], value)
        elif key in self._validSettings:
            if key in self._intSettings:
                try:
                    value = int(value)
                except:
                    self.logger.error("Could not parse int for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse int for '%s' in stanza '%s'" % (key, stanza))
            elif key in self._floatSettings:
                try:
                    value = float(value)
                except:
                    self.logger.error("Could not parse float for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse float for '%s' in stanza '%s'" % (key, stanza))
            elif key in self._boolSettings:
                try:
                    # Splunk gives these to us as a string '0' which bool thinks is True
                    # ConfigParser gives 'false', so adding more strings
                    if value in ('0', 'false', 'False'):
                        value = 0
                    value = bool(value)
                except:
                    self.logger.error("Could not parse bool for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse bool for '%s' in stanza '%s'" % (key, stanza))
            elif key in self._jsonSettings:
                try:
                    value = json.loads(value)
                except:
                    self.logger.error("Could not parse json for '%s' in stanza '%s'" % (key, stanza))
                    raise ValueError("Could not parse json for '%s' in stanza '%s'" % (key, stanza))
            # 12/3/13 CS Adding complex settings, which is a dictionary with the key containing
            # the config item name and the value is a list of valid values or a callback function
            # which will parse the value or raise a ValueError if it is unparseable
            elif key in self._complexSettings:
                complexSetting = self._complexSettings[key]
                self.logger.debugv("Complex setting for '%s' in stanza '%s'" % (key, stanza))
                # Set value to result of callback, e.g. parsed, or the function should raise an error
                if isinstance(complexSetting, types.FunctionType) or isinstance(complexSetting, types.MethodType):
                    self.logger.debugv("Calling function for setting '%s' with value '%s'" % (key, value))
                    value = complexSetting(value)
                elif isinstance(complexSetting, list):
                    if not value in complexSetting:
                        self.logger.error("Setting '%s' is invalid for value '%s' in stanza '%s'" % (key, value, stanza))
                        raise ValueError("Setting '%s' is invalid for value '%s' in stanza '%s'" % (key, value, stanza))
        else:
            # Notifying only if the setting isn't valid and continuing on
            # This will allow future settings to be added and be backwards compatible
            self.logger.info("Key '%s' in stanza '%s' may not be a valid setting" % (key, stanza))
        return value

    def _validateTimezone(self, value):
        """Callback for complexSetting timezone which will parse and validate the timezone"""
        self.logger.debug("Parsing timezone {}".format(value))
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
                self.logger.error("Could not parse timezone {}".format(value))
                raise ValueError("Could not parse timezone {}".format(value))
        self.logger.debug("Parsed timezone {}".format(value))
        return value

    def _validateCount(self, value):
        """Callback to override count to -1 if set to 0 in the config, otherwise return int"""
        self.logger.debug("Validating count of {}".format(value))
        # 5/13/14 CS Hack to take a zero count in the config and set it to a value which signifies
        # the special condition rather than simply being zero events, setting to -1
        try:
            value = int(value)
        except:
            self.logger.error("Could not parse int for count {}".format(value))
            raise ValueError("Could not parse int for count {}".format(value))

        if value == 0:
            value = -1
        self.logger.debug("Count set to {}".format(value))

        return value

    def _validateSeed(self, value):
        """Callback to set random seed"""
        self.logger.debug("Validating random seed {}".format(value))
        try:
            value = int(value)
        except:
            self.logger.error("Could not parse int for seed {}".format(value))
            raise ValueError("Could not parse int for seed {}".format(value))

        self.logger.info("Using random seed {}".format(value))
        random.seed(value)



    def _buildConfDict(self):
        """Build configuration dictionary that we will use """

        # Abstracts grabbing configuration from Splunk or directly from Configuration Files

        if self.splunkEmbedded and not STANDALONE:
            self.logger.info('Retrieving eventgen configurations from /configs/eventgen')
            import splunk.entity as entity
            self._confDict = entity.getEntities('configs/conf-eventgen', count=-1, sessionKey=self.sessionKey)
        else:
            self.logger.info('Retrieving eventgen configurations with ConfigParser()')
            # We assume we're in a bin directory and that there are default and local directories
            conf = ConfigParser()
            # Make case sensitive
            conf.optionxform = str
            currentdir = os.getcwd()

            conffiles = [ ]
            # 2/1/15 CS  Moving to argparse way of grabbing command line parameters
            if self.configfile:
                if os.path.exists(self.configfile):
                    # 2/1/15 CS Adding a check to see whether we're instead passed a directory
                    # In which case we'll assume it's a splunk app and look for config files in
                    # default and local
                    if os.path.isdir(self.configfile):
                        conffiles = [os.path.join(self.grandparentdir, 'default', 'eventgen.conf'),
                                os.path.join(self.configfile, 'default', 'eventgen.conf'),
                                os.path.join(self.configfile, 'local', 'eventgen.conf')]
                    else:
                        conffiles = [os.path.join(self.grandparentdir, 'default', 'eventgen.conf'),
                                self.configfile]
            if len(conffiles) == 0:
                conffiles = [os.path.join(self.grandparentdir, 'default', 'eventgen.conf'),
                            os.path.join(self.grandparentdir, 'local', 'eventgen.conf')]

            self.logger.debug('Reading configuration files for non-splunkembedded: %s' % conffiles)
            conf.read(conffiles)

            sections = conf.sections()
            ret = { }
            orig = { }
            for section in sections:
                ret[section] = dict(conf.items(section))
                # For compatibility with Splunk's configs, need to add the app name to an eai:acl key
                ret[section]['eai:acl'] = { 'app': self.grandparentdir.split(os.sep)[-1] }
            self._confDict = ret

        self.logger.debug("ConfDict returned %s" % pprint.pformat(dict(self._confDict)))
