'''
Copyright (C) 2005-2015 Splunk Inc. All Rights Reserved.
'''

from __future__ import division

# import rpdb2; rpdb2.start_embedded_debugger('some_password')

import sys, os
path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

import logging
import time
import sys
from select import select
from eventgenconfig import Config
from eventgentimer import Timer
from eventgenoutput import Output
import argparse

def parse_args():
    """Parse command line arguments"""

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("configfile", 
                        help="Location of eventgen.conf, app folder, or name of an app in $SPLUNK_HOME/etc/apps to run")
    parser.add_argument("-v", "--verbosity", action="count",
                        help="increase output verbosity")
    # parser.add_argument("-e", "--earliest", metavar="ISO8601_DateTime",
    #                     help="Start generating events at this time")
    # parser.add_argument("-l", "--latest", metavar="ISO8601_DateTime",
    #                     help="Stop generating events at this time.  Note if this is not specified, eventgen will run until terminated by the user or parent process.")
    group = parser.add_argument_group("sample", "Run eventgen with only one sample for testing")
    group.add_argument("-s", "--sample",
                        help="Run specified sample only, overriding outputMode to stdout, disabling all other samples")
    megroup = group.add_mutually_exclusive_group()
    megroup.add_argument("--keepoutput", action="store_true",
                        help="Keep original outputMode for the sample")
    megroup.add_argument("--devnull", action="store_true",
                        help="Set outputMode to devnull")
    megroup.add_argument("--modinput", action="store_true",
                        help="Set outputMode to modinput, to see metadata")
    group.add_argument("-c", "--count", type=int,
                        help="Set sample count")
    group.add_argument("-i", "--interval", type=int,
                        help="Set sample interval")
    group.add_argument("-b", "--backfill",
                        help="Set time to backfill from.  Note: to use it, send the parameter with space in front like ' -60m'")
    group.add_argument("-e", "--end",
                        help="Set time to end generation at or a number of intervals to run.  Note: to use it with a time, send the parameter with space in front like ' -10m'")

    group = parser.add_argument_group("Advanced", "Advanced settings for performance testing")
    group.add_argument("--generators", type=int, help="Number of GeneratorWorkers (mappers)")
    group.add_argument("--outputters", type=int, help="Number of OutputWorkers (reducers)")
    group.add_argument("--disableOutputQueue", action="store_true", help="Disable reducer step")
    group.add_argument("--multiprocess", action="store_true", help="Use multiprocesing instead of threading")
    group.add_argument("--profiler", action="store_true", help="Turn on cProfiler")

    args = parser.parse_args()

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
