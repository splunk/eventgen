# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from outputplugin import OutputPlugin
import sys
from xml.sax.saxutils import escape
import logging

class ModInputOutputPlugin(OutputPlugin):
    name = 'modinput'
    MAXQUEUELENGTH = 10
    useOutputQueue = False

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

    def flush(self, q):
        out = ""
        if len(q) > 0:
            m = q.pop(0)
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
                    m = q.pop(0)
                except IndexError:
                    m = False

        print out
        sys.stdout.flush()

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')

def load():
    """Returns an instance of the plugin"""
    return ModInputOutputPlugin