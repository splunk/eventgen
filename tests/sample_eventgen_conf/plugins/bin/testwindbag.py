from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import itertools
from collections import deque
from eventgenoutput import Output

class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'WindbagGenerator', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, count, earliest, latest, samplename=None):    
        l = [ {'_raw': '2014-01-05 23:07:08 WINDBAG Event 1 of 100000'} for i in xrange(count) ]

        self._out.bulksend(l)
        return 0


def load():
    return WindbagGenerator