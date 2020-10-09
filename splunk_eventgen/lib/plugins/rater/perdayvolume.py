from queue import Full

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.plugins.rater.config import ConfigRater


class PerDayVolume(ConfigRater):
    name = "PerDayVolumeRater"
    stopping = False

    def __init__(self, sample):
        super(PerDayVolume, self).__init__(sample)
        # Logger already setup by config, just get an instance
        logger.debug(
            "Starting PerDayVolumeRater for %s" % sample.name
            if sample is not None
            else "None"
        )
        self.previous_count_left = 0
        self.raweventsize = 0

    def queue_it(self, count):
        count = count + self.previous_count_left
        if 0 < count < self.raweventsize:
            logger.info(
                "current interval size is {}, which is smaller than a raw event size {}.".format(
                    count, self.raweventsize
                )
                + "Wait for the next turn."
            )
            self.update_options(previous_count_left=count)
        else:
            self.update_options(previous_count_left=0)
        et = self.sample.earliestTime()
        lt = self.sample.latestTime()
        # self.generatorPlugin is only an instance, now we need a real plugin. Make a copy of
        # of the sample in case another generator corrupts it.
        genPlugin = self.generatorPlugin(sample=self.sample)
        # Adjust queue for threading mode
        genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
        genPlugin.updateCounts(count=count, start_time=et, end_time=lt)
        try:
            self.generatorQueue.put(genPlugin)
        except Full:
            logger.warning("Generator Queue Full. Skipping current generation.")

    def rate(self):
        perdayvolume = float(self.sample.perDayVolume)
        # Convert perdayvolume to bytes from GB
        perdayvolume = perdayvolume * 1024 * 1024 * 1024
        interval = self.sample.interval
        if self.sample.interval == 0:
            logger.debug("Running perDayVolume as if for 24hr period.")
            interval = 86400
        logger.debug(
            "Current perDayVolume: %f,  Sample interval: %s" % (perdayvolume, interval)
        )
        intervalsperday = 86400 / interval
        perintervalvolume = perdayvolume / intervalsperday
        count = self.sample.count
        rateFactor = self.adjust_rate_factor()
        logger.debug(
            "Size per interval: %s, rate factor to adjust by: %s"
            % (perintervalvolume, rateFactor)
        )
        ret = int(round(perintervalvolume * rateFactor, 0))
        if rateFactor != 1.0:
            logger.debug(
                "Original count: %s Rated count: %s Rate factor: %s"
                % (count, ret, rateFactor)
            )
        logger.debug(
            "Finished rating, interval: {0}s, generation rate: {1} MB/interval".format(
                interval, round((ret / 1024 / 1024), 4)
            )
        )
        return ret


def load():
    return PerDayVolume
