import random

import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.outputplugin import OutputPlugin

try:
    from concurrent.futures import ThreadPoolExecutor

    import requests
    from requests import Session
    from requests_futures.sessions import FuturesSession

except ImportError:
    pass
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


class HTTPCoreOutputPlugin(OutputPlugin):
    name = "httpcore"
    MAXQUEUELENGTH = 1000
    useOutputQueue = False
    validSettings = [
        "httpeventServers",
        "httpeventOutputMode",
        "httpeventMaxPayloadSize",
    ]
    defaultableSettings = [
        "httpeventServers",
        "httpeventOutputMode",
        "httpeventMaxPayloadSize",
    ]
    jsonSettings = ["httpeventServers"]

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

    # TODO: make workers a param that can be set in eventgen.conf
    def _setup_REST_workers(self, session=None, workers=20):
        # disable any "requests" warnings
        requests.packages.urllib3.disable_warnings()
        # Bind passed in samples to the outputter.
        self.lastsourcetype = None
        if not session:
            session = Session()
        self.session = FuturesSession(
            session=session, executor=ThreadPoolExecutor(max_workers=workers)
        )
        self.active_sessions = []

    @staticmethod
    def _urlencode(value):
        """
        Takes a value and make sure everything int he string is URL safe.
        :param value: string
        :return: urlencoded string
        """
        return six.moves.urllib.parse.quote(value)

    @staticmethod
    def _bg_convert_json(sess, resp):
        """
        Takes a futures session object, and sets the data to a parsed json output. Use this as a background task for the
        session queue. Example: future = session.get('http://httpbin.org/get', background_callback=_bg_convert_json)
        :param sess: futures session object. Automatically called on a background_callback as aruguments.
        :param resp: futures resp object.  Automatically called on a background_callback as aruguments.
        :return:
        """
        if resp.status_code == 200:
            if getattr(resp, "json", None):
                resp.data = resp.json()
            else:
                if type(resp.data) == str:
                    resp.data = json.loads(resp.data)

    def updateConfig(self, config):
        OutputPlugin.updateConfig(self, config)
        try:
            if hasattr(self.config, "httpeventServers") is False:
                if hasattr(self._sample, "httpeventServers"):
                    self.config.httpeventServers = self._sample.httpeventServers
                else:
                    logger.error(
                        "outputMode %s but httpeventServers not specified for sample %s"
                        % (self.name, self._sample.name)
                    )
                    raise NoServers(
                        "outputMode %s but httpeventServers not specified for sample %s"
                        % (self.name, self._sample.name)
                    )
            # set default output mode to round robin
            if (
                hasattr(self.config, "httpeventOutputMode")
                and self.config.httpeventOutputMode
            ):
                self.httpeventoutputmode = config.httpeventOutputMode
            else:
                if (
                    hasattr(self._sample, "httpeventOutputMode")
                    and self._sample.httpeventOutputMode
                ):
                    self.httpeventoutputmode = self._sample.httpeventOutputMode
                else:
                    self.httpeventoutputmode = "roundrobin"
            if (
                hasattr(self.config, "httpeventMaxPayloadSize")
                and self.config.httpeventMaxPayloadSize
            ):
                self.httpeventmaxsize = self.config.httpeventMaxPayloadSize
            else:
                if (
                    hasattr(self._sample, "httpeventMaxPayloadSize")
                    and self._sample.httpeventMaxPayloadSize
                ):
                    self.httpeventmaxsize = self._sample.httpeventMaxPayloadSize
                else:
                    self.httpeventmaxsize = 10000
            logger.debug("Currentmax size: %s " % self.httpeventmaxsize)
            if isinstance(config.httpeventServers, str):
                self.httpeventServers = json.loads(config.httpeventServers)
            else:
                self.httpeventServers = config.httpeventServers
            logger.debug(
                "Setting up the connection pool for %s in %s"
                % (self._sample.name, self._app)
            )
            self.createConnections()
            logger.debug("Pool created.")
            logger.debug("Finished init of %s plugin." % self.name)
        except Exception as e:
            logger.exception(str(e))

    def createConnections(self):
        self.serverPool = []
        if self.httpeventServers:
            for server in self.httpeventServers.get("servers"):
                if not server.get("address"):
                    logger.error(
                        "requested a connection to a httpevent server, but no address specified for sample %s"
                        % self._sample.name
                    )
                    raise ValueError(
                        "requested a connection to a httpevent server, but no address specified for sample %s"
                        % self._sample.name
                    )
                if not server.get("port"):
                    logger.error(
                        "requested a connection to a httpevent server, but no port specified for server %s"
                        % server
                    )
                    raise ValueError(
                        "requested a connection to a httpevent server, but no port specified for server %s"
                        % server
                    )
                if not server.get("key"):
                    logger.error(
                        "requested a connection to a httpevent server, but no key specified for server %s"
                        % server
                    )
                    raise ValueError(
                        "requested a connection to a httpevent server, but no key specified for server %s"
                        % server
                    )
                if not (
                    (server.get("protocol") == "http")
                    or (server.get("protocol") == "https")
                ):
                    logger.error(
                        "requested a connection to a httpevent server, but no protocol specified for server %s"
                        % server
                    )
                    raise ValueError(
                        "requested a connection to a httpevent server, but no protocol specified for server %s"
                        % server
                    )
                logger.debug(
                    "Validation Passed, Creating a requests object for server: %s"
                    % server.get("address")
                )

                setserver = {}
                setserver["url"] = "%s://%s:%s/services/collector" % (
                    server.get("protocol"),
                    server.get("address"),
                    server.get("port"),
                )
                setserver["header"] = "Splunk %s" % server.get("key")
                logger.debug("Adding server set to pool, server: %s" % setserver)
                self.serverPool.append(setserver)
        else:
            raise NoServers(
                "outputMode %s but httpeventServers not specified for sample %s"
                % (self.name, self._sample.name)
            )

    def _sendHTTPEvents(self, payload):
        currentreadsize = 0
        stringpayload = ""
        totalbytesexpected = 0
        totalbytessent = 0
        numberevents = len(payload)
        logger.debug("Sending %s events to splunk" % numberevents)
        for line in payload:
            logger.debug("line: %s " % line)
            targetline = json.dumps(line)
            logger.debug("targetline: %s " % targetline)
            targetlinesize = len(targetline)
            totalbytesexpected += targetlinesize
            if (int(currentreadsize) + int(targetlinesize)) <= int(
                self.httpeventmaxsize
            ):
                stringpayload = stringpayload + targetline
                currentreadsize = currentreadsize + targetlinesize
                logger.debug("stringpayload: %s " % stringpayload)
            else:
                logger.debug(
                    "Max size for payload hit, sending to splunk then continuing."
                )
                try:
                    self._transmitEvents(stringpayload)
                    totalbytessent += len(stringpayload)
                    currentreadsize = targetlinesize
                    stringpayload = targetline
                except Exception as e:
                    logger.exception(str(e))
                    raise e
        else:
            try:
                totalbytessent += len(stringpayload)
                logger.debug(
                    "End of for loop hit for sending events to splunk, total bytes sent: %s ---- out of %s -----"
                    % (totalbytessent, totalbytesexpected)
                )
                self._transmitEvents(stringpayload)
            except Exception as e:
                logger.exception(str(e))
                raise e

    def _transmitEvents(self, payloadstring):
        targetServer = []
        logger.debug("Transmission called with payloadstring: %s " % payloadstring)
        if self.httpeventoutputmode == "mirror":
            targetServer = self.serverPool
        else:
            targetServer.append(random.choice(self.serverPool))
        for server in targetServer:
            logger.debug("Selected targetServer object: %s" % targetServer)
            url = server["url"]
            headers = {}
            headers["Authorization"] = server["header"]
            headers["content-type"] = "application/json"
            try:
                payloadsize = len(payloadstring)
                self.active_sessions.append(
                    self.session.post(
                        url=url, data=payloadstring, headers=headers, verify=False
                    )
                )
            except Exception as e:
                logger.error("Failed for exception: %s" % e)
                logger.error(
                    "Failed sending events to url: %s  sourcetype: %s  size: %s"
                    % (url, self.lastsourcetype, payloadsize)
                )
                logger.debug(
                    "Failed sending events to url: %s  headers: %s payload: %s"
                    % (url, headers, payloadstring)
                )
                raise e


def load():
    """Returns an instance of the plugin"""
    return HTTPCoreOutputPlugin
