from splunk_eventgen.lib.outputplugin import OutputPlugin
from splunk_eventgen.lib.logging_config import logger

import logging
import requests
import time
import sys
import os

import requests
from requests import Session
from requests_futures.sessions import FuturesSession
from concurrent.futures import ThreadPoolExecutor

try:
    import ujson as json
except:
    import json

class NoSCPEndPoint(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class NoSCPAccessToken(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class SCPOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = 'scpout'
    MAXQUEUELENGTH = 1000

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self.scpHttpPayloadMax = 150000 # Documentation recommends 20KB to 200KB. Going with 150KB.
        self.scpEndPoint = getattr(self._sample, "scpEndPoint", None)
        self.scpAccessToken = getattr(self._sample, "scpAccessToken", None)
        self.scpClientId = getattr(self._sample, 'scpClientId', '')
        self.scpClientSecret = getattr(self._sample, 'scpClientSecret', '')
        self.scpRetryNum = int(getattr(self._sample, 'scpRetryNum', 0)) # By default, retry num is 0

        if not self.scpEndPoint:
            raise NoSCPEndPoint("Please specify your REST endpoint for the SCP tenant")

        if not self.scpAccessToken:
            raise NoSCPAccessToken("Please specify your REST endpoint access token for the SCP tenant")

        if self.scpClientId and self.scpClientSecret:
            logger.info("Both scpClientId and scpClientSecret are supplied. We will renew the expired token using these credentials.")
            self.scpRenewToken = True
        else:
            self.scpRenewToken = False

        self.header = {
            "Authorization": f"Bearer {self.scpAccessToken}",
            "Content-Type": "application/json"
        }

        self.accessTokenExpired = False
        self.tokenRenewEndPoint = "https://auth.scp.splunk.com/token"
        self.tokenRenewBody = {
            "client_id": self.scpClientId,
            "client_secret": self.scpClientSecret,
            "grant_type": "client_credentials"
        }

        self._setup_REST_workers()
    
    def _setup_REST_workers(self, session=None, workers=10):
        # disable any "requests" warnings
        requests.packages.urllib3.disable_warnings()
        # Bind passed in samples to the outputter.
        if not session:
            session = Session()
        self.session = FuturesSession(session=session, executor=ThreadPoolExecutor(max_workers=workers))
        self.active_sessions = []

    def flush(self, events):
        for i in range(self.scpRetryNum + 1):
            logger.debug(f"Sending data to the scp endpoint. Num:{i}")
            self._sendHTTPEvents(events)

            if not self.checkResults():
                if self.accessTokenExpired and self.scpRenewToken:
                    self.renewAccessToken()
                self.active_sessions = []
            else:
                break
                
    def checkResults(self):
        for session in self.active_sessions:
            response = session.result()
            if response.status_code == 401 and "Invalid or Expired Bearer Token" in response.text:
                logger.error("scpAccessToken is invalid or expired")
                self.accessTokenExpired = True
                return False
            elif response.status_code != 200:
                logger.error(f"Data transmisison failed with {response.status_code} and {response.text}")
                return False
        logger.debug(f"Data transmission successful")
        return True
    
    def renewAccessToken(self):
        response = requests.post(self.tokenRenewEndPoint, data=self.tokenRenewBody, timeout=5)
        if response.status_code == 200:
            logger.info("Renewal of the access token succesful")
            self.scpAccessToken = response.json()["access_token"]
            setattr(self._sample, "scpAccessToken", self.scpAccessToken)
            self.accessTokenExpired = False
        else:
            logger.error("Renewal of the access token failed")

    def _sendHTTPEvents(self, events):
        currentPayloadSize = 0
        currentPayload = []
        try:
            for event in events:
                # Reformat the event to fit the scp request spec
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
                if (currentPayloadSize + targetlinesize) < self.scpHttpPayloadMax:
                    currentPayload.append(event)
                    currentPayloadSize += targetlinesize
                else:
                    self.active_sessions.append(self.session.post(url=self.scpEndPoint, data=json.dumps(currentPayload), headers=self.header, verify=False))
                    currentPayloadSize = targetlinesize
                    currentPayload = [event]
            
            # Final flush of the leftover events
            if currentPayloadSize > 0:
                self.active_sessions.append(self.session.post(url=self.scpEndPoint, data=json.dumps(currentPayload), headers=self.header, verify=False))

        except Exception as e:
            logger.exception(str(e))
            raise e


def load():
    """Returns an instance of the plugin"""
    return SCPOutputPlugin