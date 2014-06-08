from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque

class OutputPlugin:
	name = 'OutputPlugin'
	
	def __init__(self, sample):
		self._app = sample.app
		self._sample = sample
		self._outputMode = sample.outputMode
		
		# Logger already setup by config, just get an instance
		logger = logging.getLogger('eventgen')
		from eventgenconfig import EventgenAdapter
		adapter = EventgenAdapter(logger, {'module': 'OutputPlugin', 'sample': sample.name})
		self.logger = adapter

		from eventgenconfig import Config
		globals()['c'] = Config()

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

def load():
	return OutputPlugin