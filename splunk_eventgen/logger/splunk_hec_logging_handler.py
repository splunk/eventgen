from __future__ import absolute_import
import json
import logging
import os
import threading
import time
import datetime
import socket
import traceback
import platform
import commands
import atexit
from requests_futures import sessions

def setInterval(interval):
    def decorator(function):
        def wrapper(*args, **kwargs):
            stopped = threading.Event()
            def loop(): # executed in another thread
                while True:
                    if stopped.is_set():
                        return
                    else:
                        function(*args, **kwargs)
                        time.sleep(interval)
            t = threading.Thread(target=loop)
            t.daemon = True
            t.start()
            return stopped
        return wrapper
    return decorator

class SplunkHECHandler(logging.Handler):

    def __init__(self, targetserver, hec_token, eventgen_name=None):
        self._name = 'eventgen_splunk_hec_logger'
        self.targetserver = targetserver
        self.hec_token = hec_token
        self.host = socket.gethostname()
        self.pid = os.getpid()
        self.events = []
        self.send = True
        self.os = platform.platform()
        self.system_username = commands.getoutput('whoami')
        self.eventgen_name = eventgen_name
        atexit.register(self._stopFlushTimer)

        self.log = logging.getLogger(self._name)
        self.log.setLevel(logging.DEBUG)
        self.log.info("SplunkHECHandler logger is initialized")

        try:
            self.ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in[socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        except:
            self.ip = "unknown"

        self.session = sessions.FuturesSession(max_workers=32)

        if not targetserver or not hec_token:
            self.log.warn("Please provide valid targetserver and hec_token in default/eventgen_engine.conf.")
            self.send = False

        super(SplunkHECHandler, self).__init__()

        self.timer = self._flushAndRepeatTimer()

    @setInterval(1)
    def _flushAndRepeatTimer(self):
        if self.send:
            self.flush()

    def _stopFlushTimer(self):
        if self.send:
            self.send = False
            self.flush()
            self.timer.set()


    def _getEndpoint(self):
        targeturi = "{0}/services/collector/event".format(self.targetserver)
        return targeturi

    def _getTraceback(self, record):
        if record.exc_info:
            return traceback.format_exc()
        return None

    def _getPayload(self, record):
        payload = {
            'event': {
                'log': record.name,
                'level': logging.getLevelName(record.levelno),
                'message': record.getMessage(),
                'local_time': str(datetime.datetime.now()),
                'ip': self.ip,
                'os': self.os,
                'system_username': self.system_username,
                'eventgen_name': self.eventgen_name
            },
            'time': time.time(),
            'index': 'eventgen',
            'source': 'eventgen',
            'sourcetype': 'eventgen6',
            'host': self.host,
        }
        tb = self._getTraceback(record)
        if tb:
            payload['traceback'] = tb
        return json.dumps(payload)

    def _sendHTTPEvents(self, current_batch):
        currentreadsize = 0
        stringpayload = ""
        totalbytesexpected = 0
        totalbytessent = 0
        for line in current_batch:
            targetline = str(line)
            targetlinesize = len(targetline)
            totalbytesexpected += targetlinesize
            if (int(currentreadsize) + int(targetlinesize)) <= 10000:  #10000 is the default max size of HEC sessions
                stringpayload = stringpayload + targetline
                currentreadsize = currentreadsize + targetlinesize
            else:
                try:
                    self._transmitEvents(stringpayload)
                    totalbytessent += len(stringpayload)
                    currentreadsize = 0
                    stringpayload = targetline
                except Exception as e:
                    raise e
        else:
            try:
                totalbytessent += len(stringpayload)
                self._transmitEvents(stringpayload)
            except Exception as e:
                raise e

    def _transmitEvents(self, data):
        # Sending events every 10 seconds
        try:
            self.session.post(self._getEndpoint(),
                              data=data,
                              headers={'Authorization': 'Splunk {0}'.format(self.hec_token), 'content-type': 'application/json'},
                              verify=False)
            time.sleep(10)
        except Exception as e:
            self.log.exception(e)
            raise e

    def flush(self):
        self.log.debug('Flush Running. Num of events: {}.'.format(len(self.events)))
        events = self.events
        self.events = []
        if self.send:
            self._sendHTTPEvents(events)

    def emit(self, record):
        """
        Override emit() method in handler parent for sending log to RESTful API
        """
        pid = os.getpid()
        if pid != self.pid:
            self.pid = pid
            self.events = []
            self.timer = self._flushAndRepeatTimer()
            atexit.register(self._stopFlushTimer)

        if record.name.startswith('requests') or record.name in ['urllib3.connectionpool']:
            return

        self.events.append(self._getPayload(record))
