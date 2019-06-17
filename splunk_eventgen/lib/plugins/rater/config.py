from raterplugin import RaterPlugin
from Queue import Full

class ConfigRater(RaterPlugin):
    name = 'ConfigRater'
    stopping = False

    def __init__(self, sample):
        super(ConfigRater, self).__init__(sample)
        self._setup_logging()

    def queue_it(self, count):
        et = self.sample.earliestTime()
        lt = self.sample.latestTime()
        if count < 1 and count != -1:
            self.logger.info(
                "There is no data to be generated in worker {0} because the count is {1}.".format(
                    self.sample.config.generatorWorkers, count))
        else:
            genPlugin = self.generatorPlugin(sample=self.sample)
            # Adjust queue for threading mode
            genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
            genPlugin.updateCounts(count=count, start_time=et, end_time=lt)
            try:
                self.generatorQueue.put(genPlugin)
                self.logger.info(("Put {0} MB of events in queue for sample '{1}'" +
                                  "with et '{2}' and lt '{3}'").format(
                                      round((count / 1024.0 / 1024), 4),
                                      self.sample.name, et, lt))
            except Full:
                self.logger.warning("Generator Queue Full. Skipping current generation.")


def load():
    return ConfigRater
