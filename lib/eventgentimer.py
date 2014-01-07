import threading
import time
import logging
from eventgenconfig import Config
import sys
import datetime
import copy
from Queue import Full

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

        logger.debug('Starting timer for %s' % sample.name if sample is not None else "None")

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
        # TODO hide this behind a config setting
        if True:
            import cProfile
            globals()['threadrun'] = self.real_run
            cProfile.runctx("threadrun()", globals(), locals(), "eventgen_timer_%s" % self.sample.name)
        else:
            self.real_run()

    def real_run(self):
        if self.sample.delay > 0:
            logger.info("Sample set to delay %s, sleeping." % s.delay)
            time.sleep(self.sample.delay)

        # 12/29/13 CS Queueable plugins pull from the worker queue as soon as items
        # are in it and farm it out to a pool of workers to generate.
        # Non-Queueable plugins will run as a seperate process all on their own generating
        # events, and is the same as we used to operate.

        # 12/29/13 Non Queueable, same as before
        plugin = c.getPlugin('generator.'+self.sample.generator)
        logger.debugv("Generating for class '%s' for generator '%s' queueable: %s" % (plugin.__name__, self.sample.generator, plugin.queueable))

        if not plugin.queueable:
            # Get an instance of the plugin instead of the class itself
            plugin = plugin(self.sample)
            plugin.setupBackfill()
        else:
            plugin(self.sample).setupBackfill()

        while (1):
            if not self.stopping:
                if not self.interruptcatcher:
                    if self.countdown <= 0:
                        # 12/15/13 CS Moving the rating to a separate plugin architecture
                        count = self.rater.rate()

                        # Override earliest and latest during backfill until we're at current time
                        if self.sample.backfill != None and not self.sample.backfilldone:
                            if self.sample.backfillts >= self.sample.now(realnow=True):
                                logger.info("Backfill complete")
                                self.sample.backfilldone = True
                            else:
                                logger.debug("Still backfilling for sample '%s'.  Currently at %s" % (self.sample.name, self.sample.backfillts))

                        if not plugin.queueable:
                            try:
                                partialInterval = plugin.gen(count, None, None)
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
                                # sleepTime = self.time + (partialInterval % self.time)
                                # self.countdown -= sleepTime
                            # else:
                            #     sleepTime = partialInterval
                            #     self.countdown = 0
                              
                            logger.debug("Generation of sample '%s' in app '%s' sleeping for %f seconds" \
                                        % (self.sample.name, self.sample.app, partialInterval) ) 
                            logger.debug("Queue depth for sample '%s' in app '%s': %d" % (self.sample.name, self.sample.app, c.outputQueue.qsize()))   
                            # if sleepTime > 0:
                            if self.countdown > 0:
                                self.sample.saveState()
                        else:
                            # Check for if we're backfilling still

                            # Determine earliest and latest times to send

                            # Put into the queue to be generated
                            # TODO Temporary, just gnerate counte events for now
                            logger.debug("Putting %d events in queue for sample '%s'" % (count, self.sample.name))
                            stop = False
                            while not stop:
                                try:
                                    c.generatorQueue.put((copy.copy(self.sample), count, self.sample.earliestTime(), self.sample.latestTime()), block=True, timeout=1.0)
                                    stop = True
                                except Full:
                                    logger.warn("Generator Queue Full, looping")
                                    if self._sample.stopping:
                                        stop = True
                                    pass
                            # c.generatorQueue.put(self.sample, count, earliestTime, latestTime)

                            # Sleep until we're supposed to wake up and generate more events
                            self.countdown = self.sample.interval

                        # Clear cache for timestamp
                        self.sample.timestamp = None

                        # No rest for the wicked!  Or while we're doing backfill
                        if self.sample.backfill != None and not self.sample.backfilldone:
                            # Since we would be sleeping, increment the timestamp by the amount of time we're sleeping
                            incsecs = round(self.countdown / 1, 0)
                            incmicrosecs = self.countdown % 1
                            self.sample.backfillts += datetime.timedelta(seconds=incsecs, microseconds=incmicrosecs)
                            self.countdown = 0
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
        self.sample.stopping = True
                     
    		