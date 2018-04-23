from __future__ import division
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
        self._setup_logging()
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

    # loggers can't be pickled due to the lock object, remove them before we try to pickle anything.
    def __getstate__(self):
        temp = self.__dict__
        if getattr(self, 'logger', None):
            temp.pop('logger', None)
        return temp

    def __setstate__(self, d):
        self.__dict__ = d
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')

    def set_events(self, events):
        self.events = events

    def updateConfig(self, config):
        self.config = config

    def run(self):
        if self.events:
            self.flush(q=self.events)
        self.events = None


def load():
    return OutputPlugin