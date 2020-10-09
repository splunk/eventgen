from queue import Full

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.raterplugin import RaterPlugin


class CountRater(RaterPlugin):
    name = "CountRater"
    stopping = False

    def __init__(self, sample):
        super(CountRater, self).__init__(sample)

    def single_queue_it(self, count, remaining_count=None):
        """
        This method is used for specifying how to queue your rater plugin based on single process
        :param count: Used to count number of events in a bundle
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
            genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
            genPlugin.updateCounts(count=count, start_time=et, end_time=lt)
            try:
                self.generatorQueue.put(genPlugin)
                logger.info(
                    (
                        "Put {0} MB of events in queue for sample '{1}'"
                        + "with et '{2}' and lt '{3}'"
                    ).format(
                        round((count / 1024.0 / 1024), 4), self.sample.name, et, lt
                    )
                )
            except Full:
                logger.warning("Generator Queue Full. Skipping current generation.")

    def multi_queue_it(self, count):
        logger.info("Entering multi-processing division of sample")
        numberOfWorkers = self.config.generatorWorkers
        # this is a redundant check, but will prevent some missed call to multi_queue without a valid setting
        if bool(self.sample.splitSample):
            # if split = 1, then they want to divide by number of generator workers, else use the splitSample
            if self.sample.splitSample == 1:
                targetWorkersToUse = numberOfWorkers
            else:
                targetWorkersToUse = self.sample.splitSample
        else:
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
    return CountRater
