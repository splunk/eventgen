from __future__ import division

import logging
import random
import urllib

from outputplugin import OutputPlugin

try:
    import requests
    from requests import Session
    from requests_futures.sessions import FuturesSession
    from concurrent.futures import ThreadPoolExecutor
except ImportError:
    pass
try:
    import ujson as json
except:
    import json


class NoServers(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class BadConnection(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class HTTPEventOutputPlugin(OutputPlugin):
    '''
    HTTPEvent output will enable events that are generated to be sent directly
    to splunk through the HTTP event input.  In order to use this output plugin,
    you will need to supply an attribute 'httpeventServers' as a valid json object.
    this json object should look like the following:

    {servers:[{ protocol:http/https, address:127.0.0.1, port:8088, key:12345-12345-123123123123123123}]}

    '''
    name = 'httpevent'
    MAXQUEUELENGTH = 1000
    useOutputQueue = False
    validSettings = ['httpeventServers', 'httpeventOutputMode', 'httpeventMaxPayloadSize']
    defaultableSettings = ['httpeventServers', 'httpeventOutputMode', 'httpeventMaxPayloadSize']
    jsonSettings = ['httpeventServers']

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

    # TODO: make workers a param that can be set in eventgen.conf
    def _setup_REST_workers(self, session=None, workers=10):
        # disable any "requests" warnings
        requests.packages.urllib3.disable_warnings()
        # Bind passed in samples to the outputter.
        self.lastsourcetype = None
        if not session:
            session = Session()
        self.session = FuturesSession(session=session, executor=ThreadPoolExecutor(max_workers=workers))
        self.active_session_info = []

    @staticmethod
    def _urlencode(value):
        '''
        Takes a value and make sure everything int he string is URL safe.
        :param value: string
        :return: urlencoded string
        '''
        return urllib.quote(value)

    @staticmethod
    def _bg_convert_json(sess, resp):
        '''
        Takes a futures session object, and sets the data to a parsed json output. Use this as a background task for the
        session queue. Example: future = session.get('http://httpbin.org/get', background_callback=_bg_convert_json)
        :param sess: futures session object. Automatically called on a background_callback as aruguments.
        :param resp: futures resp object.  Automatically called on a background_callback as aruguments.
        :return:
        '''
        if resp.status_code == 200:
            if getattr(resp, "json", None):
                resp.data = resp.json()
            else:
                if type(resp.data) == str:
                    resp.data = json.loads(resp.data)

    def updateConfig(self, config):
        OutputPlugin.updateConfig(self, config)
        try:
            if hasattr(self.config, 'httpeventServers') is False:
                if hasattr(self._sample, 'httpeventServers'):
                    self.config.httpeventServers = self._sample.httpeventServers
                else:
                    self.logger.error(
                        'outputMode httpevent but httpeventServers not specified for sample %s' % self._sample.name)
                    raise NoServers(
                        'outputMode httpevent but httpeventServers not specified for sample %s' % self._sample.name)
            # set default output mode to round robin
            if hasattr(self.config, 'httpeventOutputMode') and self.config.httpeventOutputMode:
                self.httpeventoutputmode = self.config.httpeventOutputMode
            else:
                if hasattr(self._sample, 'httpeventOutputMode') and self._sample.httpeventOutputMode:
                    self.httpeventoutputmode = self._sample.httpeventOutputMode
                else:
                    self.httpeventoutputmode = 'roundrobin'

            if hasattr(self.config, 'httpeventMaxPayloadSize') and self.config.httpeventMaxPayloadSize:
                self.httpeventmaxsize = self.config.httpeventMaxPayloadSize
            else:
                if hasattr(self._sample, 'httpeventMaxPayloadSize') and self._sample.httpeventMaxPayloadSize:
                    self.httpeventmaxsize = self._sample.httpeventMaxPayloadSize
                else:
                    self.httpeventmaxsize = 10000

            if hasattr(self.config, 'httpeventAllowFailureCount') and self.config.httpeventAllowFailureCount:
                self.httpeventAllowFailureCount = int(self.config.httpeventOutputMode)
            else:
                if hasattr(self._sample, 'httpeventAllowFailureCount') and self._sample.httpeventAllowFailureCount:
                    self.httpeventAllowFailureCount = int(self._sample.httpeventAllowFailureCount)
                else:
                    self.httpeventAllowFailureCount = 100

            self.logger.debug("Currentmax size: %s " % self.httpeventmaxsize)
            if isinstance(config.httpeventServers, str):
                self.httpeventServers = json.loads(config.httpeventServers)
            else:
                self.httpeventServers = config.httpeventServers
            self.logger.debug("Setting up the connection pool for %s in %s" % (self._sample.name, self._app))
            self.createConnections()
            self.logger.debug("Pool created and finished init of httpevent plugin.")
        except Exception as e:
            self.logger.exception(str(e))

    def createConnections(self):
        self.serverPool = []
        if self.httpeventServers:
            for server in self.httpeventServers.get('servers'):
                if not server.get('address'):
                    raise ValueError(
                        'requested a connection to a httpevent server, but no address specified for sample %s' %
                        self._sample.name)
                if not server.get('port'):
                    raise ValueError(
                        'requested a connection to a httpevent server, but no port specified for server %s' % server)
                if not server.get('key'):
                    raise ValueError(
                        'requested a connection to a httpevent server, but no key specified for server %s' % server)
                if not ((server.get('protocol') == 'http') or (server.get('protocol') == 'https')):
                    raise ValueError(
                        'requested a connection to a httpevent server, but no protocol specified for server %s' %
                        server)
                self.logger.debug("Validation Passed, Creating a requests object for server: %s" % server.get('address'))

                setserver = {}
                setserver['url'] = "%s://%s:%s/services/collector" % (server.get('protocol'), server.get('address'),
                                                                      server.get('port'))
                setserver['header'] = "Splunk %s" % server.get('key')
                self.logger.debug("Adding server set to pool, server: %s" % setserver)
                self.serverPool.append(setserver)
        else:
            raise NoServers('outputMode httpevent but httpeventServers not specified for sample %s' % self._sample.name)

    def _sendHTTPEvents(self, payload):
        currentreadsize = 0
        stringpayload = ""
        totalbytesexpected = 0
        totalbytessent = 0
        numberevents = len(payload)
        self.logger.debug("Sending %s events to splunk" % numberevents)
        session_info_list = []
        for line in payload:
            self.logger.debugv("line: %s " % line)
            targetline = json.dumps(line)
            self.logger.debugv("targetline: %s " % targetline)
            targetlinesize = len(targetline)
            totalbytesexpected += targetlinesize
            if (int(currentreadsize) + int(targetlinesize)) <= int(self.httpeventmaxsize):
                stringpayload = stringpayload + targetline
                currentreadsize = currentreadsize + targetlinesize
                self.logger.debugv("stringpayload: %s " % stringpayload)
            else:
                self.logger.debug("Max size for payload hit, sending to splunk then continuing.")
                self._transmitEvents(stringpayload)
                totalbytessent += len(stringpayload)
                currentreadsize = 0
                stringpayload = targetline
                
        totalbytessent += len(stringpayload)
        self.logger.debug(
            "End of for loop hit for sending events to splunk, total bytes sent: %s ---- out of %s -----" %
            (totalbytessent, totalbytesexpected))
        self._transmitEvents(stringpayload)

    def _transmitEvents(self, payloadstring):
        targetServer = []
        self.logger.debug("Transmission called with payloadstring length: %s " % len(payloadstring))

        if not self.serverPool:
            raise Exception("No available servers exist. Please check your httpServers.")
        
        if self.httpeventoutputmode == "mirror":
            targetServer = self.serverPool
        else:
            targetServer.append(random.choice(self.serverPool))

        for server in targetServer:
            self.logger.debug("Selected targetServer object: %s" % targetServer)
            url = server['url']
            headers = {}
            headers['Authorization'] = server['header']
            headers['content-type'] = 'application/json'
            try:
                session_info = list()
                session_info.append(url)
                session_info.append(self.session.post(url=url, data=payloadstring, headers=headers, verify=False))
                self.active_session_info.append(session_info)
            except Exception as e:
                self.logger.error("Failed sending events to url: %s  sourcetype: %s  size: %s" %
                                  (url, self.lastsourcetype, len(payloadstring)))
    
    def reset_count(self, url):
        try:
            self.config.httpeventServersCountdownMap['url'] = self.httpeventAllowFailureCount
        except:
            pass
        
    def remove_requets_target(self, url):
        if isinstance(self.config.httpeventServers, str):
            httpeventServers = json.loads(self.config.httpeventServers)
        else:
            httpeventServers = self.config.httpeventServers

        # If url fail more than specified count, we completely remove it from the pool.
        try:
            countdown_map = self.config.httpeventServersCountdownMap
        except:
            self.config.httpeventServersCountdownMap = {}
            for i, server_info in enumerate(self.serverPool):
                # URL is in format: https://2.2.2.2:8088/services/collector
                self.config.httpeventServersCountdownMap[server_info.get('url', '')] = self.httpeventAllowFailureCount
            countdown_map = self.config.httpeventServersCountdownMap

        for i, server_info in enumerate(httpeventServers.get('servers', [])):
            target_url = '{}://{}:{}'.format(server_info.get('protocol', ''), server_info.get('address', ''), server_info.get('port', '')) 
            if target_url in url:
                if countdown_map[url] <= 0:
                    del httpeventServers.get('servers')[i]
                    self.logger.warning("Cannot reach {}. Removing from the server pool".format(url))
                else:
                    countdown_map[url] -= 1
                    self.logger.debug("Cannot reach {}. Lowering countdown to {}".format(url, countdown_map[url]))

        if isinstance(self.config.httpeventServers, str):
            self.config.httpeventServers = json.dumps(httpeventServers)
        else:
            self.config.httpeventServers = httpeventServers
        self._sample.httpeventServers = httpeventServers
        self.config.httpeventServersCountdownMap = countdown_map

    def flush(self, q):
        self.logger.debug("Flush called on httpevent plugin")
        self._setup_REST_workers()
        if len(q) > 0:
            try:
                payload = []
                self.logger.debug("Currently being called with %d events" % len(q))
                for event in q:
                    self.logger.debugv("HTTPEvent proccessing event: %s" % event)
                    payloadFragment = {}
                    if event.get('_raw') is None or event['_raw'] == "\n":
                        self.logger.error('failure outputting event, does not contain _raw')
                    else:
                        self.logger.debugv("Event contains _raw, attempting to process...")
                        payloadFragment['event'] = event['_raw']
                        if event.get('source'):
                            self.logger.debugv("Event contains source, adding to httpevent event")
                            payloadFragment['source'] = event['source']
                        if event.get('sourcetype'):
                            self.logger.debugv("Event contains sourcetype, adding to httpevent event")
                            payloadFragment['sourcetype'] = event['sourcetype']
                            self.lastsourcetype = event['sourcetype']
                        if event.get('host'):
                            self.logger.debugv("Event contains host, adding to httpevent event")
                            payloadFragment['host'] = event['host']
                        if event.get('_time'):
                            # make sure _time can be an epoch timestamp
                            try:
                                float(event.get("_time"))
                                self.logger.debugv("Event contains _time, adding to httpevent event")
                                payloadFragment['time'] = event['_time']
                            except:
                                self.logger.error("Timestamp not in epoch format, ignoring event: {0}".format(event))
                        if event.get('index'):
                            self.logger.debugv("Event contains index, adding to httpevent event")
                            payloadFragment['index'] = event['index']
                    self.logger.debugv("Full payloadFragment: %s" % json.dumps(payloadFragment))
                    payload.append(payloadFragment)
                self.logger.debug("Finished processing events, sending all to splunk")
                self._sendHTTPEvents(payload)
                if not self.config.httpeventWaitResponse:
                    self.logger.debug("Ignoring response from HTTP server, leaving httpevent outputter")
                else:
                    for session_info in self.active_session_info:
                        url, session = session_info[0], session_info[1]
                        try:
                            response = session.result(3)
                            self.reset_count(url)
                            self.logger.debug("Payload successfully sent to " + url)
                        except Exception as e:
                            self.remove_requets_target(url)
            except Exception as e:
                self.logger.error('Failed sending events, reason: %s ' % e)

def load():
    """Returns an instance of the plugin"""
    return HTTPEventOutputPlugin
