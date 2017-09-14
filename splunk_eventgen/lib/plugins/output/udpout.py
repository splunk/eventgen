from __future__ import division
from outputplugin import OutputPlugin
import logging

class UdpOutputPlugin(OutputPlugin):
    queueable = True
    name = 'udpout'
    MAXQUEUELENGTH = 10

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

        self._l = logging.getLogger('UdpOutput'+ sample.name)
        self._l.setLevel(logging.INFO)

        self._udpDestinationHost = sample.udpDestinationHost if hasattr(sample,'udpDestinationHost') and sample.udpDestinationHost else '127.0.0.1'
        self._udpDestinationPort = sample.udpDestinationPort if hasattr(sample,'udpDestinationPort') and sample.udpDestinationPort else '3333'

        import socket  # Import socket module
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def flush(self, q):
        for x in q:
            msg = x['_raw'].rstrip() + '\n'
            self.s.sendto(msg, (self._udpDestinationHost, int(self._udpDestinationPort)))
            self._l.info("Sent msg to Host:{0} Port:{1}".format(self._udpDestinationHost, self._udpDestinationPort))

def load():
    """Returns an instance of the plugin"""
    return UdpOutputPlugin