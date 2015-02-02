import threading
import time
import logging
from eventgenconfig import Config
import sys
import datetime, time
import copy
from Queue import Full
try:
    import zmq
except ImportError:
    pass
from eventgenoutput import Output
import marshal

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

        self.logger.debug('Starting timer for %s' % sample.name if sample is not None else "None")

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

        Actual work for queueable plugins is done in lib/plugins/generatorworker.python
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

        # if not plugin.queueable:
        #     # Get an instance of the plugin instead of the class itself
        #     if self.sample.out == None:
        #         self.logger.info("Setting up Output class for sample '%s' in app '%s'" % (self.sample.name, self.sample.app))
        #         self.sample.out = Output(self.sample)
        #     with c.copyLock:
        #         plugin = plugin(self.sample)
        #     plugin.setupBackfill()
        # else:
        with c.copyLock:
            p = plugin(self.sample)
        p.setupBackfill()

        if c.queueing == 'zeromq':
            context = zmq.Context()
            self.sender = context.socket(zmq.PUSH)
            self.sender.connect(c.zmqBaseUrl+(':' if c.zmqBaseUrl.startswith('tcp') else '/')+str(c.zmqBasePort+2))

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

                            ## Sleep for partial interval
                            # If we're going to sleep for longer than the default check for kill interval
                            # go ahead and flush output so we're not just waiting
                            if partialInterval > self.time:
                                self.logger.debugv("Flushing because we're sleeping longer than a polling interval")
                                self.sample.out.flush()

                              
                            self.logger.debug("Generation of sample '%s' in app '%s' sleeping for %f seconds" \
                                        % (self.sample.name, self.sample.app, partialInterval) ) 
                            # logger.debug("Queue depth for sample '%s' in app '%s': %d" % (self.sample.name, self.sample.app, c.outputQueue.qsize()))   
                        else:
                            # Put into the queue to be generated
                            stop = False
                            while not stop:
                                try:
                                    if c.queueing == 'python':
                                        c.generatorQueue.put((self.sample.name, count, (time.mktime(et.timetuple())*1000+et.microsecond), (time.mktime(lt.timetuple())*1000+lt.microsecond)), block=True, timeout=1.0)
                                    elif c.queueing == 'zeromq':
                                        self.sender.send(marshal.dumps((self.sample.name, count, (time.mktime(et.timetuple())+et.microsecond), (time.mktime(lt.timetuple())+lt.microsecond))))
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
                     
    		
