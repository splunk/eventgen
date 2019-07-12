from raterplugin import RaterPlugin

class ConfigRater(RaterPlugin):
    name = 'ConfigRater'
    stopping = False

    def __init__(self, sample):
        super(ConfigRater, self).__init__(sample)
        self._setup_logging()

    def single_queue_it(self, count):
        super(ConfigRater, self).single_queue_it(count)


    def multi_queue_it(self, count):
        pass

def load():
    return ConfigRater
