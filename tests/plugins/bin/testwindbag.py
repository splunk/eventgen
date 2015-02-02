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
        if self._sample.out == None:
            self.logger.info("Setting up Output class for sample '%s' in app '%s'" % (self._sample.name, self._sample.app))
            self._sample.out = Output(self._sample)
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