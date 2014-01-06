from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime

class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, count, earliest, latest):
        # for i in xrange(count):
        #     self._sample.out.send("%s WINDBAG Event %d of %d" % (datetime.datetime.strftime(latest, "%Y-%m-%d %H:%M:%S"), i+1, count))
        l = [ ]
        for i in xrange(count):
            l.append({ '_raw': "%s WINDBAG Event %d of %d" % (datetime.datetime.strftime(latest, "%Y-%m-%d %H:%M:%S"), i+1, count),
                        'index': self._sample.index,
                        'host': self._sample.host,
                        'source': self._sample.source,
                        'sourcetype': self._sample.sourcetype,
                        '_time': latest})
        self._sample.out.bulksend(l)


def load():
    return WindbagGenerator