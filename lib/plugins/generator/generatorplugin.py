from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
from eventgenoutput import Output

class GeneratorPlugin:
    def __init__(self, sample):
        self._sample = sample
        
        self._queue = deque([])

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

def load():
    return GeneratorPlugin