# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from plugin import OutputPlugin

class ModInputOutputPlugin(OutputPlugin):
    name = 'modinput'
    MAXQUEUELENGTH = 10

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

    def flush(self, q):
        out = '<stream>\n'
        if len(q) > 0:
            m = q.popleft()
            while m:
                out += '  <event>\n'
                out += '    <index>%s</index>' % m['index']
                out += '    <source>%s</source>' % m['source']
                out += '    <sourcetype>%s</sourcetype>' % m['sourcetype']
                out += '    <host>%s</host>' % m['host']
                out += '    <data>%s</data>' % m['_raw']
                out += '  </event>'

                try:
                    m = q.popleft()
                except IndexError:
                    m = False
        
        out += '</stream>\n'
        print out

def load():
    """Returns an instance of the plugin"""
    return ModInputOutputPlugin