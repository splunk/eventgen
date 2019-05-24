from raterplugin import RaterPlugin

class ConfigRater(RaterPlugin):
    name = 'ConfigRater'
    stopping = False

    def __init__(self, sample):
        super(ConfigRater, self).__init__(sample)
        self._setup_logging()

def load():
    return ConfigRater
