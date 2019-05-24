from __future__ import division
import datetime
from datetime import timedelta

from generatorplugin import GeneratorPlugin


class SplitCounterGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)
        self.start_count = 0

    def update_start_count(self, target):
        self.start_count = target

    def gen(self, count, earliest, latest, samplename=None):
        if count < 0:
            self.logger.warn('Sample size not found for count=-1 and generator=splitcounter, defaulting to count=60')
            count = 60
        time_interval = timedelta.total_seconds((latest - earliest)) / count
        max_count = count + self.start_count
        for i in xrange(count):
            current_count = i + self.start_count
            current_time_object = earliest + datetime.timedelta(0, time_interval * (i + 1))
            msg = '{0} -0700 SplitterCounter Event {1} of {2}'.format(current_time_object, (current_count + 1), max_count)
            self._out.send(msg)
        return 0


def load():
    return SplitCounterGenerator
