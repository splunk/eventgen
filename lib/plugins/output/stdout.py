# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from outputplugin import OutputPlugin
import sys

class StdOutOutputPlugin(OutputPlugin):
	name = 'stdout'
	MAXQUEUELENGTH = 1000

	def __init__(self, sample):
		OutputPlugin.__init__(self, sample)

	def flush(self, q):
		# if len(q) > 0:
		# 	m = q.popleft()
		# 	while m:
		# 	    print m['_raw'].rstrip()
		# 	    try:
		# 	        m = q.popleft()
		# 	    except IndexError:
		# 	        m = False
		# for x in q:
		# 	print x['_raw'].rstrip()
		buf = ''
		for x in q:
			buf += x['_raw'].rstrip()+'\n'
		sys.stdout.write(buf)

def load():
    """Returns an instance of the plugin"""
    return StdOutOutputPlugin