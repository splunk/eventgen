from nameko.extensions import DependencyProvider
import eventgen_core
import logging
import argparse
import sys
import os
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
CUSTOM_CONFIG_PATH = os.path.realpath(os.path.join(FILE_PATH, "default", "eventgen_wsgi.conf"))

# For some reason, the args from __main__ get passed to eventgen_nameko_dependency and causes this error:
# usage: eventgen_nameko_dependency [-h]
# eventgen_nameko_dependency: error: unrecognized arguments: --role master --config server_conf.yml
sys.argv = [sys.argv.pop(0)]

def create_args():
    parser = argparse.ArgumentParser(prog="eventgen_nameko_dependency")
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
    args.verbosity = 1
    args.wsgi = True
    args.modinput_mode = False
    return args

class EventgenDependency(DependencyProvider):

    arguments = create_args()
    eventgen = eventgen_core.EventGenerator(arguments)
    log = logging.getLogger('eventgen_dependency')
    log.info("EventgenDependency Init. Memory reference to eventgen object: {}".format(eventgen))

    configured = False
    configfile = 'N/A'

    if os.path.isfile(CUSTOM_CONFIG_PATH):
        configured = True
        configfile = CUSTOM_CONFIG_PATH
        eventgen.reload_conf(CUSTOM_CONFIG_PATH)

    def get_dependency(self, worker_ctx):
        return self

    def refresh_eventgen(self):
        self.eventgen = eventgen_core.EventGenerator(self.arguments)
        self.configured = False
        self.configfile = 'N/A'
        self.log.info("Refreshed Eventgen Object: {}".format(self.eventgen))
