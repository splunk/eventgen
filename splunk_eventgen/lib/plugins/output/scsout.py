from concurrent.futures import ThreadPoolExecutor

import requests
from requests import Session
from requests_futures.sessions import FuturesSession

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.outputplugin import OutputPlugin

try:
    import ujson as json
except:
    import json


class NoSCSEndPoint(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class NoSCSAccessToken(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class SCSOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "scsout"
    MAXQUEUELENGTH = 1000

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self.scsHttpPayloadMax = (
            150000  # Documentation recommends 20KB to 200KB. Going with 150KB.
        )
        self.scsEndPoint = getattr(self._sample, "scsEndPoint", None)
        self.scsAccessToken = getattr(self._sample, "scsAccessToken", None)
        self.scsClientId = getattr(self._sample, "scsClientId", "")
        self.scsClientSecret = getattr(self._sample, "scsClientSecret", "")
        self.scsRetryNum = int(
            getattr(self._sample, "scsRetryNum", 0)
        )  # By default, retry num is 0

        self._setup_REST_workers()

    def _setup_REST_workers(self, session=None, workers=10):
        # disable any "requests" warnings
        requests.packages.urllib3.disable_warnings()
        # Bind passed in samples to the outputter.
        if not session:
            session = Session()
        self.session = FuturesSession(
            session=session, executor=ThreadPoolExecutor(max_workers=workers)
        )
        self.active_sessions = []

    def flush(self, events):
        if not self.scsEndPoint:
            if getattr(self.config, "scsEndPoint", None):
                self.scsEndPoint = self.config.scsEndPoint
            else:
                raise NoSCSEndPoint(
                    "Please specify your REST endpoint for the SCS tenant"
                )

        if not self.scsAccessToken:
            if getattr(self.config, "scsAccessToken", None):
                self.scsAccessToken = self.config.scsAccessToken
            else:
                raise NoSCSAccessToken(
                    "Please specify your REST endpoint access token for the SCS tenant"
                )

        if self.scsClientId and self.scsClientSecret:
            logger.info(
                "Both scsClientId and scsClientSecret are supplied."
                + " We will renew the expired token using these credentials."
            )
            self.scsRenewToken = True
        else:
            if getattr(self.config, "scsClientId", None) and getattr(
                self.config, "scsClientSecret", None
            ):
                self.scsClientId = self.config.scsClientId
                self.scsClientSecret = self.config.scsClientSecret
                logger.info(
                    "Both scsClientId and scsClientSecret are supplied."
                    + " We will renew the expired token using these credentials."
                )
                self.scsRenewToken = True
            else:
                self.scsRenewToken = False

        self.header = {
            "Authorization": "Bearer {0}".format(self.scsAccessToken),
            "Content-Type": "application/json",
        }

        self.accessTokenExpired = False
        self.tokenRenewEndPoint = "https://auth.scp.splunk.com/token"
        self.tokenRenewBody = {
            "client_id": self.scsClientId,
            "client_secret": self.scsClientSecret,
            "grant_type": "client_credentials",
        }

        for i in range(self.scsRetryNum + 1):
            logger.debug("Sending data to the scs endpoint. Num:{0}".format(i))
            self._sendHTTPEvents(events)

            if not self.checkResults():
                if self.accessTokenExpired and self.scsRenewToken:
                    self.renewAccessToken()
                self.active_sessions = []
            else:
                break

    def checkResults(self):
        for session in self.active_sessions:
            response = session.result()
            if (
                response.status_code == 401
                and "Invalid or Expired Bearer Token" in response.text
            ):
                logger.error("scsAccessToken is invalid or expired")
                self.accessTokenExpired = True
                return False
            elif response.status_code != 200:
                logger.error(
                    "Data transmisison failed with {0} and {1}".format(
                        response.status_code, response.text
                    )
                )
                return False
        logger.debug("Data transmission successful")
        return True

    def renewAccessToken(self):
        response = requests.post(
            self.tokenRenewEndPoint, data=self.tokenRenewBody, timeout=5
        )
        if response.status_code == 200:
            logger.info("Renewal of the access token succesful")
            self.scsAccessToken = response.json()["access_token"]
            setattr(self._sample, "scsAccessToken", self.scsAccessToken)
            self.accessTokenExpired = False
        else:
            logger.error("Renewal of the access token failed")

    def _sendHTTPEvents(self, events):
        currentPayloadSize = 0
        currentPayload = []
        try:
            for event in events:
                # Reformat the event to fit the scs request spec
                # TODO: Move this logic to generator
                try:
                    event["body"] = event.pop("_raw")
                    event["timestamp"] = int(event.pop("_time") * 1000)
                    event.pop("index")
                    if "attributes" not in event:
                        event["attributes"] = {}
                        event["attributes"]["hostRegex"] = event.pop("hostRegex")
                except:
                    pass

                targetline = json.dumps(event)
                targetlinesize = len(targetline)

                # Continue building a current payload if the payload is less than the max size
                if (currentPayloadSize + targetlinesize) < self.scsHttpPayloadMax:
                    currentPayload.append(event)
                    currentPayloadSize += targetlinesize
                else:
                    self.active_sessions.append(
                        self.session.post(
                            url=self.scsEndPoint,
                            data=json.dumps(currentPayload),
                            headers=self.header,
                            verify=False,
                        )
                    )
                    currentPayloadSize = targetlinesize
                    currentPayload = [event]

            # Final flush of the leftover events
            if currentPayloadSize > 0:
                self.active_sessions.append(
                    self.session.post(
                        url=self.scsEndPoint,
                        data=json.dumps(currentPayload),
                        headers=self.header,
                        verify=False,
                    )
                )

        except Exception as e:
            logger.exception(str(e))
            raise e


def load():
    """Returns an instance of the plugin"""
    return SCSOutputPlugin
