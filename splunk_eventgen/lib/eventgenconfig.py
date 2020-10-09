import datetime
import json
import logging.handlers
import os
import pprint
import random
import re
import types
from configparser import RawConfigParser

import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request

from splunk_eventgen.lib.eventgenexceptions import FailedLoadingPlugin, PluginNotLoaded
from splunk_eventgen.lib.eventgensamples import Sample
from splunk_eventgen.lib.eventgentoken import Token
from splunk_eventgen.lib.logging_config import logger

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

    DEFAULT_SAMPLE_DIR = "samples"

    # Stolen from http://code.activestate.com/recipes/66531/
    # This implements a Borg patterns, similar to Singleton
    # It allows numerous instantiations but always shared state
    __sharedState = {}

    # Internal vars
    _firsttime = True
    _confDict = None

    # Externally used vars
    debug = False
    verbosity = logging.ERROR
    splunkEmbedded = False
    sessionKey = None
    grandparentdir = None
    greatgrandparentdir = None
    samples = []
    sampleDir = None
    outputWorkers = None
    generatorWorkers = None
    sampleTimers = []

    # Config file options.  We do not define defaults here, rather we pull them in
    # from eventgen.conf.
    # These are only options which are valid in the 'global' stanza
    # 5/22 CS Except for blacklist, we define that in code, since splunk complains about it in
    # the config files
    threading = None
    disabled = None
    blacklist = r".*\.part"

    __generatorworkers = []
    __outputworkers = []
    outputPlugins = {}
    plugins = {}
    outputQueue = None
    generatorQueue = None
    args = None

    # Validations
    _validSettings = [
        "disabled",
        "blacklist",
        "spoolDir",
        "spoolFile",
        "breaker",
        "sampletype",
        "interval",
        "delay",
        "count",
        "bundlelines",
        "earliest",
        "latest",
        "eai:acl",
        "hourOfDayRate",
        "dayOfWeekRate",
        "randomizeCount",
        "randomizeEvents",
        "outputMode",
        "fileName",
        "fileMaxBytes",
        "fileBackupFiles",
        "index",
        "source",
        "sourcetype",
        "host",
        "hostRegex",
        "projectID",
        "accessToken",
        "mode",
        "backfill",
        "backfillSearch",
        "eai:userName",
        "eai:appName",
        "timeMultiple",
        "debug",
        "minuteOfHourRate",
        "timezone",
        "dayOfMonthRate",
        "monthOfYearRate",
        "perDayVolume",
        "outputWorkers",
        "generator",
        "rater",
        "generatorWorkers",
        "timeField",
        "sampleDir",
        "threading",
        "profiler",
        "maxIntervalsBeforeFlush",
        "maxQueueLength",
        "splunkMethod",
        "splunkPort",
        "syslogDestinationHost",
        "syslogDestinationPort",
        "syslogAddHeader",
        "verbosity",
        "useOutputQueue",
        "seed",
        "end",
        "autotimestamps",
        "autotimestamp",
        "httpeventWaitResponse",
        "outputCounter",
        "sequentialTimestamp",
        "extendIndexes",
        "disableLoggingQueue",
        "splitSample",
    ]
    _validTokenTypes = {"token": 0, "replacementType": 1, "replacement": 2}
    _validHostTokens = {"token": 0, "replacement": 1}
    _validReplacementTypes = [
        "static",
        "timestamp",
        "replaytimestamp",
        "random",
        "rated",
        "file",
        "mvfile",
        "seqfile",
        "integerid",
    ]
    validOutputModes = []
    _intSettings = [
        "interval",
        "outputWorkers",
        "generatorWorkers",
        "maxIntervalsBeforeFlush",
        "maxQueueLength",
        "splitSample",
        "fileMaxBytes",
    ]
    _floatSettings = ["randomizeCount", "delay", "timeMultiple"]
    _boolSettings = [
        "disabled",
        "randomizeEvents",
        "bundlelines",
        "profiler",
        "useOutputQueue",
        "autotimestamp",
        "httpeventWaitResponse",
        "outputCounter",
        "sequentialTimestamp",
        "disableLoggingQueue",
        "syslogAddHeader",
    ]
    _jsonSettings = [
        "hourOfDayRate",
        "dayOfWeekRate",
        "minuteOfHourRate",
        "dayOfMonthRate",
        "monthOfYearRate",
        "autotimestamps",
    ]
    _defaultableSettings = [
        "disabled",
        "spoolDir",
        "spoolFile",
        "breaker",
        "sampletype",
        "interval",
        "delay",
        "count",
        "bundlelines",
        "earliest",
        "latest",
        "hourOfDayRate",
        "dayOfWeekRate",
        "randomizeCount",
        "randomizeEvents",
        "outputMode",
        "fileMaxBytes",
        "fileBackupFiles",
        "splunkHost",
        "splunkPort",
        "splunkMethod",
        "index",
        "source",
        "sourcetype",
        "host",
        "hostRegex",
        "projectID",
        "accessToken",
        "mode",
        "minuteOfHourRate",
        "timeMultiple",
        "dayOfMonthRate",
        "monthOfYearRate",
        "perDayVolume",
        "sessionKey",
        "generator",
        "rater",
        "timeField",
        "maxQueueLength",
        "maxIntervalsBeforeFlush",
        "autotimestamp",
        "splitSample",
    ]
    _complexSettings = {
        "sampletype": ["raw", "csv"],
        "mode": ["sample", "replay"],
        "threading": ["thread", "process"],
    }

    def __init__(
        self,
        configfile=None,
        sample=None,
        override_outputter=False,
        override_count=False,
        override_interval=False,
        override_backfill=False,
        override_end=False,
        threading="thread",
        override_generators=None,
        override_outputqueue=False,
        profiler=False,
        verbosity=40,
    ):
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
        self.verbosity = verbosity
        if override_generators is not None and override_generators >= 0:
            self.generatorWorkers = override_generators
        if override_outputqueue:
            self.useOutputQueue = False

        if self._firsttime:
            # Determine some path names in our environment
            self.grandparentdir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            self.greatgrandparentdir = os.path.dirname(self.grandparentdir)

            # 1/11/14 CS Adding a initial config parsing step (this does this twice now, oh well, just runs once
            # per execution) so that I can get config before calling parse()

            c = RawConfigParser()
            c.optionxform = str
            c.read([os.path.join(self.grandparentdir, "default", "eventgen.conf")])

            self._complexSettings["timezone"] = self._validateTimezone

            self._complexSettings["seed"] = self._validateSeed

            self.stopping = False

            # self.copyLock = threading.Lock() if self.threading == 'thread' else multiprocessing.Lock()

            self._firsttime = False

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of our Config"""
        # Filter items from config we don't want to pretty print
        filter_list = [
            "samples",
            "sampleTimers",
            "__generatorworkers",
            "__outputworkers",
        ]
        # Eliminate recursive going back to parent
        temp = dict(
            [
                (key, value)
                for (key, value) in self.__dict__.items()
                if key not in filter_list
            ]
        )

        return (
            "Config:"
            + pprint.pformat(temp)
            + "\nSamples:\n"
            + pprint.pformat(self.samples)
        )

    def getPlugin(self, name, s=None):
        """Return a reference to a Python object (not an instance) referenced by passed name"""
        """
        APPPERF-263:
        make sure we look in __outputPlugins as well. For some reason we
        keep 2 separate dicts of plugins.
        """
        plugintype = name.split(".")[0]
        if name not in self.plugins and name not in self.outputPlugins:
            # 2/1/15 CS If we haven't already seen the plugin, try to load it
            # Note, this will only work for plugins which do not specify config validation
            # parameters.  If they do, configs may not validate for user provided plugins.
            if s:
                if plugintype in ("generator", "rater"):
                    plugin = getattr(s, plugintype)
                else:
                    plugin = getattr(s, "outputMode")
                if plugin is not None:
                    logger.debug(
                        "Attempting to dynamically load plugintype '%s' named '%s' for sample '%s'"
                        % (plugintype, plugin, s.name)
                    )
                    bindir = os.path.join(s.sampleDir, os.pardir, "bin")
                    libdir = os.path.join(s.sampleDir, os.pardir, "lib")
                    plugindir = os.path.join(libdir, "plugins", plugintype)
                    targetplugin = PluginNotLoaded(
                        bindir=bindir,
                        libdir=libdir,
                        plugindir=plugindir,
                        name=plugin,
                        type=plugintype,
                    )
                    if targetplugin.name not in self.extraplugins:
                        self.extraplugins.append(targetplugin.name)
                        raise targetplugin
                    else:
                        raise FailedLoadingPlugin(name=plugin)

        # APPPERF-263: consult both __outputPlugins and __plugins
        if name not in self.plugins and name not in self.outputPlugins:
            raise KeyError("Plugin " + name + " not found")

        # return in order of precedence:  __plugins, __outputPlugins, None
        # Note: because of the above KeyError Exception we should never return
        # None, but it is the sane behavior for a getter method
        return self.plugins.get(name, self.outputPlugins.get(name, None))

    def makeSplunkEmbedded(self, sessionKey):
        self.sessionKey = sessionKey
        self.splunkEmbedded = True

    def getSplunkUrl(self, s):
        """
        If we're embedded in Splunk, get it from Splunk's Python libraries, otherwise get it from config.

        Returns a tuple of ( splunkUrl, splunkMethod, splunkHost, splunkPort )
        """
        if self.splunkEmbedded:
            try:
                import splunk.auth

                splunkUrl = splunk.auth.splunk.getLocalServerInfo()
                results = re.match(r"(http|https)://([^:/]+):(\d+).*", splunkUrl)
                splunkMethod = results.groups()[0]
                splunkHost = results.groups()[1]
                splunkPort = results.groups()[2]
            except:
                import traceback

                trace = traceback.format_exc()
                logger.error(
                    "Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s.  Stacktrace: %s"
                    % (s.name, trace)
                )
                raise ValueError(
                    "Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s"
                    % s.name
                )
        else:
            # splunkMethod and splunkPort are defaulted so only check for splunkHost
            if s.splunkHost is None:
                logger.error(
                    "Splunk URL Requested but splunkHost not set for sample '%s'"
                    % s.name
                )
                raise ValueError(
                    "Splunk URL Requested but splunkHost not set for sample '%s'"
                    % s.name
                )

            splunkUrl = "%s://%s:%s" % (s.splunkMethod, s.splunkHost, s.splunkPort)
            splunkMethod = s.splunkMethod
            splunkHost = s.splunkHost
            splunkPort = s.splunkPort

        logger.debug(
            "Getting Splunk URL: %s Method: %s Host: %s Port: %s"
            % (splunkUrl, splunkMethod, splunkHost, splunkPort)
        )
        return (splunkUrl, splunkMethod, splunkHost, splunkPort)

    def parse(self):
        """Parse configs from Splunk REST Handler or from files.
        We get called manually instead of in __init__ because we need find out if we're Splunk embedded before
        we figure out how to configure ourselves.
        """
        self.samples = []
        logger.debug("Parsing configuration files.")
        self._buildConfDict()
        # Set defaults config instance variables to 'global' section
        # This establishes defaults for other stanza settings
        if "global" in self._confDict:
            for key, value in self._confDict["global"].items():
                value = self._validateSetting("global", key, value)
                setattr(self, key, value)
            del self._confDict["global"]
            if "default" in self._confDict:
                del self._confDict["default"]

        tempsamples = []
        tempsamples2 = []

        stanza_map = {}
        stanza_list = []
        for stanza in self._confDict:
            stanza_list.append(stanza)
            stanza_map[stanza] = []

        for stanza, settings in self._confDict.items():
            for stanza_item in stanza_list:
                if stanza != stanza_item and re.match(stanza, stanza_item):
                    stanza_map[stanza_item].append(stanza)

        # 1/16/16 CS Trying to clean up the need to have attributes hard coded into the Config object
        # and instead go off the list of valid settings that could be set
        for setting in self._validSettings:
            if not hasattr(self, setting):
                setattr(self, setting, None)

        # Now iterate for the rest of the samples we've found
        # We'll create Sample objects for each of them
        for stanza, settings in self._confDict.items():
            if self.sample is not None and self.sample != stanza:
                logger.info(
                    "Skipping sample '%s' because of command line override", stanza
                )
                continue

            sampleexists = False
            for sample in self.samples:
                if sample.name == stanza:
                    sampleexists = True

            # If we see the sample in two places, use the first and ignore the second
            if not sampleexists:
                s = Sample(stanza)
                s.splunkEmbedded = self.splunkEmbedded

                s.updateConfig(self)

                # Get the latest token number of the current stanza
                last_token_number = 0
                for key, value in settings.items():
                    if (
                        "token" in key
                        and key[6].isdigit()
                        and int(key[6]) > last_token_number
                    ):
                        last_token_number = int(key[6])

                # Apply global tokens to the current stanza
                kv_pair_items = list(settings.items())
                if stanza in stanza_map:
                    for global_stanza in stanza_map[stanza]:
                        i = 0

                        # Scan for tokens first
                        while True:
                            if (
                                "token.{}.token".format(i)
                                in self._confDict[global_stanza]
                            ):
                                token = self._confDict[global_stanza].get(
                                    "token.{}.token".format(i)
                                )
                                replacement = self._confDict[global_stanza].get(
                                    "token.{}.replacement".format(i)
                                )
                                replacementType = self._confDict[global_stanza].get(
                                    "token.{}.replacementType".format(i)
                                )

                                last_token_number += 1
                                if token:
                                    k = "token.{}.token".format(last_token_number)
                                    v = token
                                    kv_pair_items.append((k, v))
                                if replacement:
                                    k = "token.{}.replacement".format(last_token_number)
                                    v = replacement
                                    kv_pair_items.append((k, v))
                                if replacementType:
                                    k = "token.{}.replacementType".format(
                                        last_token_number
                                    )
                                    v = replacementType
                                    kv_pair_items.append((k, v))

                                i += 1
                            else:
                                break

                        keys = list(settings.keys())
                        for k, v in self._confDict[global_stanza].items():
                            if "token" not in k and k not in keys:
                                kv_pair_items.append((k, v))

                for key, value in kv_pair_items:
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
                        if key.find("host.") > -1:
                            # logger.info("hostToken.{} = {}".format(value[1],oldvalue))
                            if not isinstance(s.hostToken, Token):
                                s.hostToken = Token(s)
                                # default hard-coded for host replacement
                                s.hostToken.replacementType = "file"
                            setattr(s.hostToken, value[0], oldvalue)
                        else:
                            if len(s.tokens) <= value[0]:
                                x = (value[0] + 1) - len(s.tokens)
                                s.tokens.extend([None for num in range(0, x)])
                            if not isinstance(s.tokens[value[0]], Token):
                                s.tokens[value[0]] = Token(s)
                            # logger.info("token[{}].{} = {}".format(value[0],value[1],oldvalue))
                            setattr(s.tokens[value[0]], value[1], oldvalue)
                    elif key == "eai:acl":
                        setattr(s, "app", value["app"])
                    else:
                        setattr(s, key, value)
                        # 6/22/12 CS Need a way to show a setting was set by the original
                        # config read
                        s._lockedSettings.append(key)
                        # logger.debug("Appending '%s' to locked settings for sample '%s'" % (key, s.name))

                # Validate all the tokens are fully setup, can't do this in _validateSettings
                # because they come over multiple lines
                # Don't error out at this point, just log it and remove the token and move on
                deleteidx = []
                for i in range(0, len(s.tokens)):
                    t = s.tokens[i]
                    # If the index doesn't exist at all
                    if t is None:
                        logger.error("Token at index %s invalid" % i)
                        # Can't modify list in place while we're looping through it
                        # so create a list to remove later
                        deleteidx.append(i)
                    elif (
                        t.token is None
                        or t.replacementType is None
                        or t.replacement is None
                    ):
                        logger.error("Token at index %s invalid" % i)
                        deleteidx.append(i)
                newtokens = []
                for i in range(0, len(s.tokens)):
                    if i not in deleteidx:
                        newtokens.append(s.tokens[i])
                s.tokens = newtokens

                # Must have eai:acl key to determine app name which determines where actual files are
                if s.app is None:
                    logger.error(
                        "App not set for sample '%s' in stanza '%s'" % (s.name, stanza)
                    )
                    raise ValueError(
                        "App not set for sample '%s' in stanza '%s'" % (s.name, stanza)
                    )
                # Set defaults for items not included in the config file
                for setting in self._defaultableSettings:
                    if not hasattr(s, setting) or getattr(s, setting) is None:
                        setattr(s, setting, getattr(self, setting, None))

                # Append to temporary holding list
                if not s.disabled:
                    s._priority = len(tempsamples) + 1
                    tempsamples.append(s)

        # 6/22/12 CS Rewriting the config matching code yet again to handling flattening better.
        # In this case, we're now going to match all the files first, create a sample for each of them
        # and then take the match from the sample seen last in the config file, and apply settings from
        # every other match to that one.
        for s in tempsamples:
            # Now we need to match this up to real files.  May generate multiple copies of the sample.
            foundFiles = []

            # 1/5/14 Adding a config setting to override sample directory, primarily so I can put tests in their own
            # directories
            if s.sampleDir is None:
                logger.debug(
                    "Sample directory not specified in config, setting based on standard"
                )
                if self.splunkEmbedded and not STANDALONE:
                    s.sampleDir = os.path.normpath(
                        os.path.join(
                            self.grandparentdir,
                            os.path.pardir,
                            os.path.pardir,
                            os.path.pardir,
                            s.app,
                            self.DEFAULT_SAMPLE_DIR,
                        )
                    )
                else:
                    # 2/1/15 CS  Adding support for looking for samples based on the config file specified on
                    # the command line.
                    if self.configfile:
                        base_dir = (
                            os.path.dirname(self.configfile)
                            if os.path.isdir(self.configfile)
                            else os.path.dirname(os.path.dirname(self.configfile))
                        )
                        s.sampleDir = os.path.join(base_dir, self.DEFAULT_SAMPLE_DIR)
                    else:
                        s.sampleDir = os.path.join(os.getcwd(), self.DEFAULT_SAMPLE_DIR)
                        if not os.path.exists(s.sampleDir):
                            newSampleDir = os.path.join(
                                self.grandparentdir, self.DEFAULT_SAMPLE_DIR
                            )
                            logger.error(
                                "Path not found for samples '%s', trying '%s'"
                                % (s.sampleDir, newSampleDir)
                            )
                            s.sampleDir = newSampleDir
            else:
                if not os.path.isabs(s.sampleDir):
                    # relative path use the conffile dir as the base dir
                    logger.debug(
                        "Sample directory specified in config, checking for relative"
                    )
                    base_path = (
                        self.configfile
                        if os.path.isdir(self.configfile)
                        else os.path.dirname(self.configfile)
                    )
                    s.sampleDir = os.path.join(base_path, s.sampleDir)
                # do nothing when sampleDir is absolute path

                # 2/1/15 CS Adding support for command line options, specifically running a single sample
                # from the command line
                self.run_sample = True
                if self.run_sample:
                    # Name doesn't match, disable
                    # if s.name != self.run_sample:
                    #     logger.debug("Disabling sample '%s' because of command line override" % s.name)
                    #     s.disabled = True
                    # # Name matches
                    # else:
                    #     logger.debug("Sample '%s' selected from command line" % s.name)
                    # Also, can't backfill search if we don't know how to talk to Splunk
                    s.backfillSearch = None
                    s.backfillSearchUrl = None
                    # Since the user is running this for debug output, lets assume that they
                    # always want to see output
                    self.maxIntervalsBeforeFlush = 1
                    s.maxIntervalsBeforeFlush = 1
                    s.maxQueueLength = s.maxQueueLength or 1
                    logger.debug(
                        "Sample '%s' setting maxQueueLength to '%s' from command line"
                        % (s.name, s.maxQueueLength)
                    )

                    if self.override_outputter:
                        logger.debug(
                            "Sample '%s' setting output to '%s' from command line"
                            % (s.name, self.override_outputter)
                        )
                        s.outputMode = self.override_outputter

                    if self.override_count:
                        logger.debug(
                            "Overriding count to '%d' for sample '%s'"
                            % (self.override_count, s.name)
                        )
                        s.count = self.override_count
                        # If we're specifying a count, turn off backfill
                        s.backfill = None

                    if self.override_interval:
                        logger.debug(
                            "Overriding interval to '%d' for sample '%s'"
                            % (self.override_interval, s.name)
                        )
                        s.interval = self.override_interval

                    if self.override_backfill:
                        logger.debug(
                            "Overriding backfill to '%s' for sample '%s'"
                            % (self.override_backfill, s.name)
                        )
                        s.backfill = self.override_backfill.lstrip()

                    if self.override_end:
                        logger.debug(
                            "Overriding end to '%s' for sample '%s'"
                            % (self.override_end, s.name)
                        )
                        s.end = self.override_end.lstrip()

                    if s.mode == "replay" and not s.end:
                        s.end = 1

            # Now that we know where samples will be written,
            # Loop through tokens and load state for any that are integerid replacementType
            for token in s.tokens:
                if token.replacementType == "integerid":
                    try:
                        stateFile = open(
                            os.path.join(
                                s.sampleDir,
                                "state."
                                + six.moves.urllib.request.pathname2url(token.token),
                            ),
                            "r",
                        )
                        token.replacement = stateFile.read()
                        stateFile.close()
                    # The file doesn't exist, use the default value in the config
                    except (IOError, ValueError):
                        token.replacement = token.replacement

            if os.path.exists(s.sampleDir):
                sampleFiles = os.listdir(s.sampleDir)
                for sample in sampleFiles:
                    sample_name = s.name
                    results = re.match(sample_name, sample)
                    if (
                        s.sampletype == "csv"
                        and not s.name.endswith(".csv")
                        and not results
                    ):
                        logger.warning(
                            "Could not find target csv, try adding .csv into stanza title and filename"
                        )
                    if results:
                        # Make sure the stanza name/regex matches the entire file name
                        match_start, match_end = results.regs[0]
                        if match_end - match_start == len(sample):
                            logger.debug(
                                "Matched file {0} with sample name {1}".format(
                                    results.group(0), s.name
                                )
                            )
                            # Store original name for future regex matching
                            s._origName = s.name
                            samplePath = os.path.join(s.sampleDir, sample)
                            if os.path.isfile(samplePath):
                                logger.debug(
                                    "Found sample file '%s' for app '%s' using config '%s' with priority '%s'"
                                    % (sample, s.app, s.name, s._priority)
                                    + "; adding to list"
                                )
                                foundFiles.append(samplePath)

            # If we didn't find any files, log about it
            if len(foundFiles) == 0:
                logger.warning("Sample '%s' in config but no matching files" % s.name)
                # 1/23/14 Change in behavior, go ahead and add the sample even if we don't find a file
                # 9/16/15 Change bit us, now only append if we're a generator other than the two stock generators
                if not s.disabled and not (
                    s.generator == "default" or s.generator == "replay"
                ):
                    tempsamples2.append(s)

            for f in foundFiles:
                if re.search(s._origName, f):
                    s.filePath = f
                    # 12/3/13 CS TODO These are hard coded but should be handled via the modular config system
                    # Maybe a generic callback for all plugins which will modify sample based on the filename
                    # found?
                    # Override <SAMPLE> with real name
                    if s.outputMode == "spool" and s.spoolFile == self.spoolFile:
                        s.spoolFile = f.split(os.sep)[-1]
                    if s.outputMode == "file" and s.fileName is None:
                        if self.fileName:
                            s.fileName = self.fileName
                            logger.debug(
                                "Found a global fileName {}. Setting the sample fileName.".format(
                                    self.fileName
                                )
                            )
                        elif s.spoolFile == self.spoolFile:
                            s.fileName = os.path.join(s.spoolDir, f.split(os.sep)[-1])
                        elif s.spoolFile is not None:
                            s.fileName = os.path.join(s.spoolDir, s.spoolFile)
                    s.name = f.split(os.sep)[-1]
                    if not s.disabled:
                        tempsamples2.append(s)
                    else:
                        logger.info(
                            "Sample '%s' for app '%s' is marked disabled."
                            % (s.name, s.app)
                        )

        # Clear tempsamples, we're going to reuse it
        tempsamples = []

        # We're now going go through the samples and attempt to apply any matches from other stanzas
        # This allows us to specify a wildcard at the beginning of the file and get more specific as we go on

        # Loop through all samples, create a list of the master samples
        for s in tempsamples2:
            foundHigherPriority = False
            othermatches = []
            # If we're an exact match, don't go looking for higher priorities
            if not s.name == s._origName:
                for matchs in tempsamples2:
                    if (
                        matchs.filePath == s.filePath
                        and s._origName != matchs._origName
                    ):
                        # We have a match, now determine if we're higher priority or not
                        # If this is a longer pattern or our match is an exact match
                        # then we're a higher priority match
                        if (
                            len(matchs._origName) > len(s._origName)
                            or matchs.name == matchs._origName
                        ):
                            # if s._priority < matchs._priority:
                            logger.debug(
                                "Found higher priority for sample '%s' with priority '%s' from sample "
                                % (s._origName, s._priority)
                                + "'%s' with priority '%s'"
                                % (matchs._origName, matchs._priority)
                            )
                            foundHigherPriority = True
                            break
                        else:
                            othermatches.append(matchs._origName)
            if not foundHigherPriority:
                logger.debug(
                    "Chose sample '%s' from samples '%s' for file '%s'"
                    % (s._origName, othermatches, s.name)
                )
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
                if (
                    s.filePath == overridesample.filePath
                    and s._origName != overridesample._origName
                ):
                    # Now we're going to loop through all valid settings and set them assuming
                    # the more specific object that we've matched doesn't already have them set
                    for settingname in self._validSettings:
                        if settingname not in [
                            "eai:acl",
                            "blacklist",
                            "disabled",
                            "name",
                        ]:
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
                                #     logger.debug("Matched setting '%s' in sample '%s' lockedSettings"
                                #         % (settingname, matchs.name))
                                if (
                                    (
                                        destsetting is None
                                        or destsetting == getattr(self, settingname)
                                    )
                                    and sourcesetting is not None
                                    and sourcesetting != getattr(self, settingname)
                                    and settingname not in s._lockedSettings
                                ):
                                    logger.debug(
                                        "Overriding setting '%s' with value '%s' from sample '%s' to "
                                        % (
                                            settingname,
                                            sourcesetting,
                                            overridesample._origName,
                                        )
                                        + "sample '%s' in app '%s'" % (s.name, s.app)
                                    )
                                    setattr(s, settingname, sourcesetting)
                            except AttributeError:
                                pass

                    # Now prepend all the tokens to the beginning of the list so they'll be sure to match first
                    newtokens = s.tokens
                    # logger.debug("Prepending tokens from sample '%s' to sample '%s' in app '%s': %s" \
                    #             % (overridesample._origName, s.name, s.app, pprint.pformat(newtokens)))
                    newtokens.extend(overridesample.tokens)
                    s.tokens = newtokens

        # We've added replay mode, so lets loop through the samples again and set the earliest and latest
        # settings for any samples that were set to replay mode
        for s in tempsamples:
            # We've added replay mode, so lets loop through the samples again and set the earliest and latest
            # settings for any samples that were set to replay mode
            if s.perDayVolume:
                logger.info(
                    "Stanza contains per day volume, changing rater and generator to perdayvolume instead of count"
                )
                s.rater = "perdayvolume"
                s.count = 1
                s.generator = "perdayvolumegenerator"
            elif s.mode == "replay":
                logger.debug("Setting defaults for replay samples")
                s.earliest = "now" if not s.earliest else s.earliest
                s.latest = "now" if not s.latest else s.latest
                s.count = 1
                s.randomizeCount = None
                s.hourOfDayRate = None
                s.dayOfWeekRate = None
                s.minuteOfHourRate = None
                s.interval = 0 if not s.interval else s.interval
                # 12/29/13 CS Moved replay generation to a new replay generator plugin
                s.generator = "replay"
            # 5/14/20 - Instead of using a static default source, leave source empty by default and
            # set it to the sample file name unless otherwise specified.
            if not s.source:
                sample_path = s.filePath if s.filePath else s.generator
                s.source = os.path.basename(sample_path)

        self.samples = tempsamples
        self._confDict = None

        # 9/2/15 Try autotimestamp values, add a timestamp if we find one
        for s in self.samples:
            if s.generator == "default":
                s.loadSample()

                if s.autotimestamp:
                    at = self.autotimestamps
                    line_puncts = []

                    # Check for _time field, if it exists, add a timestamp to support it
                    if len(s.sampleDict) > 0:
                        if "_time" in s.sampleDict[0]:
                            logger.debug(
                                "Found _time field, checking if default timestamp exists"
                            )
                            t = Token()
                            t.token = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}"
                            t.replacementType = "timestamp"
                            t.replacement = "%Y-%m-%dT%H:%M:%S.%f"

                            found_token = False
                            # Check to see if we're already a token
                            for st in s.tokens:
                                if (
                                    st.token == t.token
                                    and st.replacement == t.replacement
                                ):
                                    found_token = True
                                    break
                            if not found_token:
                                logger.debug("Found _time adding timestamp to support")
                                s.tokens.append(t)
                            else:
                                logger.debug(
                                    "_time field exists and timestamp already configured"
                                )

                    for e in s.sampleDict:
                        # Run punct against the line, make sure we haven't seen this same pattern
                        # Not totally exact but good enough for Rock'N'Roll
                        p = self._punct(e["_raw"])
                        logger.debug(
                            "Got punct of '%s' for event '%s'" % (p, e[s.timeField])
                        )
                        if p not in line_puncts:
                            for x in at:
                                t = Token()
                                t.token = x[0]
                                t.replacementType = "timestamp"
                                t.replacement = x[1]

                                try:
                                    logger.debug(
                                        "Trying regex '%s' for format '%s' on '%s'"
                                        % (x[0], x[1], e[s.timeField])
                                    )
                                    ts = s.getTSFromEvent(e["_raw"], t)
                                    if type(ts) == datetime.datetime:
                                        found_token = False
                                        # Check to see if we're already a token
                                        for st in s.tokens:
                                            if (
                                                st.token == t.token
                                                and st.replacement == t.replacement
                                            ):
                                                found_token = True
                                                break
                                        if not found_token:
                                            logger.debug(
                                                "Found timestamp '%s', extending token with format '%s'"
                                                % (x[0], x[1])
                                            )
                                            s.tokens.append(t)
                                            # Drop this pattern from ones we try in the future
                                            at = [z for z in at if z[0] != x[0]]
                                        break
                                except ValueError:
                                    pass
                        line_puncts.append(p)
        logger.debug("Finished parsing")

    def _punct(self, string):
        """Quick method of attempting to normalize like events"""
        string = string.replace("\\", "\\\\")
        string = string.replace('"', '\\"')
        string = string.replace("'", "\\'")
        string = string.replace(" ", "_")
        string = string.replace("\t", "t")
        string = re.sub(
            r"[^,;\-#\$%&+./:=\?@\\\'|*\n\r\"(){}<>\[\]\^!]", "", string, flags=re.M
        )
        return string

    def _validateSetting(self, stanza, key, value):
        """Validates settings to ensure they won't cause errors further down the line.
        Returns a parsed value (if the value is something other than a string).
        If we've read a token, which is a complex config, returns a tuple of parsed values."""
        logger.debug(
            "Validating setting for '%s' with value '%s' in stanza '%s'"
            % (key, value, stanza)
        )
        if key.find("token.") > -1:
            results = re.match(r"token\.(\d+)\.(\w+)", key)
            if results is not None:
                groups = results.groups()
                if groups[1] not in self._validTokenTypes:
                    logger.error(
                        "Could not parse token index '%s' token type '%s' in stanza '%s'"
                        % (groups[0], groups[1], stanza)
                    )
                    raise ValueError(
                        "Could not parse token index '%s' token type '%s' in stanza '%s'"
                        % (groups[0], groups[1], stanza)
                    )
                if groups[1] == "replacementType":
                    if value not in self._validReplacementTypes:
                        logger.error(
                            "Invalid replacementType '%s' for token index '%s' in stanza '%s'"
                            % (value, groups[0], stanza)
                        )
                        raise ValueError(
                            "Could not parse token index '%s' token type '%s' in stanza '%s'"
                            % (groups[0], groups[1], stanza)
                        )
                return int(groups[0]), groups[1]
        elif key.find("host.") > -1:
            results = re.match(r"host\.(\w+)", key)
            if results is not None:
                groups = results.groups()
                if groups[0] not in self._validHostTokens:
                    logger.error(
                        "Could not parse host token type '%s' in stanza '%s'"
                        % (groups[0], stanza)
                    )
                    raise ValueError(
                        "Could not parse host token type '%s' in stanza '%s'"
                        % (groups[0], stanza)
                    )
                return groups[0], value
        elif key in self._validSettings:
            if key in self._intSettings:
                try:
                    value = int(value)
                except:
                    logger.error(
                        "Could not parse int for '%s' in stanza '%s'" % (key, stanza)
                    )
                    raise ValueError(
                        "Could not parse int for '%s' in stanza '%s'" % (key, stanza)
                    )
            elif key in self._floatSettings:
                try:
                    value = float(value)
                except:
                    logger.error(
                        "Could not parse float for '%s' in stanza '%s'" % (key, stanza)
                    )
                    raise ValueError(
                        "Could not parse float for '%s' in stanza '%s'" % (key, stanza)
                    )
            elif key in self._boolSettings:
                try:
                    # Splunk gives these to us as a string '0' which bool thinks is True
                    # ConfigParser gives 'false', so adding more strings
                    if value in ("0", "false", "False"):
                        value = 0
                    value = bool(value)
                except:
                    logger.error(
                        "Could not parse bool for '%s' in stanza '%s'" % (key, stanza)
                    )
                    raise ValueError(
                        "Could not parse bool for '%s' in stanza '%s'" % (key, stanza)
                    )
            elif key in self._jsonSettings:
                try:
                    value = json.loads(value)
                except:
                    logger.error(
                        "Could not parse json for '%s' in stanza '%s'" % (key, stanza)
                    )
                    raise ValueError(
                        "Could not parse json for '%s' in stanza '%s'" % (key, stanza)
                    )
            # 12/3/13 CS Adding complex settings, which is a dictionary with the key containing
            # the config item name and the value is a list of valid values or a callback function
            # which will parse the value or raise a ValueError if it is unparseable
            elif key in self._complexSettings:
                complexSetting = self._complexSettings[key]
                logger.debug("Complex setting for '%s' in stanza '%s'" % (key, stanza))
                # Set value to result of callback, e.g. parsed, or the function should raise an error
                if isinstance(complexSetting, types.FunctionType) or isinstance(
                    complexSetting, types.MethodType
                ):
                    logger.debug(
                        "Calling function for setting '%s' with value '%s'"
                        % (key, value)
                    )
                    value = complexSetting(value)
                elif isinstance(complexSetting, list):
                    if key == "threading" and self.threading == "process":
                        value = self.threading
                    if value not in complexSetting:
                        logger.error(
                            "Setting '%s' is invalid for value '%s' in stanza '%s'"
                            % (key, value, stanza)
                        )
                        raise ValueError(
                            "Setting '%s' is invalid for value '%s' in stanza '%s'"
                            % (key, value, stanza)
                        )
        else:
            # Notifying only if the setting isn't valid and continuing on
            # This will allow future settings to be added and be backwards compatible
            logger.info(
                "Key '%s' in stanza '%s' may not be a valid setting" % (key, stanza)
            )
        return value

    def _validateTimezone(self, value):
        """Callback for complexSetting timezone which will parse and validate the timezone"""
        logger.debug("Parsing timezone {}".format(value))
        if value.find("local") >= 0:
            value = datetime.timedelta(days=1)
        else:
            try:
                # Separate the hours and minutes (note: minutes = the int value - the hour portion)
                if int(value) > 0:
                    mod = 100
                else:
                    mod = -100
                value = datetime.timedelta(
                    hours=int(int(value) / 100.0), minutes=int(value) % mod
                )
            except:
                logger.error("Could not parse timezone {}".format(value))
                raise ValueError("Could not parse timezone {}".format(value))
        logger.debug("Parsed timezone {}".format(value))
        return value

    def _validateSeed(self, value):
        """Callback to set random seed"""
        logger.debug("Validating random seed {}".format(value))
        try:
            value = int(value)
        except:
            logger.error("Could not parse int for seed {}".format(value))
            raise ValueError("Could not parse int for seed {}".format(value))

        logger.info("Using random seed {}".format(value))
        random.seed(value)

    def _buildConfDict(self):
        """Build configuration dictionary that we will use """

        # Abstracts grabbing configuration from Splunk or directly from Configuration Files
        if self.splunkEmbedded and not STANDALONE:
            logger.info("Retrieving eventgen configurations from /configs/eventgen")
            import splunk.entity as entity

            self._confDict = entity.getEntities(
                "configs/conf-eventgen", count=-1, sessionKey=self.sessionKey
            )
        else:
            logger.info("Retrieving eventgen configurations with ConfigParser()")
            # We assume we're in a bin directory and that there are default and local directories
            conf = RawConfigParser()
            # Make case sensitive
            conf.optionxform = str
            conffiles = []
            # 2/1/15 CS  Moving to argparse way of grabbing command line parameters
            if self.configfile:
                if os.path.exists(self.configfile):
                    # 2/1/15 CS Adding a check to see whether we're instead passed a directory
                    # In which case we'll assume it's a splunk app and look for config files in
                    # default and local
                    if os.path.isdir(self.configfile):
                        conffiles = [
                            os.path.join(
                                self.grandparentdir, "default", "eventgen.conf"
                            ),
                            os.path.join(self.configfile, "default", "eventgen.conf"),
                            os.path.join(self.configfile, "local", "eventgen.conf"),
                        ]
                    else:
                        conffiles = [
                            os.path.join(
                                self.grandparentdir, "default", "eventgen.conf"
                            ),
                            self.configfile,
                        ]
            if len(conffiles) == 0:
                conffiles = [
                    os.path.join(self.grandparentdir, "default", "eventgen.conf"),
                    os.path.join(self.grandparentdir, "local", "eventgen.conf"),
                ]

            logger.debug(
                "Reading configuration files for non-splunkembedded: %s" % conffiles
            )
            conf.read(conffiles)

            sections = conf.sections()
            ret = {}
            for section in sections:
                ret[section] = dict(conf.items(section))
                # For compatibility with Splunk's configs, need to add the app name to an eai:acl key
                ret[section]["eai:acl"] = {"app": self.grandparentdir.split(os.sep)[-1]}
            self._confDict = ret

        logger.debug("ConfDict returned %s" % pprint.pformat(dict(self._confDict)))
