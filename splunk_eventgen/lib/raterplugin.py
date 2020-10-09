from __future__ import division

import datetime
import random
from queue import Full

from splunk_eventgen.lib.logging_config import logger


class RaterPlugin(object):
    name = "RaterPlugin"
    stopping = False

    def __init__(self, sample):
        self.sample = sample
        self.config = None
        self.generatorQueue = None
        self.outputQueue = None
        self.outputPlugin = None
        self.generatorPlugin = None
        self.replayLock = None
        self.executions = 0

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        # temp = dict([(key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def update_options(self, **kwargs):
        allowed_attrs = [attr for attr in dir(self) if not attr.startswith("__")]
        for key in kwargs:
            if kwargs[key] and key in allowed_attrs:
                self.__dict__.update({key: kwargs[key]})

    def adjust_rate_factor(self):
        # 5/8/12 CS We've requested not the whole file, so we should adjust count based on
        # hourOfDay, dayOfWeek and randomizeCount configs
        rateFactor = 1.0
        if self.sample.randomizeCount:
            try:
                logger.debug(
                    "randomizeCount for sample '%s' in app '%s' is %s"
                    % (self.sample.name, self.sample.app, self.sample.randomizeCount)
                )
                # If we say we're going to be 20% variable, then that means we
                # can be .1% high or .1% low.  Math below does that.
                randBound = round(self.sample.randomizeCount * 1000, 0)
                rand = random.randint(0, randBound)
                randFactor = 1 + ((-((randBound / 2) - rand)) / 1000)
                logger.debug(
                    "randFactor for sample '%s' in app '%s' is %s"
                    % (self.sample.name, self.sample.app, randFactor)
                )
                rateFactor *= randFactor
            except:
                import traceback

                stack = traceback.format_exc()
                logger.error(
                    "Randomize count failed for sample '%s'.  Stacktrace %s"
                    % (self.sample.name, stack)
                )
        if type(self.sample.hourOfDayRate) == dict:
            try:
                rate = self.sample.hourOfDayRate[str(self.sample.now().hour)]
                logger.debug(
                    "hourOfDayRate for sample '%s' in app '%s' is %s"
                    % (self.sample.name, self.sample.app, rate)
                )
                rateFactor *= rate
            except KeyError:
                import traceback

                stack = traceback.format_exc()
                logger.error(
                    "Hour of day rate failed for sample '%s'.  Stacktrace %s"
                    % (self.sample.name, stack)
                )
        if type(self.sample.dayOfWeekRate) == dict:
            try:
                weekday = datetime.date.weekday(self.sample.now())
                if weekday == 6:
                    weekday = 0
                else:
                    weekday += 1
                rate = self.sample.dayOfWeekRate[str(weekday)]
                logger.debug(
                    "dayOfWeekRate for sample '%s' in app '%s' is %s"
                    % (self.sample.name, self.sample.app, rate)
                )
                rateFactor *= rate
            except KeyError:
                import traceback

                stack = traceback.format_exc()
                logger.error(
                    "Hour of day rate failed for sample '%s'.  Stacktrace %s"
                    % (self.sample.name, stack)
                )
        if type(self.sample.minuteOfHourRate) == dict:
            try:
                rate = self.sample.minuteOfHourRate[str(self.sample.now().minute)]
                logger.debug(
                    "minuteOfHourRate for sample '%s' in app '%s' is %s"
                    % (self.sample.name, self.sample.app, rate)
                )
                rateFactor *= rate
            except KeyError:
                import traceback

                stack = traceback.format_exc()
                logger.error(
                    "Minute of hour rate failed for sample '%s'.  Stacktrace %s"
                    % (self.sample.name, stack)
                )
        if type(self.sample.dayOfMonthRate) == dict:
            try:
                rate = self.sample.dayOfMonthRate[str(self.sample.now().day)]
                logger.debug(
                    "dayOfMonthRate for sample '%s' in app '%s' is %s"
                    % (self.sample.name, self.sample.app, rate)
                )
                rateFactor *= rate
            except KeyError:
                import traceback

                stack = traceback.format_exc()
                logger.error(
                    "Day of Month rate for sample '%s' failed.  Stacktrace %s"
                    % (self.sample.name, stack)
                )
        if type(self.sample.monthOfYearRate) == dict:
            try:
                rate = self.sample.monthOfYearRate[str(self.sample.now().month)]
                logger.debug(
                    "monthOfYearRate for sample '%s' in app '%s' is %s"
                    % (self.sample.name, self.sample.app, rate)
                )
                rateFactor *= rate
            except KeyError:
                import traceback

                stack = traceback.format_exc()
                logger.error(
                    "Month Of Year rate failed for sample '%s'.  Stacktrace %s"
                    % (self.sample.name, stack)
                )
        return rateFactor

    def single_queue_it(self, count):
        """
        This method is used for specifying how to queue your rater plugin based on single process
        :param count:
        :return:
        """
        et = self.sample.earliestTime()
        lt = self.sample.latestTime()
        if count < 1 and count != -1:
            logger.info(
                "There is no data to be generated in worker {0} because the count is {1}.".format(
                    self.sample.config.generatorWorkers, count
                )
            )
        else:
            genPlugin = self.generatorPlugin(sample=self.sample)
            # Adjust queue for threading mode
            genPlugin.updateCounts(count=count, start_time=et, end_time=lt)
            genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
            try:
                logger.info(
                    (
                        "Put {0} MB of events in queue for sample '{1}'"
                        + "with et '{2}' and lt '{3}'"
                    ).format(
                        round((count / 1024.0 / 1024), 4), self.sample.name, et, lt
                    )
                )
                if self.sample.generator == "replay":
                    # lock on to replay mode, this will keep the timer knowing when to continue cycles since
                    # replay mode has a dynamic replay time and interval doesn't mean the same thing.
                    if (
                        hasattr(self.config, "outputCounter")
                        and self.config.outputCounter
                    ):
                        from splunk_eventgen.lib.outputcounter import OutputCounter

                        output_counter = OutputCounter()
                    elif hasattr(self.config, "outputCounter"):
                        output_counter = self.config.outputCounter
                    genPlugin.run(output_counter=output_counter)
                else:
                    self.generatorQueue.put(genPlugin)
            except Full:
                logger.warning("Generator Queue Full. Skipping current generation.")

    def multi_queue_it(self, count):
        """
        This method is used for specifying how to queue your rater plugin based on multi-process
        by default this method will just call the single_queue_it.
        :param count:
        :return:
        """
        self.single_queue_it(count)

    def queue_it(self, count):
        if self.sample.splitSample > 0:
            self.multi_queue_it(count)
        else:
            self.single_queue_it(count)

    def rate(self):
        self.sample.count = int(self.sample.count)
        # Let generators handle infinite count for themselves
        if self.sample.count == -1 and self.sample.generator == "default":
            if not self.sample.sampleDict:
                logger.error(
                    "No sample found for default generator, cannot generate events"
                )
            self.sample.count = len(self.sample.sampleDict)
        count = self.sample.count
        rateFactor = self.adjust_rate_factor()
        ret = int(round(count * rateFactor, 0))
        if rateFactor != 1.0:
            logger.debug(
                "Original count: %s Rated count: %s Rate factor: %s"
                % (count, ret, rateFactor)
            )
        return ret


def load():
    return RaterPlugin
