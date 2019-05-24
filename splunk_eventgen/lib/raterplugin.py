from __future__ import division

import datetime
import logging
import logging.handlers
import random


class RaterPlugin(object):
    name = 'RaterPlugin'
    stopping = False

    def __init__(self, sample):
        self._setup_logging()
        self.sample = sample
        self.config = None
        self.generatorQueue = None
        self.outputQueue = None
        self.outputPlugin = None
        self.generatorPlugin = None

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        # temp = dict([(key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

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

    def update_options(self, **kwargs):
        allowed_attrs = [attr for attr in dir(self) if not attr.startswith('__')]
        for key in kwargs:
            if kwargs[key] and key in allowed_attrs:
                self.__dict__.update({key: kwargs[key]})

    def adjust_rate_factor(self):
        # 5/8/12 CS We've requested not the whole file, so we should adjust count based on
        # hourOfDay, dayOfWeek and randomizeCount configs
        rateFactor = 1.0
        if self.sample.randomizeCount:
            try:
                self.logger.debug("randomizeCount for sample '%s' in app '%s' is %s" %
                                  (self.sample.name, self.sample.app, self.sample.randomizeCount))
                # If we say we're going to be 20% variable, then that means we
                # can be .1% high or .1% low.  Math below does that.
                randBound = round(self.sample.randomizeCount * 1000, 0)
                rand = random.randint(0, randBound)
                randFactor = 1 + ((-((randBound / 2) - rand)) / 1000)
                self.logger.debug(
                    "randFactor for sample '%s' in app '%s' is %s" % (self.sample.name, self.sample.app, randFactor))
                rateFactor *= randFactor
            except:
                import traceback
                stack = traceback.format_exc()
                self.logger.error("Randomize count failed for sample '%s'.  Stacktrace %s" % (self.sample.name, stack))
        if type(self.sample.hourOfDayRate) == dict:
            try:
                rate = self.sample.hourOfDayRate[str(self.sample.now().hour)]
                self.logger.debug(
                    "hourOfDayRate for sample '%s' in app '%s' is %s" % (self.sample.name, self.sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack = traceback.format_exc()
                self.logger.error(
                    "Hour of day rate failed for sample '%s'.  Stacktrace %s" % (self.sample.name, stack))
        if type(self.sample.dayOfWeekRate) == dict:
            try:
                weekday = datetime.date.weekday(self.sample.now())
                if weekday == 6:
                    weekday = 0
                else:
                    weekday += 1
                rate = self.sample.dayOfWeekRate[str(weekday)]
                self.logger.debug(
                    "dayOfWeekRate for sample '%s' in app '%s' is %s" % (self.sample.name, self.sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack = traceback.format_exc()
                self.logger.error(
                    "Hour of day rate failed for sample '%s'.  Stacktrace %s" % (self.sample.name, stack))
        if type(self.sample.minuteOfHourRate) == dict:
            try:
                rate = self.sample.minuteOfHourRate[str(self.sample.now().minute)]
                self.logger.debug(
                    "minuteOfHourRate for sample '%s' in app '%s' is %s" % (self.sample.name, self.sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack = traceback.format_exc()
                self.logger.error(
                    "Minute of hour rate failed for sample '%s'.  Stacktrace %s" % (self.sample.name, stack))
        if type(self.sample.dayOfMonthRate) == dict:
            try:
                rate = self.sample.dayOfMonthRate[str(self.sample.now().day)]
                self.logger.debug(
                    "dayOfMonthRate for sample '%s' in app '%s' is %s" % (self.sample.name, self.sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack = traceback.format_exc()
                self.logger.error(
                    "Day of Month rate for sample '%s' failed.  Stacktrace %s" % (self.sample.name, stack))
        if type(self.sample.monthOfYearRate) == dict:
            try:
                rate = self.sample.monthOfYearRate[str(self.sample.now().month)]
                self.logger.debug(
                    "monthOfYearRate for sample '%s' in app '%s' is %s" % (self.sample.name, self.sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack = traceback.format_exc()
                self.logger.error(
                    "Month Of Year rate failed for sample '%s'.  Stacktrace %s" % (self.sample.name, stack))
        return rateFactor

    def rate(self):
        self.sample.count = int(self.sample.count)
        # Let generators handle infinite count for themselves
        if self.sample.count == -1 and self.sample.generator == 'default':
            if not self.sample.sampleDict:
                self.logger.error('No sample found for default generator, cannot generate events')
            self.sample.count = len(self.sample.sampleDict)
        count = self.sample.count
        rateFactor = self.adjust_rate_factor()
        ret = int(round(count * rateFactor, 0))
        if rateFactor != 1.0:
            self.logger.debug("Original count: %s Rated count: %s Rate factor: %s" % (count, ret, rateFactor))
        return ret


def load():
    return RaterPlugin
