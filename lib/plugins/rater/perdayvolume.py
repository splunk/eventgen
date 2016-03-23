from __future__ import division
from config import ConfigRater
import logging
import logging.handlers
import datetime
import random

class PerDayVolume(ConfigRater):
    name = 'PerDayVolumeRater'
    stopping = False

    def __init__(self, sample):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'PerDayVolume', 'sample': sample.name})
        self.logger = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

        self.logger.debug('Starting PerDayVolumeRater for %s' % sample.name if sample is not None else "None")

        self._sample = sample

    def rate(self):
        perdayvolume = float(self._sample.perDayVolume)
        # Convert perdayvolume to bytes from GB
        perdayvolume = perdayvolume * 1024 * 1024 * 1024
        interval = self._sample.interval
        if self._sample.interval == 0:
            self.logger.debug('Running perDayVolume as if for 24hr period.')
            interval = 86400
        self.logger.debug('Current perDayVolume: %f,  Sample interval: %s' % (perdayvolume, interval))
        intervalsperday = (86400 / interval)
        perintervalvolume = (perdayvolume / intervalsperday)
        count = self._sample.count


        # 5/8/12 CS We've requested not the whole file, so we should adjust count based on
        # hourOfDay, dayOfWeek and randomizeCount configs
        rateFactor = 1.0
        if self._sample.randomizeCount != 0 and self._sample.randomizeCount != None:
            try:
                self.logger.debugv("randomizeCount for sample '%s' in app '%s' is %s" \
                                % (self._sample.name, self._sample.app, self._sample.randomizeCount))
                # If we say we're going to be 20% variable, then that means we
                # can be .1% high or .1% low.  Math below does that.
                randBound = round(self._sample.randomizeCount * 1000, 0)
                rand = random.randint(0, randBound)
                randFactor = 1+((-((randBound / 2) - rand)) / 1000)
                self.logger.debug("randFactor for sample '%s' in app '%s' is %s" \
                                % (self._sample.name, self._sample.app, randFactor))
                rateFactor *= randFactor
            except:
                import traceback
                stack =  traceback.format_exc()
                self.logger.error("Randomize count failed for sample '%s'.  Stacktrace %s" % (self._sample.name, stack))
        if type(self._sample.hourOfDayRate) == dict:
            try:
                rate = self._sample.hourOfDayRate[str(self._sample.now().hour)]
                self.logger.debugv("hourOfDayRate for sample '%s' in app '%s' is %s" % (self._sample.name, self._sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack =  traceback.format_exc()
                self.logger.error("Hour of day rate failed for sample '%s'.  Stacktrace %s" % (self._sample.name, stack))
        if type(self._sample.dayOfWeekRate) == dict:
            try:
                weekday = datetime.date.weekday(self._sample.now())
                if weekday == 6:
                    weekday = 0
                else:
                    weekday += 1
                rate = self._sample.dayOfWeekRate[str(weekday)]
                self.logger.debugv("dayOfWeekRate for sample '%s' in app '%s' is %s" % (self._sample.name, self._sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack =  traceback.format_exc()
                self.logger.error("Hour of day rate failed for sample '%s'.  Stacktrace %s" % (self._sample.name, stack))
        if type(self._sample.minuteOfHourRate) == dict:
            try:
                rate = self._sample.minuteOfHourRate[str(self._sample.now().minute)]
                self.logger.debugv("minuteOfHourRate for sample '%s' in app '%s' is %s" % (self._sample.name, self._sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack =  traceback.format_exc()
                self.logger.error("Minute of hour rate failed for sample '%s'.  Stacktrace %s" % (self._sample.name, stack))
        if type(self._sample.dayOfMonthRate) == dict:
            try:
                rate = self._sample.dayOfMonthRate[str(self._sample.now().day)]
                self.logger.debugv("dayOfMonthRate for sample '%s' in app '%s' is %s" % (self._sample.name, self._sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack =  traceback.format_exc()
                self.logger.error("Day of Month rate for sample '%s' failed.  Stacktrace %s" % (self._sample.name, stack))
        if type(self._sample.monthOfYearRate) == dict:
            try:
                rate = self._sample.monthOfYearRate[str(self._sample.now().month)]
                self.logger.debugv("monthOfYearRate for sample '%s' in app '%s' is %s" % (self._sample.name, self._sample.app, rate))
                rateFactor *= rate
            except KeyError:
                import traceback
                stack =  traceback.format_exc()
                self.logger.error("Month Of Year rate failed for sample '%s'.  Stacktrace %s" % (self._sample.name, stack))
        self.logger.debug("Size per interval: %s, rate factor to adjust by: %s" % (perintervalvolume, rateFactor))
        ret = int(round(perintervalvolume * rateFactor, 0))
        if rateFactor != 1.0:
            self.logger.debug("Original count: %s Rated count: %s Rate factor: %s" % (count, ret, rateFactor))
        self.logger.info("Finished rating, returning interval rate: %s" % ret)
        return ret

def load():
    return PerDayVolume