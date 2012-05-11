'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''
from __future__ import division

import sys, os
if 'SPLUNK_HOME' in os.environ:
    path_prepend = os.environ['SPLUNK_HOME']+'/etc/apps/SA-Eventgen/lib'
else:
    path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

import logging
import threading
import time
import ctypes
import datetime
from select import select
from eventgenconfig import Config
from timeparser import timeDelta2secs

# 5/7/12 CS Working around poor signal handling by python Threads (mainly on BSD implementations
# it seems).  This hopefully handles signals properly and allows us to terminate.
# Copied from http://code.activestate.com/recipes/496960/

def _async_raise(tid, excobj):
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(excobj))
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # """if it returns a number greater than one, you're in trouble, 
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
        raise SystemError("PyThreadState_SetAsyncExc failed")

class Timer(threading.Thread):
    def raise_exc(self, excobj):
        assert self.isAlive(), "thread must be started"
        for tid, tobj in threading._active.items():
            if tobj is self:
                _async_raise(tid, excobj)
                return

        # the thread was alive when we entered the loop, but was not found 
        # in the dict, hence it must have been already terminated. should we raise
        # an exception here? silently ignore?

    def terminate(self):
        # must raise the SystemExit type, instead of a SystemExit() instance
        # due to a bug in PyThreadState_SetAsyncExc
        self.raise_exc(SystemExit)

    # Added by CS 5/7/12 to emulate threading.Timer
    def __init__(self, time, sample):
        self.time = time
        self.stopping = False
        
        self.sample = sample
        threading.Thread.__init__(self)

    def run(self):
        while (1):
            if not self.stopping:
                startTime = datetime.datetime.now()
                self.sample.gen()
                endTime = datetime.datetime.now()
                timeDiff = endTime - startTime

                timeDiffFrac = "%s.%s" % (timeDiff.seconds, timeDiff.microseconds)
                logger.info("Generation of sample '%s' in app '%s' completed in %s seconds" \
                            % (self.sample.name, self.sample.app, timeDiffFrac) )

                timeDiff = timeDelta2secs(timeDiff)
                wholeIntervals = timeDiff / self.sample.interval
                partialInterval = timeDiff % self.sample.interval

                if wholeIntervals > 1:
                    logger.warn("Generation of sample '%s' in app '%s' took longer than interval (%s seconds vs. %s seconds); consider adjusting interval" \
                                % (self.sample.name, self.sample.app, timeDiff, self.sample.interval) )

                partialInterval = self.sample.interval - partialInterval
                logger.debug("Generation of sample '%s' in app '%s' sleeping for %s seconds" \
                            % (self.sample.name, self.sample.app, partialInterval) )

                ## Sleep for partial interval
                time.sleep(partialInterval)
            else:
                sys.exit(0)

    def stop(self):
        self.stopping = True
                     
            
if __name__ == '__main__':
    debug = False
    c = Config()
    # Logger is setup by Config, just have to get an instance
    logger = logging.getLogger('eventgen')
    logger.info('Starting eventgen')
    
    # 5/6/12 CS use select to listen for input on stdin
    # if we timeout, assume we're not splunk embedded
    rlist, _, _ = select([sys.stdin], [], [], 5)
    if rlist:
        sessionKey = sys.stdin.readline().strip()
    else:
        sessionKey = ''
    
    if sessionKey == 'debug':
        c.makeSplunkEmbedded(debug=True)
    elif len(sessionKey) > 0:
        c.makeSplunkEmbedded(sessionKey=sessionKey)
        
    c.parse()

    sampleTimers = []
        
    if c.debug:
        logger.info('Entering debug (single iteration) mode')

    for s in c.samples:
        if s.interval > 0:
            if c.debug:
                s.gen()
            else:
                logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app) )    
                t = Timer(0.1, s) 
                sampleTimers.append(t)
    
    ## Start the timers
    if not c.debug:                
        first = True
        while (1):
            try:
                ## Only need to start timers once
                if first:
                    logger.info('Starting timers')
                    for sampleTimer in sampleTimers:
                        sampleTimer.start()
                    first = False
                time.sleep(600)
            except KeyboardInterrupt:
                for sampleTimer in sampleTimers:
                    sampleTimer.stop()
                sys.exit(0)