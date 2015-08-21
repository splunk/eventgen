# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from outputplugin import OutputPlugin
import sys

class StdOutOutputPlugin(OutputPlugin):
	name = 'stdout'
	MAXQUEUELENGTH = 10

	def __init__(self, sample):
		OutputPlugin.__init__(self, sample)

	def flush(self, q):
		for x in q:
			print x['_raw'].rstrip()

def load():
    """Returns an instance of the plugin"""
    return StdOutOutputPlugin