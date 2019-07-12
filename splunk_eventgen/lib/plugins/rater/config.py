from raterplugin import RaterPlugin
from logging_config import logger

class ConfigRater(RaterPlugin):
    name = 'ConfigRater'
    stopping = False

    def __init__(self, sample):
        super(ConfigRater, self).__init__(sample)

    def single_queue_it(self, count):
        super(ConfigRater, self).single_queue_it(count)


    def multi_queue_it(self, count):
        logger.info("Entering multi-processing division of sample")
        pass

def load():
    return ConfigRater
