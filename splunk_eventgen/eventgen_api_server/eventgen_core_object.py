import argparse
import logging

import splunk_eventgen.eventgen_core as eventgen_core

class EventgenCoreObject():
    def __init__(self):
        self.logger = logging.getLogger('eventgen_server')
        self.eventgen_core_object = eventgen_core.EventGenerator(self._create_args())
        self.configured = False
        self.configfile = None
    
    def refresh_eventgen_core_object(self):
        self.eventgen_core_object = eventgen_core.EventGenerator(self._create_args())
        self.configured = False
        self.configfile = 'N/A'
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
        args.multiprocess = False
        args.outputters = None
        args.profiler = False
        args.sample = None
        args.version = False
        args.subcommand = 'generate'
        args.verbosity = 20
        args.wsgi = True
        args.modinput_mode = False
        return args

