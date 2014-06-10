'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''
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
import cProfile

class Timer(threading.Thread):
    time = None
    stopping = None
    interruptcatcher = None
    countdown = None
    
    # Added by CS 5/7/12 to emulate threading.Timer
    def __init__(self, time, sample=None, interruptcatcher=None):
        self.time = time
        self.stopping = False
        self.interruptcatcher = interruptcatcher
        self.countdown = 0
        
        self.sample = sample
        threading.Thread.__init__(self)

    def run(self):
        globals()['threadrun'] = self.real_run
        cProfile.run("threadrun()", "eventgenprof_%s" % self.sample.name)

    def real_run(self):
        running = True
        if self.sample.delay > 0:
            logger.info("Sample set to delay %s, sleeping." % s.delay)
            time.sleep(self.sample.delay)
        while (running):
            if not self.stopping:
                if not self.interruptcatcher:
                    if self.countdown <= 0:
                        partialInterval = self.sample.gen()

                        self.countdown = partialInterval

                        ## Sleep for partial interval
                        # If we're going to sleep for longer than the default check for kill interval
                        # go ahead and flush output so we're not just waiting
                        if partialInterval > self.time:
                            self.sample._out.flush(force=True)

                            # Make sure that we're sleeping an accurate amount of time, including the
                            # partial seconds.  After the first sleep, we'll sleep in increments of
                            # self.time to make sure we're checking for kill signals.
                            sleepTime = self.time + (partialInterval % self.time)
                            self.countdown -= sleepTime
                        else:
                            sleepTime = partialInterval
                            self.countdown = 0
                          
                        logger.debug("Generation of sample '%s' in app '%s' sleeping for %f seconds" \
                                    % (self.sample.name, self.sample.app, partialInterval) )    
                        if sleepTime > 0:
                            self.sample.saveState()
                            time.sleep(sleepTime)
                    else:
                        self.countdown -= self.time
                        time.sleep(self.time)
                else:
                    time.sleep(self.time)
            else:
                running = False
                # sys.exit(0)

    def stop(self):
        self.sample.saveState()
        self.stopping = True
                     
            
# Copied from http://danielkaes.wordpress.com/2009/06/04/how-to-catch-kill-events-with-python/
def set_exit_handler(func):
	if os.name == "nt":
		try:
			import win32api
			win32api.SetConsoleCtrlHandler(func, True)
		except ImportError:
			version = ".".join(map(str, sys.version_info[:2]))
			raise Exception("pywin32 not installed for Python " + version)
	else:
		import signal
		signal.signal(signal.SIGTERM, func)
		signal.signal(signal.SIGINT, func)
    
def handle_exit(sig=None, func=None):
    print '\n\nCaught kill, exiting...'
    for sampleTimer in sampleTimers:
        sampleTimer.stop()
    sys.exit(0)
    		

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

    sampleTimers = []

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
                logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app) )    
                t = Timer(1.0, s) 
                sampleTimers.append(t)
    
    ## Start the timers
    if not c.runOnce:
        set_exit_handler(handle_exit)
        first = True
        while (1):
            try:
                ## Only need to start timers once
                if first:
                    logger.info('Starting timers')
                    for sampleTimer in sampleTimers:
                        sampleTimer.start()
                    first = False
                time.sleep(5)
            except KeyboardInterrupt:
                handle_exit()