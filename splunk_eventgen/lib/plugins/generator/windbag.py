from __future__ import division
from generatorplugin import GeneratorPlugin
import logging
import datetime, time
from datetime import timedelta

class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def gen(self, count, earliest, latest, samplename=None):
        # print type(latest - earliest).total_seconds()
        time_interval = timedelta.total_seconds((latest - earliest)) / count
        for i in xrange(count):
            current_time_object = earliest + datetime.timedelta(0, time_interval*(i+1))
            msg = '{0} -0700 WINDBAG Event {1} of {2}'.format(current_time_object, (i+1), count)
            self._out.send(msg)
        return 0


def load():
    return WindbagGenerator
