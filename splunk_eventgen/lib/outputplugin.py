from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque

class OutputPlugin(object):
    name = 'OutputPlugin'

    def __init__(self, sample):
        self._app = sample.app
        self._sample = sample
        self._outputMode = sample.outputMode
        self.events = None

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'OutputPlugin', 'sample': self._sample.name})
        self.logger = adapter

        self.logger.debug("Starting OutputPlugin for sample '%s' with output '%s'" % (self._sample.name, self._sample.outputMode))

        self._queue = deque([])

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def save(obj):
        return (obj.__class__, obj.__dict__)

    def load(cls, attributes):
        obj = cls.__new__(cls)
        obj.__dict__.update(attributes)
        return obj

    def set_events(self, events):
        self.events = events

    def run(self):
        if self.events:
            self.flush(q=self.events)
        self.events = None


def load():
    return OutputPlugin