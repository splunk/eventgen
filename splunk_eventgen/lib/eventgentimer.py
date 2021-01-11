import datetime
import time

from splunk_eventgen.lib.logging_config import logger


class Timer(object):
    """
    Overall governor in Eventgen. A timer is created for every sample in Eventgen. The Timer has the responsibility
    for executing each sample. There are two ways the timer can execute:
        * Queueable
        * Non-Queueable

    For Queueable plugins, we place a work item in the generator queue.  Generator workers pick up the item from the
    generator queue and do work. This queueing architecture allows for parallel execution of workers. Workers then place
    items in the output queue for Output workers to pick up and output.

    However, for some generators, like the replay generator, we need to keep a single view of state of where we are in
    the replay. This means we cannot generate items in parallel.  This is why we also offer Non-Queueable plugins. In
    the case of Non-Queueable plugins, the Timer class calls the generator method of the plugin directly, tracks the
    amount of time the plugin takes to generate and sleeps the remaining interval before calling generate again.
    """

    time = None
    countdown = None

    # Added by CS 5/7/12 to emulate threading.Timer
    def __init__(
        self,
        time,
        sample=None,
        config=None,
        genqueue=None,
        outputqueue=None,
        loggingqueue=None,
    ):
        # Logger already setup by config, just get an instance
        # setup default options
        self.profiler = config.profiler
        self.config = config
        self.sample = sample
        self.end = getattr(self.sample, "end", -1)
        self.endts = getattr(self.sample, "endts", None)
        self.generatorQueue = genqueue
        self.outputQueue = outputqueue
        self.time = time
        self.stopping = False
        self.countdown = 0
        self.executions = 0
        self.interval = getattr(self.sample, "interval", config.interval)
        logger.debug(
            "Initializing timer for %s" % sample.name if sample is not None else "None"
        )
        # load plugins
        if self.sample is not None:
            rater_class = self.config.getPlugin(
                "rater." + self.sample.rater, self.sample
            )
            backrater_class = self.config.getPlugin("rater.backfill", self.sample)
            perdayrater_class = self.config.getPlugin("rater.perdayvolume", self.sample)
            self.rater = rater_class(self.sample)
            self.backrater = backrater_class(self.sample)
            self.perdayrater = perdayrater_class(self.sample)
            self.generatorPlugin = self.config.getPlugin(
                "generator." + self.sample.generator, self.sample
            )
            self.outputPlugin = self.config.getPlugin(
                "output." + self.sample.outputMode, self.sample
            )
            if self.sample.timeMultiple < 0:
                logger.error(
                    "Invalid setting for timeMultiple: {}, value should be positive".format(
                        self.sample.timeMultiple
                    )
                )
            elif self.sample.timeMultiple != 1:
                self.interval = self.sample.interval
                logger.debug(
                    "Adjusting interval {} with timeMultiple {}, new interval: {}".format(
                        self.sample.interval, self.sample.timeMultiple, self.interval
                    )
                )
        logger.info(
            "Start '%s' generatorWorkers for sample '%s'"
            % (self.sample.config.generatorWorkers, self.sample.name)
        )

    def predict_event_size(self):
        try:
            self.sample.loadSample()
            logger.debug("File sample loaded successfully.")
        except TypeError:
            logger.debug("Error loading sample file for sample '%s'" % self.sample.name)
            return
        total_len = sum([len(e["_raw"]) for e in self.sample.sampleDict])
        sample_count = len(self.sample.sampleDict)
        if sample_count == 0:
            return 0
        else:
            return total_len / sample_count

    def run(self, futures_pool=None):
        """
        Simple wrapper method to determine whether we should be running inside python's profiler or not
        """
        if self.profiler:
            import cProfile

            globals()["threadrun"] = self.real_run
            cProfile.runctx(
                "threadrun()",
                globals(),
                locals(),
                "eventgen_timer_%s" % self.sample.name,
            )
        else:
            self.real_run()

    def real_run(self):
        """
        Worker function of the Timer class.  Determine whether a plugin is queueable, and either
        place an item in the generator queue for that plugin or call the plugin's gen method directly.
        """
        if self.sample.delay > 0:
            logger.info("Sample set to delay %s, sleeping." % self.sample.delay)
            time.sleep(self.sample.delay)

        logger.debug("Timer creating plugin for '%s'" % self.sample.name)
        local_time = datetime.datetime.now()
        end = False
        raw_event_size = self.predict_event_size()
        if self.end:
            if int(self.end) == 0:
                logger.info(
                    "End = 0, no events will be generated for sample '%s'"
                    % self.sample.name
                )
                end = True
            elif int(self.end) == -1:
                logger.info(
                    "End is set to -1. Will be running without stopping for sample %s"
                    % self.sample.name
                )
        while not end:
            try:
                # Need to be able to stop threads by the main thread or this thread. self.config will stop all threads
                # referenced in the config object, while, self.stopping will only stop this one.
                if self.config.stopping or self.stopping:
                    end = True
                self.rater.update_options(
                    config=self.config,
                    sample=self.sample,
                    generatorQueue=self.generatorQueue,
                    outputQueue=self.outputQueue,
                    outputPlugin=self.outputPlugin,
                    generatorPlugin=self.generatorPlugin,
                )
                count = self.rater.rate()
                # First run of the generator, see if we have any backfill work to do.
                if self.countdown <= 0:
                    if self.sample.backfill and not self.sample.backfilldone:
                        self.backrater.update_options(
                            config=self.config,
                            sample=self.sample,
                            generatorQueue=self.generatorQueue,
                            outputQueue=self.outputQueue,
                            outputPlugin=self.outputPlugin,
                            generatorPlugin=self.generatorPlugin,
                            samplerater=self.rater,
                        )
                        self.backrater.queue_it(count)
                    else:
                        if self.sample.generator == "perdayvolumegenerator":
                            self.perdayrater.update_options(
                                config=self.config,
                                sample=self.sample,
                                generatorQueue=self.generatorQueue,
                                outputQueue=self.outputQueue,
                                outputPlugin=self.outputPlugin,
                                generatorPlugin=self.generatorPlugin,
                                samplerater=self.rater,
                                raweventsize=raw_event_size,
                            )
                            self.perdayrater.rate()
                        self.rater.queue_it(count)
                    self.countdown = self.interval
                    self.executions += 1

            except Exception as e:
                logger.exception(str(e))
                if self.stopping:
                    end = True
                pass

            # Sleep until we're supposed to wake up and generate more events
            if self.countdown == 0:
                self.countdown = self.interval

            # 8/20/15 CS Adding support for ending generation at a certain time

            if self.end:
                if int(self.end) == -1:
                    time.sleep(self.time)
                    self.countdown -= self.time
                    continue
                # 3/16/16 CS Adding support for ending on a number of executions instead of time
                # Should be fine with storing state in this sample object since each sample has it's own unique
                # timer thread
                if not self.endts:
                    if self.executions >= int(self.end):
                        logger.info(
                            "End executions %d reached, ending generation of sample '%s'"
                            % (int(self.end), self.sample.name)
                        )
                        self.stopping = True
                        end = True
                elif local_time >= self.endts:
                    logger.info(
                        "End Time '%s' reached, ending generation of sample '%s'"
                        % (self.sample.endts, self.sample.name)
                    )
                    self.stopping = True
                    end = True

            time.sleep(self.time)
            self.countdown -= self.time
