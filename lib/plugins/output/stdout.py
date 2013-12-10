# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from plugin import OutputPlugin

class StdOutOutputPlugin(OutputPlugin):
	name = 'stdout'
	MAXQUEUELENGTH = 10

	def __init__(self, sample):
		OutputPlugin.__init__(self, sample)

	def flush(self, q):
		if len(q) > 0:
			m = q.popleft()
			while m:
			    print m['_raw'].rstrip()
			    try:
			        m = q.popleft()
			    except IndexError:
			        m = False

def load():
    """Returns an instance of the plugin"""
    return StdOutOutputPlugin