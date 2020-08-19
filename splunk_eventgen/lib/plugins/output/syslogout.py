import logging
import logging.handlers

from splunk_eventgen.lib.outputplugin import OutputPlugin

# Dict of flags to gate adding the syslogHandler only once to the given singleton logger
loggerInitialized = {}


# This filter never returns False, because its purpose is just to add the host field so it's
# available to the logging formatter.
class HostFilter(logging.Filter):
    def __init__(self, host):
        self.host = host

    def filter(self, record):
        record.host = self.host
        return True


class SyslogOutOutputPlugin(OutputPlugin):
    useOutputQueue = True
    name = "syslogout"
    MAXQUEUELENGTH = 10
    validSettings = [
        "syslogDestinationHost",
        "syslogDestinationPort",
        "syslogAddHeader",
    ]
    defaultableSettings = [
        "syslogDestinationHost",
        "syslogDestinationPort",
        "syslogAddHeader",
    ]
    intSettings = ["syslogDestinationPort"]

    def __init__(self, sample, output_counter=None):
        syslogAddHeader = getattr(sample, "syslogAddHeader", False)
        OutputPlugin.__init__(self, sample, output_counter)
        self._syslogDestinationHost = (
            sample.syslogDestinationHost
            if hasattr(sample, "syslogDestinationHost") and sample.syslogDestinationHost
            else "127.0.0.1"
        )
        self._syslogDestinationPort = (
            sample.syslogDestinationPort
            if hasattr(sample, "syslogDestinationPort") and sample.syslogDestinationPort
            else 1514
        )

        loggerName = "syslog" + sample.name
        self._l = logging.getLogger(loggerName)
        if syslogAddHeader:
            self._l.addFilter(HostFilter(host=sample.host))
        self._l.setLevel(logging.INFO)

        global loggerInitialized
        # This class is instantiated at least once each interval. Since each logger with a given name is a singleton,
        # only add the syslog handler once instead of every interval.
        if loggerName not in loggerInitialized:
            syslogHandler = logging.handlers.SysLogHandler(
                address=(self._syslogDestinationHost, int(self._syslogDestinationPort))
            )
            if syslogAddHeader:
                formatter = logging.Formatter(
                    fmt="%(asctime)s %(host)s %(message)s", datefmt="%b %d %H:%M:%S"
                )
                syslogHandler.setFormatter(formatter)
            self._l.addHandler(syslogHandler)
            loggerInitialized[loggerName] = True

    def flush(self, q):
        for x in q:
            self._l.info(x["_raw"].rstrip())


def load():
    """Returns an instance of the plugin"""
    return SyslogOutOutputPlugin
