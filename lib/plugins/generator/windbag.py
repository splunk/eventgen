from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import itertools
from collections import deque

class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, count, earliest, latest):
        # l = range(count)
        # for i in xrange(count):
        #     # self._sample.timestamp = latest
        #     # self._sample.out.send("%s WINDBAG Event %d of %d" % (datetime.datetime.strftime(latest, "%Y-%m-%d %H:%M:%S"), i+1, count))
        #     self._sample.out.send('2014-01-05 23:07:08 WINDBAG Event 1 of 100000')
        # i = itertools.imap(lambda x: self._sample.out.send('2014-01-05 23:07:08 WINDBAG Event 1 of 100000'), l)
        # filter(lambda x: x, i)
        # l = [ ]
        # for i in xrange(count):
        #     # l.append({ '_raw': "%s WINDBAG Event %d of %d" % (datetime.datetime.strftime(latest, "%Y-%m-%d %H:%M:%S"), i+1, count),
        #     # l.append({'_raw': '2014-01-05 23:07:08 WINDBAG Event 1 of 100000', 
        #     #             'index': self._sample.index,
        #     #             'host': self._sample.host,
        #     #             'source': self._sample.source,
        #     #             'sourcetype': self._sample.sourcetype,
        #     #             '_time': latest})
        #     l.append({'_raw': '2014-01-05 23:07:08 WINDBAG Event 1 of 100000'})
        l = [ {'_raw': '2014-01-05 23:07:08 WINDBAG Event 1 of 100000'} for i in xrange(count) ]
        # l = [ {'_raw': '2014-01-05 23:07:08 WINDBAG Event 1 of 100000', 
        #                 'index': self._sample.index,
        #                 'host': self._sample.host,
        #                 'source': self._sample.source,
        #                 'sourcetype': self._sample.sourcetype,
        #                 '_time': time.mktime(latest.timetuple()) } for i in xrange(count) ]
        # l = [ {'_raw': '"111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111"'} for i in xrange(count) ]
        # l = [ '2014-01-05 23:07:08 WINDBAG Event 1 of 100000' for i in xrange(count) ]

        self._sample.out.bulksend(l)
        return 0


def load():
    return WindbagGenerator