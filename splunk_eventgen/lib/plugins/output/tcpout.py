from __future__ import division
from outputplugin import OutputPlugin
import logging

class TcpOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = 'tcpout'
    MAXQUEUELENGTH = 10

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

        self._tcpDestinationHost = sample.tcpDestinationHost if hasattr(sample,'tcpDestinationHost') and sample.tcpDestinationHost else '127.0.0.1'
        self._tcpDestinationPort = sample.tcpDestinationPort if hasattr(sample,'tcpDestinationPort') and sample.tcpDestinationPort else '3333'

        import socket  # Import socket module
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

   # Bind to the port
    def flush(self, q):
        self.s.connect((self._tcpDestinationHost, int(self._tcpDestinationPort)))
        self.logger.info("Socket connected to {0}:{1}".format(self._tcpDestinationHost, self._tcpDestinationPort))
        for x in q:
            self.s.send(x['_raw'].rstrip() + '\n')
        self.s.close()

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')

def load():
    """Returns an instance of the plugin"""
    return TcpOutputPlugin