import datetime
from datetime import timedelta

from splunk_eventgen.lib.generatorplugin import GeneratorPlugin
from splunk_eventgen.lib.logging_config import logger


class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def gen(self, count, earliest, latest, samplename=None):
        if count < 0:
            logger.warning(
                "Sample size not found for count=-1 and generator=windbag, defaulting to count=60"
            )
            count = 60
        time_interval = timedelta.total_seconds((latest - earliest)) / count
        for i in range(count):
            current_time_object = earliest + datetime.timedelta(
                0, time_interval * (i + 1)
            )
            msg = "{0} -0700 WINDBAG Event {1} of {2}".format(
                current_time_object, (i + 1), count
            )
            self._out.send(msg)
        return 0


def load():
    return WindbagGenerator
