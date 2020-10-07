from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.raterplugin import RaterPlugin


class ConfigRater(RaterPlugin):
    name = "ConfigRater"
    stopping = False

    def __init__(self, sample):
        super(ConfigRater, self).__init__(sample)

    def single_queue_it(self, count):
        super(ConfigRater, self).single_queue_it(count)

    def multi_queue_it(self, count):
        logger.info("Entering multi-processing division of sample")
        numberOfWorkers = self.config.generatorWorkers
        logger.debug("Number of Workers: {0}".format(numberOfWorkers))
        # this is a redundant check, but will prevent some missed call to multi_queue without a valid setting
        if bool(self.sample.splitSample):
            # if split = 1, then they want to divide by number of generator workers, else use the splitSample
            if self.sample.splitSample == 1:
                logger.debug("SplitSample = 1, using all availible workers")
                targetWorkersToUse = numberOfWorkers
            else:
                logger.debug(
                    "SplitSample != 1, using {0} workers.".format(
                        self.sample.splitSample
                    )
                )
                targetWorkersToUse = self.sample.splitSample
        else:
            logger.debug(
                "SplitSample set to disable multithreading for just this sample."
            )
            self.single_queue_it()
        currentWorkerPrepCount = 0
        remainingCount = count
        targetLoopCount = int(count) / targetWorkersToUse
        while currentWorkerPrepCount < targetWorkersToUse:
            currentWorkerPrepCount = currentWorkerPrepCount + 1
            # check if this is the last loop, if so, add in the remainder count
            if currentWorkerPrepCount < targetWorkersToUse:
                remainingCount = count - targetLoopCount
            else:
                targetLoopCount = remainingCount
            self.single_queue_it(targetLoopCount)


def load():
    return ConfigRater
