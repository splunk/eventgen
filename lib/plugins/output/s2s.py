from __future__ import division
from outputplugin import OutputPlugin

import struct
import socket
import datetime


class S2S:
    """
    Encode and send events to Splunk over the S2S V2 wire protocol.

    It should be noted V2 is a much older protocol and is no longer utilized by any Splunk Forwarder.
    It should still work, but its a very simple protocol and we've advanced pretty far since then.
    However, if you have fully cooked events, its very lightweight and very easy to implement
    which is why I elected to implement this version.
    """

    s = None
    signature_sent = None

    def __init__(self, host='localhost', port=9997):
        """
        Initialize object.  Need to know Splunk host and port for the TCP Receiver
        """
        self._open_connection(host, port)

        self.signature_sent = False

    def _open_connection(self, host='localhost', port=9997):
        """
        Open a connection to Splunk and return a socket
        """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))

    def _encode_sig(self, serverName='s2s-api', mgmtPort='9997'):
        """
        Create Signature element of the S2S Message.  Signature is C struct:

        struct S2S_Signature
        {
            char _signature[128];
            char _serverName[256];
            char _mgmtPort[16];
        };
        """
        if not self.signature_sent:
            self.signature_sent = True
            return struct.pack('!128s256s16s', '--splunk-cooked-mode-v2--', serverName, mgmtPort)
        else:
            return ''

    def _encode_string(self, tosend=''):
        """
        Encode a string to be sent across the wire to splunk

        Wire protocol has an unsigned integer of the length of the string followed
        by a null terminated string.
        """
        tosend = str(tosend)
        return struct.pack('!I%ds' % (len(tosend)+1), len(tosend)+1, tosend)

    def _encode_key_value(self, key='', value=''):
        """
        Encode a key/value pair to send across the wire to splunk

        A key value pair is merely a concatenated set of encoded strings.
        """
        return '%s%s' % (self._encode_string(key), self._encode_string(value))

    def _encode_event(self, index='main', host='', source='', sourcetype='', _raw='_done', _time=None):
        # Create signature
        sig = self._encode_sig()

        msg_size = len(struct.pack('!I', 0)) # size of unsigned 32 bit integer, which is the count of map entries
        maps = 1

        # May not have these, so set them first
        encoded_source = False
        encoded_sourcetype = False
        encoded_host = False
        encoded_index = False

        # Encode source
        if len(source) > 0:
            encoded_source = self._encode_key_value('MetaData:Source', 'source::'+source)
            maps += 1
            msg_size += len(encoded_source)

        # Encode sourcetype
        if len(sourcetype) > 0:
            encoded_sourcetype = self._encode_key_value('MetaData:Sourcetype', 'sourcetype::'+sourcetype)
            maps += 1
            msg_size += len(encoded_sourcetype)
        
        # Encode host
        if len(host) > 0:
            encoded_host = self._encode_key_value('MetaData:Host', 'host::'+host)
            maps += 1
            msg_size += len(encoded_host)

        # Encode index
        encoded_index = self._encode_key_value('_MetaData:Index', index)
        maps += 1
        msg_size += len(encoded_index)
        
        # Encode _raw
        encoded_raw = self._encode_key_value('_raw', _raw)
        msg_size += len(encoded_raw)

        # Will include a 32 bit integer 0 between the end of raw and the _raw trailer
        msg_size += len(struct.pack('!I', 0))

        # Encode "_raw" trailer... seems to just the string '_raw' repeated again at the end of the _raw field
        encoded_raw_trailer = self._encode_string('_raw')
        msg_size += len(encoded_raw_trailer)

        # Add _done... Not sure if there's a penalty to setting this for every event
        # but otherwise we don't flush immediately
        encoded_done = self._encode_key_value('_done', '_done')
        maps += 1
        msg_size += len(encoded_done)

        # Encode _time
        if _time != None:
            encoded_time = self._encode_key_value('_time', _time)
            msg_size += len(encoded_time)
            maps += 1

        # Create buffer, starting with the signature
        buf = sig
        # Add 32 bit integer with the size of the msg, calculated earlier
        buf += struct.pack('!I', msg_size)
        # Add number of map entries, which is 5, index, host, source, sourcetype, raw
        buf += struct.pack('!I', maps)
        # Add the map entries, index, source, sourcetype, host, raw
        buf += encoded_index
        buf += encoded_host if encoded_host else ''
        buf += encoded_source if encoded_source else ''
        buf += encoded_sourcetype if encoded_sourcetype else ''
        buf += encoded_time if encoded_time else ''
        buf += encoded_done
        buf += encoded_raw
        # Add dummy zero
        buf += struct.pack('!I', 0)
        # Add trailer raw
        buf += encoded_raw_trailer
        return buf

    def send_event(self, index='main', host='', source='', sourcetype='', _raw='', _time=None):
        """
        Encode and send an event to Splunk
        """
        if len(_raw) > 0:
            e = self._encode_event(index, host, source, sourcetype, _raw, _time)
            self.s.sendall(e)

    def close(self):
        """
        Close connection and send final done event
        """
        self.s.close()

class S2SOutputPlugin(OutputPlugin):
    name = 's2s'
    MAXQUEUELENGTH = 10

    s2s = None

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

    def flush(self, q):
        if self.s2s == None:
            self.s2s = S2S(self._sample.splunkHost, self._sample.splunkPort)
        if len(q) > 0:
            m = q.popleft()
            while m:
                try:
                    self.s2s.send_event(m['index'], m['host'], m['source'], m['sourcetype'], m['_raw'], m['_time'])
                except KeyError:
                    pass
            
                try:
                    m = q.popleft()
                except IndexError:
                    m = False

def load():
    """Returns an instance of the plugin"""
    return S2SOutputPlugin