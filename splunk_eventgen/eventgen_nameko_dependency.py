from nameko.extensions import DependencyProvider
import eventgen_core
import logging
import argparse
import sys

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
    return args

class EventgenDependency(DependencyProvider):

    arguments = create_args()
    eventgen = eventgen_core.EventGenerator(arguments)
    log = logging.getLogger('eventgen_dependency')
    log.info("EventgenDependency Init. Memory reference to eventgen object: {}".format(eventgen))

    configured = False
    customconfigured = False
    configfile = 'N/A'

    def get_dependency(self, worker_ctx):
        return self
