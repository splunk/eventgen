from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
import threading
from Queue import Empty

class GeneratorWorker(threading.Thread):
    name = 'GeneratorWorker'
    stopping = False

    def __init__(self):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

        threading.Thread.__init__(self)

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def run(self):
        while not self.stopping:
            try:
                sample, count, earliest, latest = c.generatorQueue.get(block=True, timeout=1.0)
                plugin = c.getPlugin(sample.generator)(sample)
                plugin.gen(count, earliest, latest)
            except Empty:
                pass

    def stop(self):
        self.stopping = True

def load():
    return OutputWorker