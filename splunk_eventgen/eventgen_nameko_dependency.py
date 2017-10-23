from nameko.extensions import DependencyProvider
from nameko.cli.main import setup_parser
import eventgen_core
import logging
from logger.logger_config import listener_logger_config

def create_args():
    parser = setup_parser()
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

    eventgen = eventgen_core.EventGenerator(create_args())
    eventgen._setup_loggers(listener_logger_config)
    _log = logging.getLogger('eventgen_dependency')

    def __init__(self):
        self.configured = False
        self.customconfigured = False
        self.configfile = 'N/A'
        self._log.info("mem reference to eventgen: {}".format(self.eventgen))

    def get_dependency(self, worker_ctx):
        return self





