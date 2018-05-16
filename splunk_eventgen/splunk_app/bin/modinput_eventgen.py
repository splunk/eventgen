#!/usr/bin/env python
# encoding: utf-8
import sys
import logging
import argparse
import signal

# Set path so libraries will load
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'SA-Eventgen', 'lib']))
sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'SA-Eventgen', 'lib', 'splunk_eventgen', 'lib']))

from modinput.fields import BooleanField, Field
from xmloutput import setupLogger, XMLOutputManager
from modinput import ModularInput
from splunk_eventgen import eventgen_core
from splunk_eventgen.lib import eventgenconfig

# Initialize logging
logger = setupLogger(logger=None, log_format='%(asctime)s %(levelname)s [Eventgen] %(message)s', level=logging.DEBUG,
                     log_name="modinput_eventgen.log", logger_name="eventgen_app")

class SimpleNamespace(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Eventgen(ModularInput):
    scheme_args = {
                    'title': "SA-Eventgen",
                    'description': "This modular input generates data for Splunk.",
                    'use_external_validation': "true",
                    'streaming_mode': "xml",
                    'use_single_instance': "False"
    }

    def __init__(self):
        logger.debug("Setting up SA-Eventgen Modular Input")
        self.output = XMLOutputManager()

        self.args = [
            BooleanField("VERBOSE", "VERBOSE", "Verbose mode", required_on_create=True, required_on_edit=True)
        ]
        ModularInput.__init__(self, self.scheme_args, self.args)

    def create_args(self):
        parser = argparse.ArgumentParser(prog="SA-Eventgen")
        args = parser.parse_args()
        args.daemon = False
        args.verbosity = None
        args.version = False
        args.backfill = None
        args.count = None
        args.devnull = False
        args.disableOutputQueue = False
        args.end = None
        args.generators = None
        args.interval = None
        args.keepoutput = False
        args.modinput = False
        args.multiprocess = False
        args.outputters = None
        args.profiler = False
        args.sample = None
        args.version = False
        args.subcommand = 'generate'
        args.verbosity = 0
        args.wsgi = False
        args.log_path = make_splunkhome_path(['var', 'log', 'splunk'])
        args.modinput_mode = True
        return args

    def prepare_config(self, args):
        new_args = {}
        outputer = [key for key in ["keepoutput", "devnull", "modinput"] if getattr(args, key)]
        if len(outputer) > 0:
            new_args["override_outputter"] = outputer[0]
        if getattr(args, "count"):
            new_args["override_count"] = args.count
        if getattr(args, "interval"):
            new_args["override_interval"] = args.interval
        if getattr(args, "backfill"):
            new_args["override_backfill"] = args.backfill
        if getattr(args, "end"):
            new_args["override_end"] = args.end
        if getattr(args, "multiprocess"):
            new_args["threading"] = "process"
        if getattr(args, "generators"):
            new_args["override_generators"] = args.generators
        if getattr(args, "disableOutputQueue"):
            new_args["override_outputqueue"] = args.disableOutputQueue
        if getattr(args, "profiler"):
            new_args["profiler"] = args.profiler
        return new_args

    def run(self, stanza, input_config, **kwargs):
        self.output.initStream()
        logger.info("Initialized streaming")
        try:
            if input_config:
                session_key = input_config.session_key
            logger.info("Input Config is: {}".format(input_config))
            created_arguments = self.create_args()
            new_args = self.prepare_config(created_arguments)
            logger.info("Prepared Config")
            try:
                eventgen = eventgen_core.EventGenerator(created_arguments)
                logger.info("Eventgen object generated")
                config = eventgenconfig.Config(configfile=None, **new_args)
                logger.info("Config object generated")
                config.makeSplunkEmbedded(sessionKey=session_key)
                logger.info("Config made Splunk Embedded")
                eventgen.config = config
                eventgen.config.parse()
                logger.info("Finished config parsing")
                if eventgen.config.samples:
                    for sample in eventgen.config.samples:
                        sample.outputMode = "modinput"
                logger.info("Finished parse")
                eventgen._reload_plugins()
                logger.info("Finished reload")
                eventgen._setup_pools()
                logger.info("Finished setup pools")
                eventgen.start(join_after_start=True)
                logger.info("Finished running start")
            except Exception as e:
                logger.exception(e)
            self.output.finishStream()
            logger.info("Finished streaming")
        except Exception as e:
            logger.error("Main code exit, Exception caught: %s" % e)
            raise e

def handler(signum, frame):
    logger.info("Eventgen Modinput takes signal {0}. Exiting".format(signum))
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGPIPE, handler)
    worker = Eventgen()
    worker.execute()
    sys.exit(0)
