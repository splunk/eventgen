from __future__ import division
from generatorplugin import GeneratorPlugin
import logging

class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def gen(self, count, earliest, latest, samplename=None):
        eventlist = []
        for i in xrange(count):
            event = {'_raw': '2014-01-05 23:07:08 WINDBAG Event %d of %d' % ((i+1), count)}
            eventlist.append(event)
        self._out.bulksend(eventlist)
        return 0


def load():
    return WindbagGenerator
