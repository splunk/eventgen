from nameko.extensions import DependencyProvider
import eventgen_core

class EventgenDependency():

    def __init__(self):
        print 'Eventgen Dependency initialized'
        self.configured = False
        self.configfile = 'N/A'
        self.create_args()
        self.configure_default_args()
        self.eventgen = eventgen_core.EventGenerator(self.args)

    def create_args(self):
        from nameko.cli.main import setup_parser
        parser = setup_parser()
        self.args = parser.parse_args()
        self.args.daemon = False
        self.args.subcommand = 'wsgi'
        self.verbosity = None
        self.version = False

    def configure_default_args(self):
        self.args.backfill = None
        self.args.count = None
        self.args.devnull = False
        self.args.disableOutputQueue = False
        self.args.end = None
        self.args.generators = None
        self.args.interval = None
        self.args.keepoutput = False
        self.args.modinput = False
        self.args.multiprocess = False
        self.args.outputters = None
        self.args.profiler = False
        self.args.sample = None
        self.args.version = False
        self.args.subcommand = 'generate'
        self.args.verbosity = 1
        self.args.wsgi = True

