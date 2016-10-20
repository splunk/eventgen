from __future__ import division
from outputplugin import OutputPlugin
from time import sleep
import sys
try:
    import requests
except ImportError:
    pass
import json
import random
import logging

class NoServers(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class BadConnection(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

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
    validSettings = ['httpeventServers', 'httpeventOutputMode', 'httpeventMaxPayloadSize']
    defaultableSettings = ['httpeventServers', 'httpeventOutputMode', 'httpeventMaxPayloadSize']
    jsonSettings = ['httpeventServers']

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

        #disable any "requests" warnings
        requests.packages.urllib3.disable_warnings()
        # set default output mode to round robin
        #Setup loggers from the root eventgen
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'HTTPEventOutputPlugin', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

        #Bind passed in samples to the outputter.
        logger.debug("Outputmode: %s" % sample.httpeventOutputMode)
        self.lastsourcetype = None
        try:
            if hasattr(sample, 'httpeventServers') == False:
                logger.error('outputMode httpevent but httpeventServers not specified for sample %s' % self._sample.name)
                raise NoServers('outputMode httpevent but httpeventServers not specified for sample %s' % self._sample.name)
            self.httpeventoutputmode = sample.httpeventOutputMode if hasattr(sample, 'httpeventOutputMode') and sample.httpeventOutputMode else 'roundrobin'
            self.httpeventmaxsize = sample.httpeventMaxPayloadSize if hasattr(sample, 'httpeventMaxPayloadSize') and sample.httpeventMaxPayloadSize else 10000
            logger.debug("Currentmax size: %s " % self.httpeventmaxsize)
            self.httpeventServers = sample.httpeventServers
            logger.debug("Setting up the connection pool for %s in %s" % (self._sample.name, self._app))
            self.createConnections()
            logger.debug("Pool created.")
            logger.debug("Finished init of httpevent plugin.")
        except Exception as e:
            logger.exception(e)

    def createConnections(self):
        self.serverPool = []
        if self.httpeventServers:
            for server in self.httpeventServers.get('servers'):
                if not server.get('address'):
                    logger.error('requested a connection to a httpevent server, but no address specified for sample %s' % self._sample.name)
                    raise ValueError('requested a connection to a httpevent server, but no address specified for sample %s' % self._sample.name)
                if not server.get('port'):
                    logger.error('requested a connection to a httpevent server, but no port specified for server %s' % server)
                    raise ValueError('requested a connection to a httpevent server, but no port specified for server %s' % server)
                if not server.get('key'):
                    logger.error('requested a connection to a httpevent server, but no key specified for server %s' % server)
                    raise ValueError('requested a connection to a httpevent server, but no key specified for server %s' % server)
                if not ((server.get('protocol') == 'http') or (server.get('protocol') == 'https')):
                    logger.error('requested a connection to a httpevent server, but no protocol specified for server %s' % server)
                    raise ValueError('requested a connection to a httpevent server, but no protocol specified for server %s' % server)
                logger.debug("Validation Passed, Creating a requests object for server: %s" % server.get('address'))
                setserver = {}
                setserver['url'] = "%s://%s:%s/services/collector" % (server.get('protocol'), server.get('address'), server.get('port'))
                setserver['header'] = "Splunk %s" % server.get('key')
                logger.debug("Adding server set to pool, server: %s" % setserver)
                self.serverPool.append(setserver)
        else:
            raise NoServers('outputMode httpevent but httpeventServers not specified for sample %s' % self._sample.name)

    def _sendHTTPEvents(self, payload):
        currentreadsize = 0
        stringpayload = ""
        totalbytesexpected = 0
        totalbytessent = 0
        numberevents = len(payload)
        logger.debug("Sending %s events to splunk" % numberevents)
        for line in payload:
            logger.debugv("line: %s " % line)
            targetline = json.dumps(line)
            logger.debugv("targetline: %s " % targetline)
            targetlinesize = len(targetline)
            totalbytesexpected += targetlinesize
            if (int(currentreadsize) + int(targetlinesize)) <= int(self.httpeventmaxsize):
                stringpayload = stringpayload + targetline
                currentreadsize = currentreadsize + targetlinesize
                logger.debugv("stringpayload: %s " % stringpayload)
            else:
                logger.debug("Max size for payload hit, sending to splunk then continuing.")
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
                logger.debug("End of for loop hit for sending events to splunk, total bytes sent: %s ---- out of %s -----" % (totalbytessent, totalbytesexpected))
                self._transmitEvents(stringpayload)
            except Exception as e:
                raise e

    def _transmitEvents(self, payloadstring):
        targetServer = []
        logger.debugv("Transmission called with payloadstring: %s " % payloadstring)
        if self.httpeventoutputmode == "mirror":
            targetServer = self.serverPool
        else:
            targetServer.append(random.choice(self.serverPool))
        for server in targetServer:
            logger.debug("Selected targetServer object: %s" % targetServer)
            url = server['url']
            headers = {}
            headers['Authorization'] = server['header']
            headers['content-type'] = 'application/json'
            try:
                payloadsize = len(payloadstring)
                response = requests.post(url, data=payloadstring, headers=headers, verify=False)
                if not response.raise_for_status():
                    logger.debug("Payload successfully sent to httpevent server.")
                else:
                    logger.error("Server returned an error while trying to send, response code: %s" % response.status_code)
                    raise BadConnection("Server returned an error while sending, response code: %s" % response.status_code)
            except Exception as e:
                logger.error("Failed for exception: %s" % e)
                logger.error("Failed sending events to url: %s  sourcetype: %s  size: %s" % (url, self.lastsourcetype, payloadsize))
                logger.debugv("Failed sending events to url: %s  headers: %s payload: %s" % (url, headers, payloadstring))
                raise e

    def flush(self, q):
        logger.debug("Flush called on httpevent plugin")
        if len(q) > 0:
            try:
                payload = []
                lastsourcetype = ""
                payloadsize = 0
                logger.debug("Currently being called with %d events" % len(q))
                for event in q:
                    logger.debugv("HTTPEvent proccessing event: %s" % event)
                    payloadFragment = {}
                    if event.get('_raw') == None:
                        logger.error('failure outputting event, does not contain _raw')
                    else:
                        logger.debug("Event contains _raw, attempting to process...")
                        payloadFragment['event'] = event['_raw']
                        if event.get('source'):
                            logger.debug("Event contains source, adding to httpevent event")
                            payloadFragment['source'] = event['source']
                        if event.get('sourcetype'):
                            logger.debug("Event contains sourcetype, adding to httpevent event")
                            payloadFragment['sourcetype'] = event['sourcetype']
                            self.lastsourcetype = event['sourcetype']
                        if event.get('host'):
                            logger.debug("Event contains host, adding to httpevent event")
                            payloadFragment['host'] = event['host']
                        if event.get('_time'):
                            logger.debug("Event contains _time, adding to httpevent event")
                            payloadFragment['time'] = event['_time']
                        if event.get('index'):
                            logger.debug("Event contains index, adding to httpevent event")
                            payloadFragment['index'] = event['index']
                    logger.debugv("Full payloadFragment: %s" % json.dumps(payloadFragment))
                    payload.append(payloadFragment)
                logger.debug("Finished processing events, sending all to splunk")
                self._sendHTTPEvents(payload)
            except Exception as e:
                logger.error('failed indexing events, reason: %s ' % e)

def load():
    """Returns an instance of the plugin"""
    return HTTPEventOutputPlugin
