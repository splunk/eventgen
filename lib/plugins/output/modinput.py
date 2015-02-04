# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from outputplugin import OutputPlugin
import datetime, time
import sys
from xml.sax.saxutils import escape

class ModInputOutputPlugin(OutputPlugin):
    name = 'modinput'
    MAXQUEUELENGTH = 10

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

    def flush(self, q):
        out = ""
        if len(q) > 0:
            m = q.popleft()
            while m:
                try:
                    out += '  <event>\n'
                    out += '    <time>%s</time>\n' % m['_time']
                    out += '    <index>%s</index>\n' % m['index']
                    out += '    <source>%s</source>\n' % m['source']
                    out += '    <sourcetype>%s</sourcetype>\n' % m['sourcetype']
                    out += '    <host>%s</host>\n' % m['host']
                    out += '    <data>%s</data>\n' % escape(m['_raw'])
                    out += '  </event>\n'
                except KeyError:
                    pass

                try:
                    m = q.popleft()
                except IndexError:
                    m = False
        
        # out += '</stream>'
        print out
        sys.stdout.flush()

def load():
    """Returns an instance of the plugin"""
    return ModInputOutputPlugin