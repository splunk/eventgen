'''
Copyright (C) 2005-2015 Splunk Inc. All Rights Reserved.
'''

from __future__ import division
import sys, os
path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
sys.path.append(path_prepend)
import logging
import time
import splunk_eventgen.__init__ as splunk_eventgen_init
from eventgenconfig import Config
from eventgentimer import Timer

EVENTGEN_VERSION = splunk_eventgen_init.__version__

def parse_args():
    """Parse command line arguments"""

    import argparse
    subparser_dict = {}
    parser = argparse.ArgumentParser(prog='Eventgen',
                                     description='Splunk Event Generation Tool')
    parser.add_argument("-v", "--verbosity", action="count", help="increase output verbosity")
    parser.add_argument("--version", action='version', default=False, version='%(prog)s ' + EVENTGEN_VERSION)
    subparsers = parser.add_subparsers(title='commands', help="valid subcommands", dest='subcommand')
    generate_subparser = subparsers.add_parser('generate', help="Generate events using a supplied config file")
    generate_subparser.add_argument("configfile", help="Location of eventgen.conf, app folder, or name of an app in $SPLUNK_HOME/etc/apps to run")
    generate_subparser.add_argument("-s", "--sample", help="Run specified sample only, overriding outputMode to stdout, disabling all other samples")
    generate_subparser.add_argument("--keepoutput", action="store_true", help="Keep original outputMode for the sample")
    generate_subparser.add_argument("--devnull", action="store_true", help="Set outputMode to devnull")
    generate_subparser.add_argument("--modinput", action="store_true", help="Set outputMode to modinput, to see metadata")
    generate_subparser.add_argument("-c", "--count", type=int, help="Set sample count")
    generate_subparser.add_argument("-i", "--interval", type=int, help="Set sample interval")
    generate_subparser.add_argument("-b", "--backfill", help="Set time to backfill from.  Note: to use it, send the parameter with space in front like ' -60m'")
    generate_subparser.add_argument("-e", "--end", help="Set time to end generation at or a number of intervals to run.  Note: to use it with a time, send the parameter with space in front like ' -10m'")
    generate_subparser.add_argument("--generators", type=int, help="Number of GeneratorWorkers (mappers)")
    generate_subparser.add_argument("--outputters", type=int, help="Number of OutputWorkers (reducers)")
    generate_subparser.add_argument("--disableOutputQueue", action="store_true", help="Disable reducer step")
    generate_subparser.add_argument("--multiprocess", action="store_true", help="Use multiprocesing instead of threading")
    generate_subparser.add_argument("--profiler", action="store_true", help="Turn on cProfiler")
    build_subparser = subparsers.add_parser('build', help="Will build different forms of sa-eventgen")
    build_subparser.add_argument("splunk-app", help="Will create an SPL to use with splunk in an embedded mode.")
    # Help subparser
    # NOTE: Keep this at the end so we can use the subparser_dict.keys() to display valid commands
    help_subparser = subparsers.add_parser('help', help="Display usage on a subcommand")
    helpstr =  "Help on a specific command, valid commands are: " + ", ".join(subparser_dict.keys() + ["help"])
    help_subparser.add_argument("command", nargs='?', default="default", help=helpstr)
    # add subparsers to the subparser dict, this will be used later for usage / help statements.
    subparser_dict['generate'] = generate_subparser
    subparser_dict['build'] = build_subparser
    subparser_dict['help'] = help_subparser

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    args = parser.parse_args()

    if args.version:
        args.print_version()
        sys.exit(0)

    if 'subcommand' not in args:
        logger.warn("Please specify a valid subcommand to run")
        parser.print_help()
        sys.exit(2)

    if args.subcommand == "help" and args.command == "default":
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "help":
        if args.command in subparser_dict.keys():
            subparser_dict[args.command].print_help()
        else:
            parser.print_help()
        sys.exit(0)

    # Allow passing of a Splunk app on the command line and expand the full path before passing up the chain
    if not os.path.exists(args.configfile):
        if 'SPLUNK_HOME' in os.environ:
            if os.path.isdir(os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', args.configfile)):
                args.configfile = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', args.configfile)
    return args

if __name__ == '__main__':
    args = parse_args()
    c = Config(args)
    # Logger is setup by Config, just have to get an instance
    logobj = logging.getLogger('eventgen')
    from eventgenconfig import EventgenAdapter
    adapter = EventgenAdapter(logobj, {'sample': 'null', 'module': 'main'})
    logger = adapter
    logger.info('Starting eventgen')

    c.parse()

    t = Timer(1.0, interruptcatcher=True)

    for s in c.samples:
        if s.interval > 0 or s.mode == 'replay':
            logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app) )
            t = Timer(1.0, s)
            c.sampleTimers.append(t)


    first = True
    outputQueueCounter = 0
    generatorQueueCounter = 0
    while (1):
        try:
            ## Only need to start timers once
            if first:
                if os.name != "nt":
                    c.set_exit_handler(c.handle_exit)
                c.start()
                first = False

            # Every 5 seconds, get values and output basic statistics about our operations
            generatorDecrements = c.generatorQueueSize.totaldecrements()
            outputDecrements = c.outputQueueSize.totaldecrements()
            generatorsPerSec = (generatorDecrements - generatorQueueCounter) / 5
            outputtersPerSec = (outputDecrements - outputQueueCounter) / 5
            outputQueueCounter = outputDecrements
            generatorQueueCounter = generatorDecrements
            logger.info('OutputQueueDepth=%d  GeneratorQueueDepth=%d GeneratorsPerSec=%d OutputtersPerSec=%d' % (c.outputQueueSize.value(), c.generatorQueueSize.value(), generatorsPerSec, outputtersPerSec))
            kiloBytesPerSec = c.bytesSent.valueAndClear() / 5 / 1024
            gbPerDay = (kiloBytesPerSec / 1024 / 1024) * 60 * 60 * 24
            eventsPerSec = c.eventsSent.valueAndClear() / 5
            logger.info('GlobalEventsPerSec=%s KilobytesPerSec=%1f GigabytesPerDay=%1f' % (eventsPerSec, kiloBytesPerSec, gbPerDay))

            # 8/20/15 CS Since we added support for ending a certain time, see if all timers are stopped
            stop = True
            for t in c.sampleTimers:
                if t.stopping == False:
                    stop = False
            if stop:
                c.handle_exit()

            time.sleep(5)

        except KeyboardInterrupt:
            c.handle_exit()


if __name__=="__main__":
    main()
