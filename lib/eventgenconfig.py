from __future__ import division
from ConfigParser import ConfigParser
import os
import datetime, time
import sys
import re
import __main__
import logging, logging.handlers
import traceback
import json
import pprint
import copy
from eventgensamples import Sample
from eventgentoken import Token
import urllib
import types
import random
from eventgencounter import Counter
from eventgenqueue import Queue
import threading, multiprocessing
from generatorworker import GeneratorThreadWorker, GeneratorProcessWorker
from outputworker import OutputThreadWorker, OutputProcessWorker


# 6/7/14 CS   Adding a new logger adapter class which we will use to override the formatting
#             for all messsages to include the sample they came from
class EventgenAdapter(logging.LoggerAdapter):
    """
    Pass in a sample parameter and prepend sample to all logs
    """
    def process(self, msg, kwargs):
        # Useful for multiprocess debugging to add pid, commented by default
        # return "pid=%s module='%s' sample='%s': %s" % (os.getpid(), self.extra['module'], self.extra['sample'], msg), kwargs
        return "module='%s' sample='%s': %s" % (self.extra['module'], self.extra['sample'], msg), kwargs

    def debugv(self, msg, *args, **kwargs):
        """
        Delegate a debug call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        msg, kwargs = self.process(msg, kwargs)
        self.logger.debugv(msg, *args, **kwargs)


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
    __generatorworkers = [ ]
    __outputworkers = [ ]

    # Config file options.  We do not define defaults here, rather we pull them in
    # from eventgen.conf.
    # These are only options which are valid in the 'global' stanza
    # 5/22 CS Except for blacklist, we define that in code, since splunk complains about it in
    # the config files
    threading = None
    disabled = None
    blacklist = ".*\.part"

    __outputPlugins = { }
    __plugins = { }
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
                    'profiler', 'maxIntervalsBeforeFlush', 'maxQueueLength',
                    'verbose', 'useOutputQueue', 'seed','end', 'autotimestamps', 'autotimestamp']
    _validTokenTypes = {'token': 0, 'replacementType': 1, 'replacement': 2}
    _validHostTokens = {'token': 0, 'replacement': 1}
    _validReplacementTypes = ['static', 'timestamp', 'replaytimestamp', 'random', 'rated', 'file', 'mvfile', 'integerid']
    _validOutputModes = [ ]
    _intSettings = ['interval', 'outputWorkers', 'generatorWorkers', 'maxIntervalsBeforeFlush', 'maxQueueLength']
    _floatSettings = ['randomizeCount', 'delay', 'timeMultiple']
    _boolSettings = ['disabled', 'randomizeEvents', 'bundlelines', 'profiler', 'useOutputQueue', 'autotimestamp']
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

    def __init__(self, args=None):
        """Setup Config object.  Sets up Logging and path related variables."""
        # Rebind the internal datastore of the class to an Instance variable
        self.__dict__ = self.__sharedState
        if self._firsttime:
            # 2/1/15 CS  Adding support for command line arguments
            if args:
                self.args = args

            # Setup logger
            # 12/8/13 CS Adding new verbose log level to make this a big more manageable
            DEBUG_LEVELV_NUM = 9
            logging.addLevelName(DEBUG_LEVELV_NUM, "DEBUGV")
            logging.__dict__['DEBUGV'] = DEBUG_LEVELV_NUM
            def debugv(self, message, *args, **kws):
                # Yes, logger takes its '*args' as 'args'.
                if self.isEnabledFor(DEBUG_LEVELV_NUM):
                    self._log(DEBUG_LEVELV_NUM, message, args, **kws)
            logging.Logger.debugv = debugv

            logger = logging.getLogger('eventgen')
            logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
            logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            streamHandler = logging.StreamHandler(sys.stderr)
            streamHandler.setFormatter(formatter)
            # 2/1/15 CS  Adding support for command line arguments.  In this case, if we're running from the command
            # line and we have arguments, we only want output from logger if we're in verbose
            if self.args:
                if self.args.verbosity >= 1:
                    logger.addHandler(streamHandler)
                else:
                    logger.addHandler(logging.NullHandler())

                if self.args.multiprocess:
                    self.threading = 'process'
                if self.args.profiler:
                    self.profiler = True
            else:
                logger.addHandler(streamHandler)
            # logging.disable(logging.INFO)

            adapter = EventgenAdapter(logger, {'sample': 'null', 'module': 'config'})
            # Having logger as a global is just damned convenient
            self.logger = adapter

            # Determine some path names in our environment
            self.grandparentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.greatgrandparentdir = os.path.dirname(self.grandparentdir)

            # 1/11/14 CS Adding a initial config parsing step (this does this twice now, oh well, just runs once
            # per execution) so that I can get config before calling parse()

            c = ConfigParser()
            c.optionxform = str
            c.read([os.path.join(self.grandparentdir, 'default', 'eventgen.conf')])
            for s in c.sections():
                for i in c.items(s):
                    if i[0] == 'threading' and self.threading == None:
                        self.threading = i[1]

            # Set a global variables to signal to our plugins the threading model without having
            # to load config.  Kinda hacky, but easier than other methods.
            globals()['threadmodel'] = self.threading

            # Initialize plugins
            self.__outputPlugins = { }
            plugins = self.__initializePlugins(os.path.join(self.grandparentdir, 'lib', 'plugins', 'output'), self.__outputPlugins, 'output')
            self.outputQueue = Queue(100, self.threading)
            self._validOutputModes.extend(plugins)

            plugins = self.__initializePlugins(os.path.join(self.grandparentdir, 'lib', 'plugins', 'generator'), self.__plugins, 'generator')
            self.generatorQueue = Queue(10000, self.threading)

            plugins = self.__initializePlugins(os.path.join(self.grandparentdir, 'lib', 'plugins', 'rater'), self.__plugins, 'rater')
            self._complexSettings['rater'] = plugins


            self._complexSettings['timezone'] = self._validateTimezone

            self._complexSettings['count'] = self._validateCount

            self._complexSettings['seed'] = self._validateSeed

            self.generatorQueueSize = Counter(0, self.threading)
            self.outputQueueSize = Counter(0, self.threading)
            self.eventsSent = Counter(0, self.threading)
            self.bytesSent = Counter(0, self.threading)
            self.timersStarting = Counter(0, self.threading)
            self.timersStarted = Counter(0, self.threading)
            self.pluginsStarting = Counter(0, self.threading)
            self.pluginsStarted = Counter(0, self.threading)
            self.stopping = Counter(0, self.threading)

            self.copyLock = threading.Lock() if self.threading == 'thread' else multiprocessing.Lock()

            self._firsttime = False
            self.intervalsSinceFlush = { }

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of our Config"""
        # Filter items from config we don't want to pretty print
        filter_list = [ 'samples', 'sampleTimers', '__generatorworkers', '__outputworkers' ]
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key not in filter_list ])

        return 'Config:'+pprint.pformat(temp)+'\nSamples:\n'+pprint.pformat(self.samples)

    def __repr__(self):
        return self.__str__()
    '''
    APPPERF-263: add default name param. If name is supplied then only
    attempt to load <name>.py
    '''
    def __initializePlugins(self, dirname, plugins, plugintype, name=None):
        """Load a python module dynamically and add to internal dictionary of plugins (only accessed by getPlugin)"""
        ret = []

        dirname = os.path.abspath(dirname)
        self.logger.debugv("looking for plugin(s) in {}".format(dirname))
        if not os.path.isdir(dirname):
            self.logger.debugv("directory {} does not exist ... moving on".format(dirname))
            return ret

        # Include all plugin directories in sys.path for includes
        if not dirname in sys.path:
            sys.path.append(dirname)

        # Loop through all files in passed dirname looking for plugins
        for filename in os.listdir(dirname):
            filename = dirname + os.sep + filename

            # If the file exists
            if os.path.isfile(filename):
                # Split file into a base name plus extension
                basename = os.path.basename(filename)
                base, extension = os.path.splitext(basename)

                # If we're a python file and we don't start with _
                #if extension == ".py" and not basename.startswith("_"):
                # APPPERF-263: If name param is supplied, only attempt to load
                # {name}.py from {app}/bin directory
                if extension == ".py" and ((name is None and not basename.startswith("_")) or base == name):
                    self.logger.debugv("Searching for plugin in file '%s'" % filename)
                    try:
                        # Import the module
                        module = __import__(base)
                        # Signal to the plugin by adding a module level variable which indicates
                        # our threading model, thread or process
                        module.__dict__.update({ 'threadmodel': self.threading })
                        # Load will now return a threading.Thread or multiprocessing.Process based object
                        plugin = module.load()

                        # set plugin to something like output.file or generator.default
                        pluginname = plugintype + '.' + base
                        # self.logger.debugv("Filename: %s os.sep: %s pluginname: %s" % (filename, os.sep, pluginname))
                        plugins[pluginname] = plugin

                        # Return is used to determine valid configs, so only return the base name of the plugin
                        ret.append(base)

                        self.logger.debug("Loading module '%s' from '%s'" % (pluginname, basename))

                        # 12/3/13 If we haven't loaded a plugin right or we haven't initialized all the variables
                        # in the plugin, we will get an exception and the plan is to not handle it
                        if 'validSettings' in dir(plugin):
                            self._validSettings.extend(plugin.validSettings)
                        if 'defaultableSettings' in dir(plugin):
                            self._defaultableSettings.extend(plugin.defaultableSettings)
                        if 'intSettings' in dir(plugin):
                            self._intSettings.extend(plugin.intSettings)
                        if 'floatSettings' in dir(plugin):
                            self._floatSettings.extend(plugin.floatSettings)
                        if 'boolSettings' in dir(plugin):
                            self._boolSettings.extend(plugin.boolSettings)
                        if 'jsonSettings' in dir(plugin):
                            self._jsonSettings.extend(plugin.jsonSettings)
                        if 'complexSettings' in dir(plugin):
                            self._complexSettings.update(plugin.complexSettings)
                    except ValueError:
                        self.logger.error("Error loading plugin '%s' of type '%s'" % (base, plugintype))
                        self.logger.debug(traceback.format_exc())

        # Chop off the path we added
        sys.path = sys.path[0:-1]
        return ret


    def getPlugin(self, name, s=None):
        """Return a reference to a Python object (not an instance) referenced by passed name"""

        '''
        APPPERF-263:
        make sure we look in __outputPlugins as well. For some reason we
        keep 2 separate dicts of plugins.
        '''
        if not name in self.__plugins and not name in self.__outputPlugins:
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
                        pluginsdict = self.__plugins if plugintype in ('generator', 'rater') else self.__outputPlugins
                        bindir = os.path.join(s.sampleDir, os.pardir, 'bin')
                        libdir = os.path.join(s.sampleDir, os.pardir, 'lib')
                        plugindir = os.path.join(libdir, 'plugins', plugintype)

                        #APPPERF-263: be picky when loading from an app bindir (only load name)
                        self.__initializePlugins(bindir, pluginsdict, plugintype, name=plugin)

                        #APPPERF-263: be greedy when scanning plugin dir (eat all the pys)
                        self.__initializePlugins(plugindir, pluginsdict, plugintype)

        # APPPERF-263: consult both __outputPlugins and __plugins
        if not name in self.__plugins and not name in self.__outputPlugins:
            raise KeyError('Plugin ' + name + ' not found')

        # return in order of precedence:  __plugins, __outputPlugins, None
        # Note: because of the above KeyError Exception we should never return
        # None, but it is the sane behavior for a getter method
        return self.__plugins.get(name,self.__outputPlugins.get(name,None))

    def __setPlugin(self, s):
        """Called during setup, assigns which output plugin to use based on configured outputMode"""
        # 12/2/13 CS Adding pluggable output modules, need to set array to map sample name to output plugin
        # module instances

        name = s.outputMode.lower()
        key = "{type}.{name}".format(type="output", name=name)

        try:
            self.__plugins[s.name] = self.__outputPlugins[key](s)
            plugin = self.__plugins[s.name]
        except KeyError:
            try:
                # APPPERF-263: now attempt to dynamically load plugin
                self.getPlugin(key, s)
                self.__plugins[s.name] = self.__outputPlugins[key](s)
                plugin = self.__plugins[s.name]
            except KeyError:
                # APPPERF-264:  dynamic loading has failed
                raise KeyError('Output plugin %s does not exist' % s.outputMode.lower())


    def makeSplunkEmbedded(self, sessionKey=None):
        """Setup operations for being Splunk Embedded.  This is legacy operations mode, just a little bit obfuscated now.
        We wait 5 seconds for a sessionKey or 'debug' on stdin, and if we time out then we run in standalone mode.
        If we're not Splunk embedded, we operate simpler.  No rest handler for configurations. We only read configs
        in our parent app's directory."""

        fileHandler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/eventgen.log', maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fileHandler.setFormatter(formatter)
        # fileHandler.setLevel(logging.DEBUG)
        logobj = logging.getLogger('eventgen')
        logobj.handlers = [ ] # Remove existing StreamHandler if we're embedded
        logobj.addHandler(fileHandler)
        self.logger.info("Running as Splunk embedded")

        # 6/7/14 Add Metrics logger so we can output JSON metrics for Splunk
        fileHandler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/eventgen_metrics.log', maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(message)s')
        fileHandler.setFormatter(formatter)
        # fileHandler.setLevel(logging.DEBUG)
        logobj = logging.getLogger('eventgen_metrics')
        logobj.addHandler(fileHandler)
        import splunk.auth as auth
        import splunk.entity as entity
        # 5/7/12 CS For some reason Splunk will not import the modules into global in its copy of python
        # This is a hacky workaround, but it does fix the problem
        globals()['auth'] = locals()['auth']
        # globals()['bundle'] = locals()['bundle']
        globals()['entity'] = locals()['entity']
        # globals()['rest'] = locals()['rest']
        # globals()['util'] = locals()['util']

        if sessionKey == None:
            self.sessionKey = auth.getSessionKey('admin', 'changeme')
        else:
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
        self.logger.debug("Parsing configuration files.")
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

        # 1/16/16 CS Trying to clean up the need to have attributes hard coded into the Config object
        # and instead go off the list of valid settings that could be set
        for setting in self._validSettings:
            if not hasattr(self, setting):
                setattr(self, setting, None)

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

            # 1/5/14 Adding a config setting to override sample directory, primarily so I can put tests in their own
            # directories
            if s.sampleDir == None:
                self.logger.debug("Sample directory not specified in config, setting based on standard")
                if self.splunkEmbedded and not STANDALONE:
                    s.sampleDir = os.path.join(self.greatgrandparentdir, s.app, 'samples')
                else:
                    # 2/1/15 CS  Adding support for looking for samples based on the config file specified on
                    # the command line.
                    if self.args:
                        if os.path.isdir(self.args.configfile):
                            s.sampleDir = os.path.join(self.args.configfile, 'samples')
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
                    s.sampleDir = os.path.join(self.grandparentdir, s.sampleDir)
                else:
                    s.sampleDir = s.sampleDir

            # 2/1/15 CS Adding support for command line options, specifically running a single sample
            # from the command line
            if self.args:
                if self.args.sample:
                    # Name doesn't match, disable
                    if s.name != self.args.sample:
                        self.logger.debug("Disabling sample '%s' because of command line override" % s.name)
                        s.disabled = True
                    # Name matches
                    else:
                        self.logger.debug("Sample '%s' selected from command line" % s.name)
                        # Also, can't backfill search if we don't know how to talk to Splunk
                        s.backfillSearch = None
                        s.backfillSearchUrl = None
                        # Since the user is running this for debug output, lets assume that they
                        # always want to see output
                        self.maxIntervalsBeforeFlush = 1
                        s.maxIntervalsBeforeFlush = 1
                        s.maxQueueLength = 1
                        if self.args.devnull:
                            self.logger.debug("Sample '%s' redirecting to devnull from command line" % s.name)
                            s.outputMode = 'devnull'
                        elif self.args.modinput:
                            self.logger.debug("Sample '%s' setting output to modinput from command line" % s.name)
                            s.outputMode = 'modinput'
                        elif not self.args.keepoutput:
                            s.outputMode = 'stdout'

                        if self.args.count:
                            self.logger.debug("Overriding count to '%d' for sample '%s'" % (self.args.count, s.name))
                            s.count = self.args.count
                            # If we're specifying a count, turn off backfill
                            s.backfill = None

                        if self.args.interval:
                            self.logger.debug("Overriding interval to '%d' for sample '%s'" % (self.args.interval, s.name))
                            s.interval = self.args.interval

                        if self.args.backfill:
                            self.logger.debug("Overriding backfill to '%s' for sample '%s'" % (self.args.backfill, s.name))
                            s.backfill = self.args.backfill.lstrip()

                        if self.args.end:
                            self.logger.debug("Overriding end to '%s' for sample '%s'" % (self.args.end, s.name))
                            s.end = self.args.end.lstrip()


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
                    tempsamples2.append(copy.deepcopy(s))
            for f in foundFiles:
                news = copy.deepcopy(s)
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
                    newtokens = copy.deepcopy(s.tokens)
                    # self.logger.debug("Prepending tokens from sample '%s' to sample '%s' in app '%s': %s" \
                    #             % (overridesample._origName, s.name, s.app, pprint.pformat(newtokens)))
                    newtokens.extend(copy.deepcopy(overridesample.tokens))
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

            if s.mode == 'replay':
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

            self.__setPlugin(s)
            self.intervalsSinceFlush[s.name] = Counter(0, self.threading)

        self.samples = tempsamples
        self._confDict = None

        # 2/1/15 CS  Adding support for command line arguments to modify the config
        if self.args:
            if self.args.generators >= 0:
                self.generatorWorkers = self.args.generators
            if self.args.outputters >= 0:
                self.outputWorkers = self.args.outputters
            if self.args.disableOutputQueue:
                self.useOutputQueue = False
            if self.args.multiprocess:
                self.threading = 'process'
            if self.args.profiler:
                self.profiler = True

        # 9/2/15 Try autotimestamp values, add a timestamp if we find one
        for s in self.samples:
            if s.generator in ('default', 'replay'):
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



        self.logger.debug("Finished parsing.  Config str:\n%s" % self)

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
            self.logger.warning("Key '%s' in stanza '%s' is not a valid setting" % (key, stanza))
        return value

    def _validateTimezone(self, value):
        """Callback for complexSetting timezone which will parse and validate the timezone"""
        self.logger.debug("Parsing timezone '%s'" % (value))
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
                self.logger.error("Could not parse timezone '%s' for '%s'" % (value, key))
                raise ValueError("Could not parse timezone '%s' for '%s'" % (value, key))
        self.logger.debug("Parsed timezone '%s'" % (value))
        return value

    def _validateCount(self, value):
        """Callback to override count to -1 if set to 0 in the config, otherwise return int"""
        self.logger.debug("Validating count of %s" % value)
        # 5/13/14 CS Hack to take a zero count in the config and set it to a value which signifies
        # the special condition rather than simply being zero events, setting to -1
        try:
            value = int(value)
        except:
            self.logger.error("Could not parse int for 'count' in stanza '%s'" % (key, stanza))
            raise ValueError("Could not parse int for 'count' in stanza '%s'" % (key, stanza))

        if value == 0:
            value = -1
        self.logger.debug("Count set to %d" % value)

        return value

    def _validateSeed(self, value):
        """Callback to set random seed"""
        self.logger.debug("Validating random seed of %s" % value)
        try:
            value = int(value)
        except:
            self.logger.error("Could not parse int for 'seed' in stanza '%s'" % (key, stanza))
            raise ValueError("Could not parse int for 'count' in stanza '%s'" % (key, stanza))

        self.logger.info("Using random seed %s" % value)
        random.seed(value)



    def _buildConfDict(self):
        """Build configuration dictionary that we will use """

        # Abstracts grabbing configuration from Splunk or directly from Configuration Files

        if self.splunkEmbedded and not STANDALONE:
            self.logger.info('Retrieving eventgen configurations from /configs/eventgen')
            self._confDict = entity.getEntities('configs/eventgen', count=-1, sessionKey=self.sessionKey)
        else:
            self.logger.info('Retrieving eventgen configurations with ConfigParser()')
            # We assume we're in a bin directory and that there are default and local directories
            conf = ConfigParser()
            # Make case sensitive
            conf.optionxform = str
            currentdir = os.getcwd()

            conffiles = [ ]
            # 2/1/15 CS  Moving to argparse way of grabbing command line parameters
            if self.args:
                if self.args.configfile:
                    if os.path.exists(self.args.configfile):
                        # 2/1/15 CS Adding a check to see whether we're instead passed a directory
                        # In which case we'll assume it's a splunk app and look for config files in
                        # default and local
                        if os.path.isdir(self.args.configfile):
                            conffiles = [os.path.join(self.grandparentdir, 'default', 'eventgen.conf'),
                                    os.path.join(self.args.configfile, 'default', 'eventgen.conf'),
                                    os.path.join(self.args.configfile, 'local', 'eventgen.conf')]
                        else:
                            conffiles = [os.path.join(self.grandparentdir, 'default', 'eventgen.conf'),
                                    self.args.configfile]
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

        # Have to look in the data structure before normalization between what Splunk returns
        # versus what ConfigParser returns.
        logobj = logging.getLogger('eventgen')
        if self._confDict['global']['debug'].lower() == 'true' \
                or self._confDict['global']['debug'].lower() == '1':
            logobj.setLevel(logging.DEBUG)
        if self._confDict['global']['verbose'].lower() == 'true' \
                or self._confDict['global']['verbose'].lower() == '1':
            logobj.setLevel(logging.DEBUGV)

        # 2/1/15 CS  Adding support for command line options
        if self.args:
            if self.args.verbosity >= 2:
                self.debug = True
                logobj.setLevel(logging.DEBUG)
            if self.args.verbosity >= 3:
                self.verbose = True
                logobj.setLevel(logging.DEBUGV)
        self.logger.debug("ConfDict returned %s" % pprint.pformat(dict(self._confDict)))


    # Copied from http://danielkaes.wordpress.com/2009/06/04/how-to-catch-kill-events-with-python/
    def set_exit_handler(self, func):
        """Catch signals and call handle_exit when we're supposed to shut down"""
        if os.name == "nt":
            try:
                import win32api
                win32api.SetConsoleCtrlHandler(func, True)
            except ImportError:
                version = ".".join(map(str, sys.version_info[:2]))
                raise Exception("pywin32 not installed for Python " + version)
        else:
            import signal
            signal.signal(signal.SIGTERM, func)
            signal.signal(signal.SIGINT, func)

    def handle_exit(self, sig=None, func=None):
        """Clean up and shut down threads"""
        self.logger.info("Caught kill, exiting...")
        self.stopping.increment()

        # Loop through all threads/processes and mark them for death
        # This does not actually kill the plugin, but they should check to see if
        # they are set to stop with every iteration
        for sampleTimer in self.sampleTimers:
            sampleTimer.stop()

        time.sleep(0.5)

        # while self.generatorQueueSize.value() > 0 or self.outputQueueSize.value() > 0:
        #     time.sleep(0.1)

        # 7/4/16 Stop generator workers first
        for worker in self.__generatorworkers:
            worker.stop()

        time.sleep(0.5)

        for worker in self.__outputworkers:
            worker.stop()

        self.logger.info("Exiting main thread.")
        sys.exit(0)

    def start(self):
        """Start up worker threads"""
        # Only start output workers if we're going to use them
        if self.useOutputQueue:
            for x in xrange(0, self.outputWorkers):
                self.logger.info("Starting OutputWorker %d" % x)
                if self.threading == "process":
                    worker = OutputProcessWorker(x)
                else:
                    worker = OutputThreadWorker(x)
                worker.daemon = True
                worker.start()
                self.__outputworkers.append(worker)

        # Start X instantiations of GeneratorWorkers, controlled by the generators configuration
        # or command line parameter
        for x in xrange(0, self.generatorWorkers):
            self.logger.info("Starting GeneratorWorker %d" % x)
            if self.threading == "process":
                worker = GeneratorProcessWorker(x, self.generatorQueue, self.outputQueue)
            else:
                worker = GeneratorThreadWorker(x, self.generatorQueue, self.outputQueue)
            worker.daemon = True
            worker.start()
            self.__generatorworkers.append(worker)

        self.logger.debug("Waiting for workers to start for %d workers" % self.generatorWorkers)
        while self.pluginsStarted.value() < self.generatorWorkers:
            self.logger.debug("pluginsStarted value of '%d' is less than total '%d'" % (self.pluginsStarted.value(), self.generatorWorkers))
            time.sleep(0.1)

        # Start a Timer thread for every sample which will either run a non-Queueable Plugin
        # in the thread or send work to a queue which will be fulfilled by a GeneratorWorker
        for sampleTimer in self.sampleTimers:
            sampleTimer.daemon = True
            sampleTimer.start()
            self.logger.info("Starting timer for sample '%s'" % sampleTimer.sample.name)


        self.logger.debug("Waiting for timers to start for %d timers" % len(self.sampleTimers))
        while self.timersStarted.value() < len(self.sampleTimers):
            self.logger.debug("timersStarted value of '%d' is less than total '%d'" % (self.timersStarted.value(), len(self.sampleTimers)))
            time.sleep(0.1)