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
        self._name = 'splunk_hec_logger'
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

        self._log = logging.getLogger(self._name)
        self._log.info("SplunkHECHandler logger is initialized")

        try:
            self.ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in[socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        except:
            self.ip = "unknown"

        self.session = sessions.FuturesSession(max_workers=32)

        if not targetserver or not hec_token:
            self._log.warn("Please provide valid targetserver and hec_token in default/eventgen_engine.conf.")
            self.send = False

        super(SplunkHECHandler, self).__init__()

        self._flushAndRepeatTimer()

    @setInterval(1)
    def _flushAndRepeatTimer(self):
        self.flush()

    def _stopFlushTimer(self):
        self.flush()

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
            time.sleep(20)
        except Exception as e:
            self._log.exception(e)
            raise e

    def flush(self):
        self._log.debug('Flush Running. Num of events: {}.'.format(len(self.events)))
        events = self.events
        self.events = []
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

    # def __init__(self, targetserver, hec_token, log, orca_state, internal_log_level=logging.INFO, source="eventgen6", sourcetype="eventgen6_logs", index="eventgen6", max_attempts=5, targetapp=""):
    #     """
    #     log: logging object, should always be passed in
    #     hec_token: The splunk hec custom token
    #     source: source to use for events
    #     sourcetype: sourcetype to use for events
    #     index: index to store events (defaults to _internal)
    #     targetserver: full uri for battlecat server, ex: https://127.0.0.1:8088/
    #     max_attempts: Max attempts to try and send an event before giving up.
    #     """
    #     self.log = log
    #     self.log.setLevel(internal_log_level)
    #     self.pid = os.getpid()
    #     self.host = socket.getfqdn()
    #     # found here https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    #     try:
    #         self.ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in[socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
    #     except Exception as e:
    #         self.log.exception(e)
    #         self.ip = "unknown"
    #     self.uuid = uuid.uuid4()
    #     self.source = source
    #     self.sourcetype = sourcetype
    #     self.index = index
    #     self.hec_token = hec_token
    #     self.targetserver = targetserver
    #     self.app = targetapp
    #     super(SplunkHECHandler, self).__init__(self._getEndpoint())
    #     self.max_attempts = max_attempts
    #     self.timer = None
    #     self.events = []
    #     if orca_state:
    #         self.orca_home = orca_state.orca_home
    #         self.orca_conf_user = os.environ.get('ORCA_OWNER')
    #         self.hec_max_bytes_payload = int(orca_state.orca_config.get_value('general', 'hec_max_bytes_payload'))
    #         self.orca_version = orca_state.orca_version
    #     else:
    #         self.orca_home = "Reaper home"
    #         self.orca_conf_user = "Reaper user"
    #         self.hec_max_bytes_payload = 10000
    #         self.orca_version = "Reaper Version"
    #     self.os = platform.platform()
    #     self.docker_version = commands.getoutput("docker --version")
    #     self.system_username = commands.getoutput('whoami')
    #
    #     self.log.debug("setting timer to none and emptying log array")
    #     self.log.debug("Calling flush and repeat timer")
    #     self.timer = self._flushAndRepeatTimer()
    #     self.log.debug("flush and base time set, registering end of logging, restart timer")
    #     atexit.register(self._stopFlushTimer)
    #     self.send = False
    #     self._check_endpoint(targetserver)
    #     self.log.debug("End of init, logger now async.")
    #

    #
    # @setInterval(1)
    # def _flushAndRepeatTimer(self):
    #     self.log.debug("Running FlushAndRepeatTimer")
    #     self.flush()
    #
    # def _stopFlushTimer(self):
    #     self.log.debug("Stop FlushAndRepeatTimer")
    #     self.timer.set()
    #     self.flush()
    #
    # def _getEndpoint(self):
    #     """
    #     Override Build Splunk's RESTful API endpoint
    #     """
    #     self.log.debug("Running getEndpoint")
    #     targeturi = "{0}/services/collector".format(self.targetserver)
    #     self.log.debug("returning targeturi: {0}".format(targeturi))
    #     return targeturi
    #
    # def _prepPayload(self, record):
    #     """
    #     record: generated from logger module
    #     This preps the payload to be formatted in whatever content-type is
    #     expected from the RESTful API.
    #     """
    #     self.log.debug("Running prepPayload")
    #     self.log.debug("preping payload for record: {0}".format(record))
    #     return json.dumps(self._getPayload(record))
    #
    # def _getPayload(self, record):
    #     """
    #     The data that will be sent to splunk HEC.
    #     """
    #     self.log.debug("Running getPayload")
    #     payload = {
    #                'event':{
    #                      'logger': record.name,
    #                      'uuid': str(self.uuid),
    #                      'level': logging.getLevelName(record.levelno),
    #                      'app': self.app,
    #                      'message': record.getMessage(),
    #                      'ip': self.ip,
    #                      'local_time': str(datetime.datetime.now()),
    #                      'system_username': self.system_username,
    #                      'orca_username': record.user if hasattr(record, 'user') else None,
    #                      'orca_deployment_id': record.deployment if hasattr(record, 'deployment') else None,
    #                      '.orca_loc':self.orca_home,
    #                      'os': self.os,
    #                      'cmd_line_args': sys.argv[1:],
    #                      'orca_version': self.orca_version,
    #                      'docker_version':self.docker_version
    #                     },
    #                'time': time.time(),
    #                'source': self.source,
    #                'sourcetype': self.sourcetype,
    #                'index': self.index,
    #                'host': self.host
    #         }
    #     self.log.debug("Returning this payload: {0}".format(payload))
    #     return payload
    #
    # def handle_response(self, batch, sess, resp, attempt=0, *args, **kwargs):
    #     self.log.debug('Batch: {0} Sess: {1} Resp: {2}'.format(batch, sess, resp))
    #     self.log.debug('Target Attempt: {0}'.format(attempt))
    #     self.log.debug("Running handle_response")
    #     if resp.status_code != 200:
    #         self.log("Status Code not 200, Status Code: {0}".format(resp.status_code))
    #         if attempt <= self.max_attempts:
    #             attempt += 1
    #             self.flush(batch, attempt)
    #         else:
    #             self.log.error("Failed sending events due to status code")
    #     else:
    #         self.log.debug("The response came back with a {status_code}".format(status_code=resp.status_code))
    #         self.log.debug("With message {message}".format(message=resp.text))
    #
    # def _sendHTTPEvents(self, current_batch, callback):
    #     currentreadsize = 0
    #     stringpayload = ""
    #     totalbytesexpected = 0
    #     totalbytessent = 0
    #     numberevents = len(current_batch)
    #     self.log.debug("Sending %s events to splunk" % numberevents)
    #     for line in current_batch:
    #         self.log.debug("line: %s " % line)
    #         targetline = str(line)
    #         self.log.debug("targetline: %s " % targetline)
    #         targetlinesize = len(targetline)
    #         totalbytesexpected += targetlinesize
    #         if (int(currentreadsize) + int(targetlinesize)) <= self.hec_max_bytes_payload:  #10000 is the default max size of HEC sessions
    #             stringpayload = stringpayload + targetline
    #             currentreadsize = currentreadsize + targetlinesize
    #             self.log.debug("stringpayload: %s " % stringpayload)
    #         else:
    #             self.log.debug("Max size for payload hit, sending to splunk then continuing.")
    #             try:
    #                 self.log.debug(callback)
    #                 self._transmitEvents(stringpayload, callback)
    #                 totalbytessent += len(stringpayload)
    #                 currentreadsize = 0
    #                 stringpayload = targetline
    #             except Exception as e:
    #                 self.log.error("Failed in http request: {0}".format(e))
    #     else:
    #         try:
    #             totalbytessent += len(stringpayload)
    #             self.log.debug("End of for loop hit for sending events to splunk, total bytes sent: %s ---- out of %s -----" % (totalbytessent, totalbytesexpected))
    #             self.log.debug(callback)
    #             self._transmitEvents(stringpayload, callback)
    #         except Exception as e:
    #             self.log.error("Failed in http request: {0}".format(e))
    #
    # def _transmitEvents(self, data, callback):
    #     try:
    #         self.log.debug("Attempting to send events to splunk.")
    #         self.log.debug("Data object: {0}, Data type: {1}".format(data, type(data)))
    #         response=self.session.post(self._getEndpoint(),
    #                       data=data,
    #                       headers={'Authorization': 'Splunk {0}'.format(self.hec_token), 'content-type': 'application/json' },
    #                       background_callback=callback,
    #                       verify=False)
    #         self.log.debug("The response from the session post was {0}".format(response))
    #         self.log.debug("The Result is {0}".format(response.result()))
    #     except Exception as e:
    #         self.log.debug("Failed sending events. Exception: {0}".format(e))
    #
    # def flush(self, current_batch=None, attempt=1):
    #     self.log.debug("In Flush, called with batch: {0} and attempt: {1}".format(current_batch,attempt))
    #     if current_batch is None:
    #         self.log.debug("No current batch, checking if there are events waiting to be sent")
    #         self.events, current_batch = [], self.events
    #         self.log.debug("Resetting self.events and using a current_batch size of: {0}".format(len(current_batch)))
    #     callback = partial(self.handle_response, current_batch, attempt=attempt)
    #     if current_batch:
    #         self.log.debug("Current Batch Now Exists. Processing the objects")
    #         self._sendHTTPEvents(current_batch, callback)
    #
    # def emit(self, record):
    #     """
    #     Override emit() method in handler parent for sending log to RESTful API
    #     """
    #     # Check if we were able to hit the endpoint, return if not
    #     if not self.send:
    #         return
    #     self.log.debug("In Emit")
    #     pid = os.getpid()
    #     if pid != self.pid:
    #         self.pid = pid
    #         self.events = []
    #         self.timer = self._flushAndRepeatTimer()
    #         atexit.register(self._stopFlushTimer)
    #
    #     # avoid infinite recursion
    #     if record.name.startswith('HEC_LOG_OBJECT'):
    #         return
    #
    #     self.events.append(self._prepPayload(record))
    #     self.log.debug("Emitter finished, events added.")
