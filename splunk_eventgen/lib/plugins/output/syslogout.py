from __future__ import division
from outputplugin import OutputPlugin
import logging, logging.handlers

class SyslogOutOutputPlugin(OutputPlugin):
    name = 'syslogout'
    MAXQUEUELENGTH = 10
    validSettings = [ 'syslogDestinationHost', 'syslogDestinationPort' ]
    defaultableSettings = [ 'syslogDestinationHost', 'syslogDestinationPort' ]
    intSettings = [ 'syslogDestinationPort' ]

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)
        self._syslogDestinationHost = sample.syslogDestinationHost if hasattr(sample, 'syslogDestinationHost') and sample.syslogDestinationHost else '127.0.0.1'
        self._syslogDestinationPort = sample.syslogDestinationPort if hasattr(sample, 'syslogDestinationPort') and sample.syslogDestinationPort else 1514

        self._l = logging.getLogger('syslog'+ sample.name)
        self._l.setLevel(logging.INFO)
        syslogHandler = logging.handlers.SysLogHandler(address=(self._syslogDestinationHost, int(self._syslogDestinationPort)))
        self._l.addHandler(syslogHandler)

    def flush(self, q):
        for x in q:
            self._l.info(x['_raw'].rstrip())

def load():
    """Returns an instance of the plugin"""
    return SyslogOutOutputPlugin
