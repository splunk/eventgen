from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.outputplugin import OutputPlugin


class UdpOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "udpout"
    MAXQUEUELENGTH = 10

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self._udpDestinationHost = (
            sample.udpDestinationHost
            if hasattr(sample, "udpDestinationHost") and sample.udpDestinationHost
            else "127.0.0.1"
        )
        self._udpDestinationPort = (
            sample.udpDestinationPort
            if hasattr(sample, "udpDestinationPort") and sample.udpDestinationPort
            else "3333"
        )

        import socket  # Import socket module

        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def flush(self, q):
        for x in q:
            msg = x["_raw"].rstrip() + "\n"
            self.s.sendto(
                str.encode(msg),
                (self._udpDestinationHost, int(self._udpDestinationPort)),
            )
        logger.info("Flushing in udpout.")


def load():
    """Returns an instance of the plugin"""
    return UdpOutputPlugin
