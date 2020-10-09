import http.client
from collections import deque
from xml.dom import minidom

import httplib2
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.outputplugin import OutputPlugin


class SplunkStreamOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "splunkstream"
    MAXQUEUELENGTH = 100

    validSettings = [
        "splunkMethod",
        "splunkUser",
        "splunkPass",
        "splunkHost",
        "splunkPort",
    ]
    complexSettings = {"splunkMethod": ["http", "https"]}
    intSettings = ["splunkPort"]

    _splunkHost = None
    _splunkPort = None
    _splunkMethod = None
    _splunkUser = None
    _splunkPass = None
    _splunkhttp = None

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        from splunk_eventgen.lib.eventgenconfig import Config

        globals()["c"] = Config()

        (
            self._splunkUrl,
            self._splunkMethod,
            self._splunkHost,
            self._splunkPort,
        ) = c.getSplunkUrl(  # noqa: F821
            self._sample
        )
        self._splunkUser = self._sample.splunkUser
        self._splunkPass = self._sample.splunkPass

        # Cancel SSL verification
        import ssl

        ssl._create_default_https_context = ssl._create_unverified_context

        if not self._sample.sessionKey:
            try:
                myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
                logger.debug(
                    "Getting session key from '%s' with user '%s' and pass '%s'"
                    % (
                        self._splunkUrl + "/services/auth/login",
                        self._splunkUser,
                        self._splunkPass,
                    )
                )
                response = myhttp.request(
                    self._splunkUrl + "/services/auth/login",
                    "POST",
                    headers={},
                    body=six.moves.urllib.parse.urlencode(
                        {"username": self._splunkUser, "password": self._splunkPass}
                    ),
                )[1]
                self._sample.sessionKey = (
                    minidom.parseString(response)
                    .getElementsByTagName("sessionKey")[0]
                    .childNodes[0]
                    .nodeValue
                )
                logger.debug(
                    "Got new session for splunkstream, sessionKey '%s'"
                    % self._sample.sessionKey
                )
            except:
                logger.error(
                    "Error getting session key for non-SPLUNK_EMBEEDED for sample '%s'."
                    % self._sample.name
                    + " Credentials are missing or wrong"
                )
                raise IOError(
                    "Error getting session key for non-SPLUNK_EMBEEDED for sample '%s'."
                    % self._sample.name
                    + "Credentials are missing or wrong"
                )

        logger.debug(
            "Retrieved session key '%s' for Splunk session for sample %s'"
            % (self._sample.sessionKey, self._sample.name)
        )

    def flush(self, q):
        if len(q) > 0:
            # Store each source/sourcetype combo with its events so we can send them all together
            queues = {}
            for row in q:
                if row["source"] is None:
                    row["source"] = ""
                if row["sourcetype"] is None:
                    row["sourcetype"] = ""
                if not row["source"] + "_" + row["sourcetype"] in queues:
                    queues[row["source"] + "_" + row["sourcetype"]] = deque([])
                queues[row["source"] + "_" + row["sourcetype"]].append(row)

            # Iterate sub-queues, each holds events for a specific source/sourcetype combo
            for k, queue in list(queues.items()):
                if len(queue) > 0:
                    streamout = ""
                    index = source = sourcetype = host = hostRegex = None
                    metamsg = queue.popleft()
                    # We need the raw string for each event, but other data will stay the same within its own sub-queue
                    msg = metamsg["_raw"]
                    try:
                        index = metamsg["index"]
                        source = metamsg["source"]
                        sourcetype = metamsg["sourcetype"]
                        host = metamsg["host"]
                        hostRegex = metamsg["hostRegex"]
                    except KeyError:
                        pass

                    logger.debug(
                        "Flushing output for sample '%s' in app '%s' for queue '%s'"
                        % (self._sample.name, self._app, self._sample.source)
                    )
                    try:
                        if self._splunkMethod == "https":
                            connmethod = http.client.HTTPSConnection
                        else:
                            connmethod = http.client.HTTPConnection
                        splunkhttp = connmethod(self._splunkHost, self._splunkPort)
                        splunkhttp.connect()
                        urlparams = []
                        if index:
                            urlparams.append(("index", index))
                        if source:
                            urlparams.append(("source", source))
                        if sourcetype:
                            urlparams.append(("sourcetype", sourcetype))
                        if hostRegex:
                            urlparams.append(("host_regex", hostRegex))
                        if host:
                            urlparams.append(("host", host))
                        url = "/services/receivers/simple?%s" % (
                            six.moves.urllib.parse.urlencode(urlparams)
                        )
                        headers = {
                            "Authorization": "Splunk %s" % self._sample.sessionKey
                        }

                        # Iterate each raw event string in its sub-queue
                        while msg:
                            if msg[-1] != "\n":
                                msg += "\n"
                            streamout += msg
                            try:
                                msg = queue.popleft()["_raw"]
                            except IndexError:
                                msg = False

                        splunkhttp.request("POST", url, streamout, headers)
                        logger.debug(
                            "POSTing to url %s on %s://%s:%s with sessionKey %s"
                            % (
                                url,
                                self._splunkMethod,
                                self._splunkHost,
                                self._splunkPort,
                                self._sample.sessionKey,
                            )
                        )

                    except http.client.HTTPException as e:
                        logger.error(
                            'Error connecting to Splunk for logging for sample %s.  Exception "%s" Config: %s'
                            % (self._sample.name, e.args, self)
                        )
                        raise IOError(
                            "Error connecting to Splunk for logging for sample %s"
                            % self._sample
                        )

                    try:
                        response = splunkhttp.getresponse()
                        data = response.read()
                        if response.status != 200:
                            logger.error(
                                "Data not written to Splunk.  Splunk returned %s" % data
                            )
                    except http.client.BadStatusLine:
                        logger.error(
                            "Received bad status from Splunk for sample '%s'"
                            % self._sample
                        )
                    logger.debug("Closing splunkhttp connection")
                    if splunkhttp:
                        splunkhttp.close()


def load():
    """Returns an instance of the plugin"""
    return SplunkStreamOutputPlugin
