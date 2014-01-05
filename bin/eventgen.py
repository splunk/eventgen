'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''

# TODO Allow override of any configuration variable from the command line

from __future__ import division

import sys, os
path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

import logging
import threading
import multiprocessing
import time
import datetime
from select import select
from eventgenconfig import Config
from eventgentimer import Timer
from eventgenoutput import Output

if __name__ == '__main__':
    debug = False
    c = Config()
    # Logger is setup by Config, just have to get an instance
    logger = logging.getLogger('eventgen')
    logger.info('Starting eventgen')
    
    # 5/6/12 CS use select to listen for input on stdin
    # if we timeout, assume we're not splunk embedded
    # Only support standalone mode on Unix due to limitation with select()
    if os.name != "nt":
        rlist, _, _ = select([sys.stdin], [], [], 5)
        if rlist:
            sessionKey = sys.stdin.readline().strip()
        else:
            sessionKey = ''
    else:
        sessionKey = sys.stdin.readline().strip()
    
    if sessionKey == 'debug':
        c.makeSplunkEmbedded(runOnce=True)
    elif len(sessionKey) > 0:
        c.makeSplunkEmbedded(sessionKey=sessionKey)
        
    c.parse()

    if c.runOnce:
        logger.info('Entering debug (single iteration) mode')

    # Hopefully this will catch interrupts, signals, etc
    # To allow us to stop gracefully
    t = Timer(1.0, interruptcatcher=True)

    for s in c.samples:
        if s.interval > 0 or s.mode == 'replay':
            if c.runOnce:
                s.gen()
            else:
                logger.info("Setting up Output class for sample '%s' in app '%s'" % (s.name, s.app))
                s.out = Output(s)
                if s.backfillSearchUrl == None:
                    s.backfillSearchUrl = s.splunkUrl
                logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app) )    
                t = Timer(1.0, s) 
                c.sampleTimers.append(t)
    
    ## Start the timers
    if not c.runOnce:
        if os.name != "nt":
            c.set_exit_handler(c.handle_exit)
        first = True
        while (1):
            try:
                ## Only need to start timers once
                if first:
                    c.start()
                    first = False
                logger.info('Output Queue depth: %d  Generator Queue depth: %d' % (c.outputQueue.qsize(), c.generatorQueue.qsize()))
                time.sleep(5)
            except KeyboardInterrupt:
                c.handle_exit()