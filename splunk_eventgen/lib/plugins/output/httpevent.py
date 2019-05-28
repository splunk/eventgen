from __future__ import division

from httpevent_core import HTTPCoreOutputPlugin

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


class HTTPEventOutputPlugin(HTTPCoreOutputPlugin):
    '''
    HTTPEvent output will enable events that are generated to be sent directly
    to splunk through the HTTP event input.  In order to use this output plugin,
    you will need to supply an attribute 'httpeventServers' as a valid json object.
    this json object should look like the following:

    {servers:[{ protocol:http/https, address:127.0.0.1, port:8088, key:12345-12345-123123123123123123}]}
    '''
    name = 'httpevent'
    def __init__(self, sample, output_counter=None):
        super(HTTPEventOutputPlugin,self).__init__(sample,output_counter)

    def flush(self, q):
        self.logger.debug("Flush called on httpevent plugin")
        self._setup_REST_workers()
        if len(q) > 0:
            try:
                payload = []
                self.logger.debug("Currently being called with %d events" % len(q))
                for event in q:
                    self.logger.debug("HTTPEvent proccessing event: %s" % event)
                    payloadFragment = {}
                    if event.get('_raw') is None or event['_raw'] == "\n":
                        self.logger.error('failure outputting event, does not contain _raw')
                    else:
                        self.logger.debug("Event contains _raw, attempting to process...")
                        payloadFragment['event'] = event['_raw']
                        if event.get('source'):
                            self.logger.debug("Event contains source, adding to httpevent event")
                            payloadFragment['source'] = event['source']
                        if event.get('sourcetype'):
                            self.logger.debug("Event contains sourcetype, adding to httpevent event")
                            payloadFragment['sourcetype'] = event['sourcetype']
                            self.lastsourcetype = event['sourcetype']
                        if event.get('host'):
                            self.logger.debug("Event contains host, adding to httpevent event")
                            payloadFragment['host'] = event['host']
                        if event.get('_time'):
                            # make sure _time can be an epoch timestamp
                            try:
                                float(event.get("_time"))
                                self.logger.debug("Event contains _time, adding to httpevent event")
                                payloadFragment['time'] = event['_time']
                            except:
                                self.logger.error("Timestamp not in epoch format, ignoring event: {0}".format(event))
                        if event.get('index'):
                            self.logger.debug("Event contains index, adding to httpevent event")
                            payloadFragment['index'] = event['index']
                    self.logger.debug("Full payloadFragment: %s" % json.dumps(payloadFragment))
                    payload.append(payloadFragment)
                self.logger.debug("Finished processing events, sending all to splunk")
                self._sendHTTPEvents(payload)
                if self.config.httpeventWaitResponse:
                    for session in self.active_sessions:
                        response = session.result()
                        if not response.raise_for_status():
                            self.logger.debug("Payload successfully sent to httpevent server.")
                        else:
                            self.logger.error("Server returned an error while trying to send, response code: %s" %
                                              response.status_code)
                            raise BadConnection(
                                "Server returned an error while sending, response code: %s" % response.status_code)
                else:
                    self.logger.debug("Ignoring response from HTTP server, leaving httpevent outputter")
            except Exception as e:
                self.logger.error('failed indexing events, reason: %s ' % e)


def load():
    """Returns an instance of the plugin"""
    return HTTPEventOutputPlugin
