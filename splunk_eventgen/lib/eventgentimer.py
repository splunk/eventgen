import copy
import logging
import time
from Queue import Full

from timeparser import timeParserTimeMath


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
        self.executions = 0
        self.interval = getattr(self.sample, "interval", config.interval)
        # enable the logger
        self._setup_logging()
        self.logger.debug('Initializing timer for %s' % sample.name if sample is not None else "None")
        # load plugins
        if self.sample is not None:
            rater_class = self.config.getPlugin('rater.' + self.sample.rater, self.sample)
            self.rater = rater_class(self.sample)
            self.generatorPlugin = self.config.getPlugin('generator.' + self.sample.generator, self.sample)
            self.outputPlugin = self.config.getPlugin('output.' + self.sample.outputMode, self.sample)
            if self.sample.timeMultiple < 0:
                self.logger.error("Invalid setting for timeMultiple: {}, value should be positive".format(
                    self.sample.timeMultiple))
            elif self.sample.timeMultiple != 1:
                self.interval = self.sample.interval * self.sample.timeMultiple
                self.logger.debug("Adjusting interval {} with timeMultiple {}, new interval: {}".format(
                    self.sample.interval, self.sample.timeMultiple, self.interval))
        self.logger.info(
            "Start '%s' generatorWorkers for sample '%s'" % (self.sample.config.generatorWorkers, self.sample.name))

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

    def predict_event_size(self):
        try:
            self.sample.loadSample()
            self.logger.debug("File sample loaded successfully.")
        except TypeError:
            self.logger.error("Error loading sample file for sample '%s'" % self.sample.name)
            return
        return len(self.sample.sampleDict[0]['_raw'])

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

        end = False
        previous_count_left = 0
        raw_event_size = self.predict_event_size()
        if self.end:
            if int(self.end) == 0:
                self.logger.info("End = 0, no events will be generated for sample '%s'" % self.sample.name)
                end = True
            elif int(self.end) == -1:
                self.logger.info("End is set to -1. Will be running without stopping for sample %s" % self.sample.name)
        while not end:
            # Need to be able to stop threads by the main thread or this thread. self.config will stop all threads
            # referenced in the config object, while, self.stopping will only stop this one.
            if self.config.stopping or self.stopping:
                end = True
            count = self.rater.rate()
            # First run of the generator, see if we have any backfill work to do.
            if self.countdown <= 0:
                if self.sample.backfill and not self.sample.backfilldone:
                    realtime = self.sample.now(realnow=True)
                    if "-" in self.sample.backfill[0]:
                        mathsymbol = "-"
                    else:
                        mathsymbol = "+"
                    backfillnumber = ""
                    backfillletter = ""
                    for char in self.sample.backfill:
                        if char.isdigit():
                            backfillnumber += char
                        elif char != "-":
                            backfillletter += char
                    backfillearliest = timeParserTimeMath(plusminus=mathsymbol, num=backfillnumber, unit=backfillletter,
                                                          ret=realtime)
                    while backfillearliest < realtime:
                        if self.executions == int(self.end):
                            self.logger.info("End executions %d reached, ending generation of sample '%s'" % (int(
                                self.end), self.sample.name))
                            break
                        et = backfillearliest
                        lt = timeParserTimeMath(plusminus="+", num=self.interval, unit="s", ret=et)
                        genPlugin = self.generatorPlugin(sample=self.sample)
                        # need to make sure we set the queue right if we're using multiprocessing or thread modes
                        genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
                        genPlugin.updateCounts(count=count, start_time=et, end_time=lt)
                        try:
                            self.generatorQueue.put(genPlugin)
                            self.executions += 1
                        except Full:
                            self.logger.warning("Generator Queue Full. Skipping current generation.")
                        backfillearliest = lt
                        
                    self.sample.backfilldone = True
                else:
                    # 12/15/13 CS Moving the rating to a separate plugin architecture
                    # Save previous interval count left to avoid perdayvolumegenerator drop small tasks
                    if self.sample.generator == 'perdayvolumegenerator':
                        count = self.rater.rate() + previous_count_left
                        if 0 < count < raw_event_size:
                            self.logger.info("current interval size is {}, which is smaller than a raw event size {}.".
                                             format(count, raw_event_size) + "Wait for the next turn.")
                            previous_count_left = count
                            self.countdown = self.interval
                            self.executions += 1
                            continue
                        else:
                            previous_count_left = 0
                    else:
                        count = self.rater.rate()

                    et = self.sample.earliestTime()
                    lt = self.sample.latestTime()

                    try:
                        if count < 1 and count != -1:
                            self.logger.info(
                                "There is no data to be generated in worker {0} because the count is {1}.".format(
                                    self.sample.config.generatorWorkers, count))
                        else:
                            # Spawn workers at the beginning of job rather than wait for next interval
                            self.logger.info("Start '%d' generatorWorkers for sample '%s'" %
                                             (self.sample.config.generatorWorkers, self.sample.name))
                            for worker_id in range(self.config.generatorWorkers):
                                # self.generatorPlugin is only an instance, now we need a real plugin. Make a copy of
                                # of the sample in case another generator corrupts it.
                                copy_sample = copy.copy(self.sample)
                                copy_tokens = []
                                for token in self.sample.tokens:
                                    copy_tokens.append(token.deepcopy(self.sample))
                                copy_sample.tokens = copy_tokens
                                genPlugin = self.generatorPlugin(sample=copy_sample)
                                # Adjust queue for threading mode
                                genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
                                genPlugin.updateCounts(count=count, start_time=et, end_time=lt)

                                try:
                                    self.generatorQueue.put(genPlugin)
                                    self.executions += 1
                                    self.logger.info(("Worker# {0}: Put {1} MB of events in queue for sample '{2}'" +
                                                      "with et '{3}' and lt '{4}'").format(
                                                          worker_id, round((count / 1024.0 / 1024), 4),
                                                          self.sample.name, et, lt))
                                except Full:
                                    self.logger.warning("Generator Queue Full. Skipping current generation.")
                    except Exception as e:
                        self.logger.exception(e)
                        if self.stopping:
                            end = True
                        pass

                # Sleep until we're supposed to wake up and generate more events
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
                            self.logger.info("End executions %d reached, ending generation of sample '%s'" % (int(
                                self.end), self.sample.name))
                            self.stopping = True
                            end = True
                    elif lt >= self.endts:
                        self.logger.info("End Time '%s' reached, ending generation of sample '%s'" % (self.sample.endts,
                                                                                                      self.sample.name))
                        self.stopping = True
                        end = True

            else:
                time.sleep(self.time)
                self.countdown -= self.time
