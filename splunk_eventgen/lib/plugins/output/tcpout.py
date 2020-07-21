from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.outputplugin import OutputPlugin


class TcpOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "tcpout"
    MAXQUEUELENGTH = 10

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self._tcpDestinationHost = (
            sample.tcpDestinationHost
            if hasattr(sample, "tcpDestinationHost") and sample.tcpDestinationHost
            else "127.0.0.1"
        )
        self._tcpDestinationPort = (
            sample.tcpDestinationPort
            if hasattr(sample, "tcpDestinationPort") and sample.tcpDestinationPort
            else "3333"
        )

        import socket  # Import socket module

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def flush(self, q):
        self.s.connect((self._tcpDestinationHost, int(self._tcpDestinationPort)))
        logger.info(
            "Socket connected to {0}:{1}".format(
                self._tcpDestinationHost, self._tcpDestinationPort
            )
        )
        for x in q:
            msg = x["_raw"].rstrip() + "\n"
            self.s.send(str.encode(msg))
        self.s.close()


def load():
    """Returns an instance of the plugin"""
    return TcpOutputPlugin
