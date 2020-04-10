from splunk_eventgen.lib.outputplugin import OutputPlugin
from splunk_eventgen.lib.logging_config import logger

import logging
import requests
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor

try:
    import ujson as json
except:
    import json

class NoSCSIngestEndPoint(Exception):
    pass

class NoSCSAccessToken(Exception):
    pass

class NoSCSTenant(Exception):
    pass

class NoClientCredentials(Exception):
    pass

class NoSCSEnv(Exception):
    pass

class SCSOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = 'scsout'
    MAXQUEUELENGTH = 1000

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self._payload_limit = 150000 
        self.scs_scheme = getattr(self._sample, "scsScheme", "https")
        self.scs_env = getattr(self._sample, "scsEnv")
        self.scs_ingest_end_point = getattr(self._sample, "scsIngestEndPoint")
        self.tenant = getattr(self._sample, "scsTenant")
        self.verify = False if hasattr(self._sample, "scsInsecure") and getattr(self._sample, "scsInsecure") == "true" else True

        if not self.scs_ingest_end_point:
            raise NoSCSEndPoint("please specify your REST endpoint (events | metrics)")
        if not self.tenant:
            raise NoSCSTenant("please specify your tenant name")
        # if not self.scs_env:
        #     raise NoSCSEnv("please specify the SCS environment of your tenant")

        host = self._get_scs_attributes(self.scs_env)["api_url"]
        self.api_url = f'{self.scs_scheme}://{host}/{self.tenant}/ingest/v1beta2/{self.scs_ingest_end_point}'

        self._session = requests.Session()

        self._update_session()

    def _update_session(self):

        self._session.headers.update({
            'Content-Type' : "application/json",
            "Authorization": f"Bearer {self._sample.scsAccessToken}"
        })

    def _get_scs_attributes(self, scs_env):
        """
        return a dict of scs attributes according to scs env
        """
        if scs_env == "play":
            return {
                "k8s_index": "k8s_dev",
                "auth_url": "auth.playground.scp.splunk.com",
                "api_url": "api.playground.scp.splunk.com"
            }
        elif scs_env == "stage":
            return {
                "k8s_index": "k8s_stage",
                "auth_url": "auth.staging.scp.splunk.com",
                "api_url": "api.staging.scp.splunk.com"
            }
        elif scs_env == "prod":
            return {
                "k8s_index": "k8s_prod",
                "auth_url": "auth.scp.splunk.com",
                "api_url": "api.scp.splunk.com"
            }
        else:
            raise KeyError("scs_env only takes play | stage | prod")

    def _ingest(self, events):
        data = json.dumps(events)

        n_retry = 0

        while True:
            try:
                res = self._session.post(self.api_url, data=data, timeout=60, verify=self.verify)

                if res.status_code != 200:
                    logger.error("status %s %s" % (res.status_code, res.text))
                    if res.status_code == 401:
                        self._update_session()

                    continue

                break

            except Exception as e:
                logger.error(e)
                time.sleep(600)
                continue

        logger.debug(f"Successfully sent out {len(events)} {self.scs_ingest_end_point} of {self._sample.name}")

    def flush(self, events):
        logger.debug(f"Number of events: {len(events)}")

        with ThreadPoolExecutor(max_workers=5) as executor:

            while events:

                current_size = 0
                payload = []
                
                while events:
                    current_event = events.pop()
                    payload.append(current_event)
                    current_size += len(json.dumps(current_event))
                    if not events:
                        logger.debug(f"Sending out last batch... {len(payload)} events")
                        # self._ingest(payload)
                        executor.submit(self._ingest, payload)
                    if current_size >= self._payload_limit:
                        logger.debug(f"Sending out batch... {len(payload)} events")
                        # self._ingest(payload)
                        executor.submit(self._ingest, payload)
                        break
                
def load():
    """Returns an instance of the plugin"""
    return SCSOutputPlugin