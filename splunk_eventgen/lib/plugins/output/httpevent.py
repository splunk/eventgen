from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.plugins.output.httpevent_core import HTTPCoreOutputPlugin

try:
    import ujson as json
except ImportError:
    import json


class NoServers(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class BadConnection(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class HTTPEventOutputPlugin(HTTPCoreOutputPlugin):
    """
    HTTPEvent output will enable events that are generated to be sent directly
    to splunk through the HTTP event input.  In order to use this output plugin,
    you will need to supply an attribute 'httpeventServers' as a valid json object.
    this json object should look like the following:
    {servers:[{ protocol:http/https, address:127.0.0.1, port:8088, key:12345-12345-123123123123123123}]}
    """

    name = "httpevent"

    def __init__(self, sample, output_counter=None):
        super(HTTPEventOutputPlugin, self).__init__(sample, output_counter)

    def flush(self, q):
        logger.debug("Flush called on httpevent plugin")
        self._setup_REST_workers()
        if len(q) > 0:
            try:
                payload = []
                logger.debug("Currently being called with %d events" % len(q))
                for event in q:
                    logger.debug("HTTPEvent proccessing event: %s" % event)
                    payloadFragment = {}
                    if event.get("_raw") is None or event["_raw"] == "\n":
                        logger.error("failure outputting event, does not contain _raw")
                    else:
                        logger.debug("Event contains _raw, attempting to process...")
                        payloadFragment["event"] = event["_raw"]
                        if event.get("source"):
                            logger.debug(
                                "Event contains source, adding to httpevent event"
                            )
                            payloadFragment["source"] = event["source"]
                        if event.get("sourcetype"):
                            logger.debug(
                                "Event contains sourcetype, adding to httpevent event"
                            )
                            payloadFragment["sourcetype"] = event["sourcetype"]
                            self.lastsourcetype = event["sourcetype"]
                        if event.get("host"):
                            logger.debug(
                                "Event contains host, adding to httpevent event"
                            )
                            payloadFragment["host"] = event["host"]
                        if event.get("_time"):
                            # make sure _time can be an epoch timestamp
                            try:
                                float(event.get("_time"))
                                logger.debug(
                                    "Event contains _time, adding to httpevent event"
                                )
                                payloadFragment["time"] = event["_time"]
                            except:
                                logger.error(
                                    "Timestamp not in epoch format, ignoring event: {0}".format(
                                        event
                                    )
                                )
                        if event.get("index"):
                            logger.debug(
                                "Event contains index, adding to httpevent event"
                            )
                            payloadFragment["index"] = event["index"]
                    logger.debug(
                        "Full payloadFragment: %s" % json.dumps(payloadFragment)
                    )
                    payload.append(payloadFragment)
                logger.debug("Finished processing events, sending all to splunk")
                self._sendHTTPEvents(payload)
                payload = []
                if self.config.httpeventWaitResponse:
                    for session in self.active_sessions:
                        response = session.result()
                        if not response.raise_for_status():
                            logger.debug(
                                "Payload successfully sent to httpevent server."
                            )
                        else:
                            logger.error(
                                "Server returned an error while trying to send, response code: %s"
                                % response.status_code
                            )
                            raise BadConnection(
                                "Server returned an error while sending, response code: %s"
                                % response.status_code
                            )
                else:
                    logger.debug(
                        "Ignoring response from HTTP server, leaving httpevent outputter"
                    )
            except Exception as e:
                logger.error("failed indexing events, reason: %s " % e)


def load():
    """Returns an instance of the plugin"""
    return HTTPEventOutputPlugin
