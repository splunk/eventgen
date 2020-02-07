from splunk_eventgen.lib.outputplugin import OutputPlugin
from splunk_eventgen.lib.logging_config import logger

import logging
import requests
import time
import sys
import os

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

class SCSOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = 'scsout'
    MAXQUEUELENGTH = 1000

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self.scsHttpPayloadMax = 150000 # Documentation recommends 20KB to 200KB. Going with 150KB.
        self.scsScheme = getattr(self._sample, "scsScheme", "https")
        self.scsHost = getattr(self._sample, "scsHost", "api.scp.splunk.com")
        self.scsIngestEndPoint = getattr(self._sample, "scsIngestEndPoint")
        self.scsAccessToken = getattr(self._sample, "scsAccessToken")
        self.tenant = getattr(self._sample, "scsTenant")
        self.verify = False if hasattr(self._sample, "scsInsecure") and getattr(self._sample, "scsInsecure") == "true" else True

        if not self.scsIngestEndPoint:
            raise NoSCSEndPoint("Please specify your REST endpoint (events | metrics)")

        if not self.scsAccessToken:
            raise NoSCSAccessToken("Please specify your auth access token")

        self.api_url = f'{self.scsScheme}://{self.scsHost}/{self.tenant}/ingest/v1beta2/{self.scsIngestEndPoint}'

    def _send_batch(self, events):
        data = json.dumps(events)

        n_retry = 0

        while True:
            n_retry += 1
            if n_retry > 100:
                log.info("Have retried over 100 times")
            
            headers = {
                'Authorization' : 'Bearer %s' % getattr(self._sample, "scsAccessToken"),
                'Content-Type' : "application/json"
            }

            try:
                res = requests.post(self.api_url, headers=headers, data=data, timeout=3, verify=self.verify)

                if res.status_code != 200:
                    logger.error("status %s %s" % (res.status_code, res.text))                

                    if res.status_code == 401 or res.status_code == 403:
                        logger.error("authrization issue occurs")

                    time.sleep(0.1)

                    continue

            except Exception as e:
                logger.error(e)
                continue

            finally:
                logger.debug(f"Successfully sent out {len(events)} {self.scsIngestEndPoint} of {self._sample.name}")
                break

    def flush(self, events):
        logger.info(f"Number of events: {len(events)}")

        while events:

            current_size = 0
            payload = []
            
            while events:
                current_event = events.pop()
                payload.append(current_event)
                current_size += len(current_event['body'])
                if current_size >= self.scsHttpPayloadMax:
                    logger.info(f"Sending out batch... {len(payload)} events")
                    self._send_batch(payload)
                    break
                elif not events:
                    logger.info(f"Sending out last batch... {len(payload)} events")
                    self._send_batch(payload)
                

        

def load():
    """Returns an instance of the plugin"""
    return SCSOutputPlugin