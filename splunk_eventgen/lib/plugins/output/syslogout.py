from __future__ import division
from outputplugin import OutputPlugin
import logging, logging.handlers

# Dict of flags to gate adding the syslogHandler only once to the given singleton logger
loggerInitialized = {}

class SyslogOutOutputPlugin(OutputPlugin):
    useOutputQueue = True
    name = 'syslogout'
    MAXQUEUELENGTH = 10
    validSettings = [ 'syslogDestinationHost', 'syslogDestinationPort' ]
    defaultableSettings = [ 'syslogDestinationHost', 'syslogDestinationPort' ]
    intSettings = [ 'syslogDestinationPort' ]

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)
        self._syslogDestinationHost = sample.syslogDestinationHost if hasattr(sample, 'syslogDestinationHost') and sample.syslogDestinationHost else '127.0.0.1'
        self._syslogDestinationPort = sample.syslogDestinationPort if hasattr(sample, 'syslogDestinationPort') and sample.syslogDestinationPort else 1514

        loggerName = 'syslog' + sample.name
        self._l = logging.getLogger(loggerName)
        self._l.setLevel(logging.INFO)

        global loggerInitialized
        # This class is instantiated at least once each interval. Since each logger with a given name is a singleton,
        # only add the syslog handler once instead of every interval.
        if not loggerName in loggerInitialized:
            syslogHandler = logging.handlers.SysLogHandler(address=(self._syslogDestinationHost, int(self._syslogDestinationPort)))
            self._l.addHandler(syslogHandler)
            loggerInitialized[loggerName] = True

    def flush(self, q):
        for x in q:
            self._l.info(x['_raw'].rstrip())

def load():
    """Returns an instance of the plugin"""
    return SyslogOutOutputPlugin
