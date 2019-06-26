from __future__ import division

import logging

from outputplugin import OutputPlugin


class DevNullOutputPlugin(OutputPlugin):
    name = 'devnull'
    MAXQUEUELENGTH = 1000
    useOutputQueue = True

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)
        self.firsttime = True

    def flush(self, q):
        if self.firsttime:
            self.f = open('/dev/null', 'w')
            self.firsttime = False
        buf = '\n'.join(x['_raw'].rstrip() for x in q)
        self.f.write(buf)

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen_devnullout')


def load():
    """Returns an instance of the plugin"""
    return DevNullOutputPlugin
