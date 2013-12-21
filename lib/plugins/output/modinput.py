# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from plugin import OutputPlugin
import datetime

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
                out += '    <time>%s</time>\n' % datetime.datetime.strftime(m['_time'], '%s')
                out += '    <index>%s</index>\n' % m['index']
                out += '    <source>%s</source>\n' % m['source']
                out += '    <sourcetype>%s</sourcetype>\n' % m['sourcetype']
                out += '    <host>%s</host>\n' % m['host']
                out += '    <data>%s</data>\n' % m['_raw']
                out += '  </event>\n'

                try:
                    m = q.popleft()
                except IndexError:
                    m = False
        
        out += '</stream>'
        print out

def load():
    """Returns an instance of the plugin"""
    return ModInputOutputPlugin