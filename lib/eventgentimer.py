import threading
import time
import logging
from eventgenconfig import Config
import sys
import datetime, time
import copy
from Queue import Full
from eventgenoutput import Output
import marshal
import random

class Timer(threading.Thread):
    """
    Overall governor in Eventgen.  A timer is created for every sample in Eventgen.  The Timer has the responsibility
    for executing each sample.  There are two ways the timer can execute:
        * Queueable
        * Non-Queueable

    For Queueable plugins, we place a work item in the generator queue.  Generator workers pick up the item from the generator
    queue and do work.  This queueing architecture allows for parallel execution of workers.  Workers then place items in the 
    output queue for Output workers to pick up and output.

    However, for some generators, like the replay generator, we need to keep a single view of state of where we are in the replay.
    This means we cannot generate items in parallel.  This is why we also offer Non-Queueable plugins.  In the case of 
    Non-Queueable plugins, the Timer class calls the generator method of the plugin directly, tracks the amount of time
    the plugin takes to generate and sleeps the remaining interval before calling generate again.
    """


    time = None
    stopping = None
    interruptcatcher = None
    countdown = None
    
    # Added by CS 5/7/12 to emulate threading.Timer
    def __init__(self, time, sample=None, interruptcatcher=None):
        # Logger already setup by config, just get an instance
        logobj = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        if sample == None:
            adapter = EventgenAdapter(logobj, {'module': 'Timer', 'sample': 'null'})
        else:
            adapter = EventgenAdapter(logobj, {'module': 'Timer', 'sample': sample.name})
        self.logger = adapter

        globals()['c'] = Config()

        self.logger.debug('Initializing timer for %s' % sample.name if sample is not None else "None")

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
        """
        Simple wrapper method to determine whether we should be running inside python's profiler or not
        """
        if c.profiler:
            import cProfile
            globals()['threadrun'] = self.real_run
            cProfile.runctx("threadrun()", globals(), locals(), "eventgen_timer_%s" % self.sample.name)
        else:
            self.real_run()

    def real_run(self):
        """
        Worker function of the Timer class.  Determine whether a plugin is queueable, and either
        place an item in the generator queue for that plugin or call the plugin's gen method directly.

        Actual work for queueable plugins is done in lib/plugins/generatorworker.py
        """
        if self.sample.delay > 0:
            self.logger.info("Sample set to delay %s, sleeping." % s.delay)
            time.sleep(self.sample.delay)
            

        # 12/29/13 CS Queueable plugins pull from the worker queue as soon as items
        # are in it and farm it out to a pool of workers to generate.
        # Non-Queueable plugins will run as a seperate process all on their own generating
        # events, and is the same as we used to operate.

        # 12/29/13 Non Queueable, same as before
        plugin = c.getPlugin('generator.'+self.sample.generator, self.sample)
        self.logger.debugv("Generating for class '%s' for generator '%s' queueable: %s" % (plugin.__name__, self.sample.generator, plugin.queueable))
        
        # Wait a random amount of time, try to grab a lock, then start up the timer
        time.sleep(random.randint(0, 100)/1000)
        self.logger.debug("Timer creating plugin for '%s'" % self.sample.name)
        with c.copyLock:
            while c.timersStarting.value() > 0:
                self.logger.debug("Waiting for exclusive lock to start for timer '%s'" % self.sample.name)
                time.sleep(0.1)
                
            c.timersStarting.increment()
            p = plugin(self.sample)
            self.executions = 0
            
            c.timersStarting.decrement()
            c.timersStarted.increment()
        
        # 9/6/15 Don't do any work until all the timers have started
        while c.timersStarted.value() < len(c.sampleTimers):
            self.logger.debug("Not all timers started, sleeping for timer '%s'" % self.sample.name)
            time.sleep(1.0)
        try:
            p.setupBackfill()
        except ValueError as e:
            self.logger.error("Exception during backfill for sample '%s': '%s'" % (self.sample.name, str(e)))
            

        while (1):
            if not self.stopping:
                if not self.interruptcatcher:
                    if self.countdown <= 0:
                        # 12/15/13 CS Moving the rating to a separate plugin architecture
                        count = self.rater.rate()

                        et = self.sample.earliestTime()
                        lt = self.sample.latestTime()

                        # Override earliest and latest during backfill until we're at current time
                        if self.sample.backfill != None and not self.sample.backfilldone:
                            if self.sample.backfillts >= self.sample.now(realnow=True):
                                self.logger.info("Backfill complete")
                                self.sample.backfilldone = True
                            else:
                                self.logger.debug("Still backfilling for sample '%s'.  Currently at %s" % (self.sample.name, self.sample.backfillts))

                        if not p.queueable:
                            try:
                                partialInterval = p.gen(count, et, lt)
                            # 11/24/13 CS Blanket catch for any errors
                            # If we've gotten here, all error correction has failed and we
                            # need to gracefully exit providing some error context like what sample
                            # we came from
                            except (KeyboardInterrupt, SystemExit):
                                raise
                            except:
                                import traceback
                                self.logger.error('Exception in sample: %s\n%s' % (self.sample.name, \
                                        traceback.format_exc()))
                                sys.stderr.write('Exception in sample: %s\n%s' % (self.sample.name, \
                                        traceback.format_exc()))
                                sys.exit(1)

                            self.countdown = partialInterval
                            self.executions += 1

                            ## Sleep for partial interval
                            # If we're going to sleep for longer than the default check for kill interval
                            # go ahead and flush output so we're not just waiting
                            # if partialInterval > self.time:
                            #     self.logger.debugv("Flushing because we're sleeping longer than a polling interval")
                            #     self.sample.out.flush()

                              
                            self.logger.debug("Generation of sample '%s' in app '%s' sleeping for %f seconds" \
                                        % (self.sample.name, self.sample.app, partialInterval) ) 
                            # logger.debug("Queue depth for sample '%s' in app '%s': %d" % (self.sample.name, self.sample.app, c.outputQueue.qsize()))   
                        else:
                            # Put into the queue to be generated
                            stop = False
                            while not stop:
                                try:
                                    c.generatorQueue.put((self.sample.name, count, (time.mktime(et.timetuple())*(10**6)+et.microsecond), (time.mktime(lt.timetuple())*(10**6)+lt.microsecond)), block=True, timeout=1.0)
                                    c.generatorQueueSize.increment()
                                    self.logger.debug("Put %d events in queue for sample '%s' with et '%s' and lt '%s'" % (count, self.sample.name, et, lt))
                                    stop = True
                                except Full:
                                    self.logger.warning("Generator Queue Full, looping")
                                    if self.stopping:
                                        stop = True
                                    pass

                            # Sleep until we're supposed to wake up and generate more events
                            self.countdown = self.sample.interval
                            self.executions += 1

                        # Clear cache for timestamp
                        # self.sample.timestamp = None

                        # No rest for the wicked!  Or while we're doing backfill
                        if self.sample.backfill != None and not self.sample.backfilldone:
                            # Since we would be sleeping, increment the timestamp by the amount of time we're sleeping
                            incsecs = round(self.countdown / 1, 0)
                            incmicrosecs = self.countdown % 1
                            self.sample.backfillts += datetime.timedelta(seconds=incsecs, microseconds=incmicrosecs)
                            self.countdown = 0

                        if self.countdown > 0:
                            self.sample.saveState()

                        # 8/20/15 CS Adding support for ending generation at a certain time
                        if self.sample.end != None:
                            # 3/16/16 CS Adding support for ending on a number of executions instead of time
                            # Should be fine with storing state in this sample object since each sample has it's own unique
                            # timer thread
                            if self.sample.endts == None:
                                if self.executions >= self.sample.end:
                                    self.logger.info("End executions %d reached, ending generation of sample '%s'" % (self.sample.end, self.sample.name))
                                    self.stopping = True
                            elif lt >= self.sample.endts:
                                self.logger.info("End Time '%s' reached, ending generation of sample '%s'" % (self.sample.endts, self.sample.name))
                                self.stopping = True
                    else:
                        self.countdown -= self.time
                        time.sleep(self.time)
                else:
                    time.sleep(self.time)
            else:
                self.logger.info("Stopped timer for sample '%s'" % self.sample.name)
                sys.exit(0)

    def stop(self):
        self.logger.info("Stopping timer for sample '%s'" % self.sample.name)
        self.sample.saveState()
        self.stopping = True
                     
    		
