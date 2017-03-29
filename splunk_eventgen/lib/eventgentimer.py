import logging
import sys
import datetime, time
import copy

class Timer(object):
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
    countdown = None

    # Added by CS 5/7/12 to emulate threading.Timer
    def __init__(self, time, sample=None, config=None, genqueue=None, outputqueue=None, loggingqueue=None):
        # Logger already setup by config, just get an instance
        # setup default options
        self.profiler = config.profiler
        self.config = config
        self.sample = sample
        self.end = getattr(self.sample, "end", None)
        self.endts = getattr(self.sample, "endts", None)
        self.generatorQueue = genqueue
        self.outputQueue = outputqueue
        self.time = time
        self.stopping = False
        self.countdown = 0
        #enable the logger
        self._setup_logging()
        self.logger.debug('Initializing timer for %s' % sample.name if sample is not None else "None")
        # load plugins
        if self.sample != None:
            self.rater = self.config.getPlugin('rater.'+self.sample.rater)(self.sample)
            self.generatorPlugin = self.config.getPlugin('generator.'+self.sample.generator, self.sample)

    # loggers can't be pickled due to the lock object, remove them before we try to pickle anything.
    def __getstate__(self):
        temp = self.__dict__
        if getattr(self, 'logger', None):
            temp.pop('logger', None)
        return temp

    def __setstate__(self, d):
        self.__dict__ = d
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')

    def run(self):
        """
        Simple wrapper method to determine whether we should be running inside python's profiler or not
        """
        if self.profiler:
            import cProfile
            globals()['threadrun'] = self.real_run
            cProfile.runctx("threadrun()", globals(), locals(), "eventgen_timer_%s" % self.sample.name)
        else:
            self.real_run()

    def real_run(self):
        """
        Worker function of the Timer class.  Determine whether a plugin is queueable, and either
        place an item in the generator queue for that plugin or call the plugin's gen method directly.
        """
        if self.sample.delay > 0:
            self.logger.info("Sample set to delay %s, sleeping." % self.sample.delay)
            time.sleep(self.sample.delay)
            
        self.logger.debug("Timer creating plugin for '%s'" % self.sample.name)

        self.executions = 0
        end = False
        while not end:
            # Need to be able to stop threads by the main thread or this thread. self.config will stop all threads
            # referenced in the config object, while, self.stopping will only stop this one.
            if self.config.stopping or self.stopping:
                end = True
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
                try:
                    # create a generator object, then place it in the generator queue.
                    start_time=(time.mktime(et.timetuple())*(10**6)+et.microsecond)
                    end_time=(time.mktime(lt.timetuple())*(10**6)+lt.microsecond)
                    # self.generatorPlugin is only an instance, now we need a real plugin.
                    # make a copy of the sample so if it's mutated by another process, it won't mess up geeneration
                    # for this generator.
                    copy_sample = copy.copy(self.sample)
                    genPlugin = self.generatorPlugin(sample=copy_sample)
                    # need to make sure we set the queue right if we're using multiprocessing or thread modes
                    genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
                    genPlugin.updateCounts(count=count,
                                           start_time=et,
                                           end_time=lt)
                    self.generatorQueue.put(genPlugin)
                    self.logger.debug("Put %d events in queue for sample '%s' with et '%s' and lt '%s'" % (count, self.sample.name, et, lt))
                #TODO: put this back to just catching a full queue
                except Exception as e:
                    self.logger.exception(e)
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
                if self.end != None:
                    # 3/16/16 CS Adding support for ending on a number of executions instead of time
                    # Should be fine with storing state in this sample object since each sample has it's own unique
                    # timer thread
                    if self.endts == None:
                        if self.executions >= self.end:
                            self.logger.info("End executions %d reached, ending generation of sample '%s'" % (self.end, self.sample.name))
                            self.stopping = True
                            end = True
                    elif lt >= self.endts:
                        self.logger.info("End Time '%s' reached, ending generation of sample '%s'" % (self.sample.endts, self.sample.name))
                        self.stopping = True
                        end = True
            else:
                self.countdown -= self.time
                time.sleep(self.time)
