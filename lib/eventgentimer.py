import threading
import time
import logging
from eventgenconfig import Config
import sys

class Timer(threading.Thread):
# class Timer(multiprocessing.Process):
    time = None
    stopping = None
    interruptcatcher = None
    countdown = None
    
    # Added by CS 5/7/12 to emulate threading.Timer
    def __init__(self, time, sample=None, interruptcatcher=None):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        globals()['c'] = Config()

        self.time = time
        self.stopping = False
        self.interruptcatcher = interruptcatcher
        self.countdown = 0
        
        self.sample = sample
        if self.sample != None:
            self.rater = c.getPlugin('rater.'+self.sample.rater)(self.sample)
        threading.Thread.__init__(self)
        # multiprocessing.Process.__init__(self)

    def run(self):
        if self.sample.delay > 0:
            logger.info("Sample set to delay %s, sleeping." % s.delay)
            time.sleep(self.sample.delay)
        while (1):
            if not self.stopping:
                if not self.interruptcatcher:
                    if self.countdown <= 0:
                        # 12/15/13 CS Moving the rating to a separate plugin architecture
                        count = self.rater.rate()

                        try:
                            partialInterval = self.sample.gen(count, None, None)
                        # 11/24/13 CS Blanket catch for any errors
                        # If we've gotten here, all error correction has failed and we
                        # need to gracefully exit providing some error context like what sample
                        # we came from
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except:
                            import traceback
                            logger.error('Exception in sample: %s\n%s' % (self.sample.name, \
                                    traceback.format_exc()))
                            sys.stderr.write('Exception in sample: %s\n%s' % (self.sample.name, \
                                    traceback.format_exc()))
                            sys.exit(1)

                        self.countdown = partialInterval

                        ## Sleep for partial interval
                        # If we're going to sleep for longer than the default check for kill interval
                        # go ahead and flush output so we're not just waiting
                        if partialInterval > self.time:
                            logger.debugv("Flushing because we're sleeping longer than a polling interval")
                            self.sample.out.flush()

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
                        logger.debug("Queue depth for sample '%s' in app '%s': %d" % (self.sample.name, self.sample.app, c.outputQueue.qsize()))   
                        if sleepTime > 0:
                            self.sample.saveState()
                            time.sleep(sleepTime)
                    else:
                        self.countdown -= self.time
                        time.sleep(self.time)
                else:
                    time.sleep(self.time)
            else:
                sys.exit(0)

    def stop(self):
        self.sample.saveState()
        self.stopping = True
                     
    		