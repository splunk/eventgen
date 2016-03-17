from __future__ import division
from outputplugin import OutputPlugin
import sys
try:
    import requests
except ImportError:
    pass
import json
import random
import logging

class BattleCatOutputPlugin(OutputPlugin):
    '''
    Battlecat output will enable events that are generated to be sent directly
    to splunk through the HTTP event input.  In order to use this output plugin,
    you will need to supply an attribute 'battlecatServers' as a valid json object.
    this json object should look like the following:
    
    {servers:[{ protocol:http/https, address:127.0.0.1, port:8088, key:12345-12345-123123123123123123}]}
    
    '''
    name = 'battlecat'
    MAXQUEUELENGTH = 100
    validSettings = [ 'battlecatServers' ]
    defaultableSettings = [ 'battlecatServers' ]
    jsonSettings = ['battlecatServers']

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

        #disable any "requests" warnings
        requests.packages.urllib3.disable_warnings()
        #Setup loggers from the root eventgen
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'BattlecatOutputPlugin', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

        #Bind passed in samples to the outputter.
        if hasattr(sample, 'battlecatServers') == False:
            logger.error('outputMode battlecat but battlecatServers not specified for sample %s' % self._sample.name)
            raise ValueError('outputMode battlecat but battlecatServers not specified for sample %s' % self._sample.name)
        self.battlecatServers = sample.battlecatServers
        logger.debug("Setting up the connection pool for %s in %s" % (self._sample.name, self._app))
        self.createConnections()
        logger.debug("Pool created.")

    def createConnections(self):
        self.serverPool = []
        for server in self.battlecatServers.get('servers'):
            if not server.get('address'):
                logger.error('requested a connection to a battlecat server, but no address specified for sample %s' % self._sample.name)
                raise ValueError('requested a connection to a battlecat server, but no address specified for sample %s' % self._sample.name)
            if not server.get('port'):
                logger.error('requested a connection to a battlecat server, but no port specified for server %s' % server)
                raise ValueError('requested a connection to a battlecat server, but no port specified for server %s' % server)
            if not server.get('key'):
                logger.error('requested a connection to a battlecat server, but no key specified for server %s' % server)
                raise ValueError('requested a connection to a battlecat server, but no key specified for server %s' % server)
            if not ((server.get('protocol') == 'http') or (server.get('protocol') == 'https')):
                logger.error('requested a connection to a battlecat server, but no protocol specified for server %s' % server)
                raise ValueError('requested a connection to a battlecat server, but no protocol specified for server %s' % server)
            logger.debug("Validation Passed, Creating a requests object for server: %s" % server.get('address'))
            setserver = {}
            setserver['url'] = "%s://%s:%s/services/collector" % (server.get('protocol'), server.get('address'), server.get('port'))
            setserver['header'] = "Splunk %s" % server.get('key')
            logger.debug("Adding server set to pool, server: %s" % setserver)
            self.serverPool.append(setserver)


    def flush(self, q):
        logger.debug("Flush called on battlecat plugin")
        if len(q) > 0:
            try:
                payload = ""
                lastsourcetype = ""
                payloadsize = 0
                logger.debug("Currently being called with %d events" % len(q))
                for event in q:
                    logger.debug("Battlecat proccessing event: %s" % event)
                    payloadFragment = {}
                    if event.get('_raw') == None:
                        logger.error('failure outputting event, does not contain _raw')
                    else:
                        logger.debug("Event contains _raw, attempting to process...")
                        payloadFragment['event'] = event['_raw']
                        if event.get('source'):
                            logger.debug("Event contains source, adding to battlecat event")
                            payloadFragment['source'] = event['source']
                        if event.get('sourcetype'):
                            logger.debug("Event contains sourcetype, adding to battlecat event")
                            payloadFragment['sourcetype'] = event['sourcetype']
                            lastsourcetype = event['sourcetype']
                        if event.get('host'):
                            logger.debug("Event contains host, adding to battlecat event")
                            payloadFragment['host'] = event['host']
                        if event.get('_time'):
                            logger.debug("Event contains _time, adding to battlecat event")
                            payloadFragment['time'] = event['_time']
                        if event.get('index'):
                            logger.debug("Event contains index, adding to battlecat event")
                            payloadFragment['index'] = event['index']
                    logger.debug("Full payloadFragment: %s" % json.dumps(payloadFragment))
                    payload = payload + json.dumps(payloadFragment)
                targetServer = random.choice(self.serverPool)
                logger.debug("Selected targetServer object: %s" % targetServer)
                url = targetServer['url']
                headers = {}
                headers['Authorization'] = targetServer['header']
                headers['content-type'] = 'application/json'
                logger.debug("Payload created, sending it to battlecat server: %s" % url)
                try:
                    payloadsize = len(payload)
                    response = requests.post(url, data=payload, headers=headers, verify=False)
                    if not response.raise_for_status():
                        logger.debug("Payload successfully sent to battlecat server.")
                    else:
                        logger.error("Server returned an error while trying to send, response code: %s" % response.status_code)
                except Exception as e:
                    logger.error("Failed for exception: %s" % e)
                    logger.error("Failed sending events to url: %s  sourcetype: %s  size: %s" % (url, lastsourcetype, payloadsize ))
                    logger.debugv("Failed sending events to url: %s  headers: %s payload: %s" % (url, headers, payload))
            except:
                logger.error('failed indexing events')

def load():
    """Returns an instance of the plugin"""
    return BattleCatOutputPlugin
