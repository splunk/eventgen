from __future__ import division
from outputplugin import OutputPlugin

class StdOutOutputPlugin(OutputPlugin):
    name = 'stdout'
    MAXQUEUELENGTH = 10

    def __init__(self, sample, config=None):
        OutputPlugin.__init__(self, sample)

    def flush(self, q):
        for x in q:
            print x['_raw'].rstrip()

def load():
    """Returns an instance of the plugin"""
    return StdOutOutputPlugin