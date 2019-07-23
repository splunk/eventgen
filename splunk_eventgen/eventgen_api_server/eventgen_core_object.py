import argparse
import logging
import os

import splunk_eventgen.eventgen_core as eventgen_core

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
CUSTOM_CONFIG_PATH = os.path.realpath(os.path.join(FILE_PATH, "..", "default", "eventgen_wsgi.conf"))

class EventgenCoreObject():
    def __init__(self):
        self.logger = logging.getLogger('eventgen_server')
        self.eventgen_core_object = eventgen_core.EventGenerator(self._create_args())
        self.configured = False
        self.configfile = None
        self.check_and_configure_eventgen()
    
    def check_and_configure_eventgen(self):
        if os.path.isfile(CUSTOM_CONFIG_PATH):
            self.configured = True
            self.configfile = CUSTOM_CONFIG_PATH
            self.eventgen_core_object.reload_conf(CUSTOM_CONFIG_PATH)
            self.logger.info("Configured Eventgen from {}".format(CUSTOM_CONFIG_PATH))

    def refresh_eventgen_core_object(self):
        self.eventgen_core_object.kill_processes()
        self.eventgen_core_object = eventgen_core.EventGenerator(self._create_args())
        self.configured = False
        self.configfile = None
        self.check_and_configure_eventgen()
        self.logger.info("Refreshed the eventgen core object")

    def _create_args(self):
        args = argparse.Namespace()
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
        args.multiprocess = True
        args.outputters = None
        args.profiler = False
        args.sample = None
        args.version = False
        args.subcommand = 'generate'
        args.verbosity = 20
        args.wsgi = True
        args.modinput_mode = False
        args.generator_queue_size = 1500
        return args
