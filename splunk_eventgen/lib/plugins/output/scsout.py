from splunk_eventgen.lib.outputplugin import OutputPlugin
from splunk_eventgen.lib.logging_config import logger

import logging
import requests
import time
import sys
import os
import re
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
    listRE = re.compile(r'list(\[[^\]]+\])', re.I)

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self._payload_limit = 150000
        self._session = requests.Session()

        self.scs_scheme = getattr(self._sample, "scsScheme", "https")
        self.scs_env = getattr(self._sample, "scsEnv")
        self.scs_ingest_end_point = getattr(self._sample, "scsIngestEndPoint")
        self.tenant = getattr(self._sample, "scsTenant")
        self.attr_keys = getattr(self._sample, "attribute_keys", None)
        self._host = self._get_scs_attributes(self.scs_env)["api_url"]
        self.verify = False if hasattr(self._sample, "scsInsecure") and getattr(self._sample, "scsInsecure") == "true" else True

        if not self.scs_ingest_end_point:
            raise NoSCSIngestEndPoint("please specify your REST endpoint (events | metrics)")
        if not self.tenant:
            raise NoSCSTenant("please specify your tenant(s), be it a single value or a list")
        if not self.scs_env:
            raise NoSCSEnv("please specify the SCS environment of your tenant")

        # create an attribute key in new event dict, which takes in a line of string of keys delimited by comma
        if self.attr_keys:
            self.attr_keys = [k.strip() for k in self.attr_keys.split(',')]

        # self.api_url = f'{self.scs_scheme}://{host}/{self.tenant}/ingest/v1beta2/{self.scs_ingest_end_point}'

        tenant_list_match = self.listRE.match(self.tenant)
        if tenant_list_match:
            self.tenant = json.loads(tenant_list_match.group(1))

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

    def _ingest(self, events, tenant):
        data = json.dumps(events)
        api_url = f'{self.scs_scheme}://{self._host}/{tenant}/ingest/v1beta2/{self.scs_ingest_end_point}'

        n_retry = 0

        while True:
            try:
                res = self._session.post(api_url, data=data, timeout=360, verify=self.verify)

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

        logger.debug(f"Successfully sent out {len(events)} {self.scs_ingest_end_point} of {self._sample.name} to {tenant}")

    def flush(self, events):
        logger.debug(f"Number of events: {len(events)}")

        while events:

            current_size = 0
            payload = []
            
            while events:
                current_event = events.pop()
                current_eventbody = current_event['body']
                try:
                    current_eventbody = json.loads(current_eventbody)
                    current_event['body'] = current_eventbody
                except ValueError:
                    pass

                if self.attr_keys:
                    # event_dict = json.loads(current_event['body'])
                    temp_dict = dict()
                    for k in self.attr_keys:
                        if k in current_eventbody:
                            temp_dict[k] = current_eventbody[k]
                    # current_event["attributes"] = json.dumps({k: event_dict[k] for k in self.attr_keys})
                    current_event["attributes"] = temp_dict
                    # current_event['body'] = event_dict
                    # current_event['body'] = current_event['body'].strip("\n") # strip newline
                # print(current_event)
                payload.append(current_event)
                current_size += len(json.dumps(current_event))
                if not events:
                    logger.debug(f"Sending out last batch... {len(payload)} events")
                    if isinstance(self.tenant, list):
                        with ThreadPoolExecutor(max_workers=len(self.tenant)) as executor:
                            for tenant in self.tenant:
                                executor.submit(self._ingest, payload, tenant)
                    else:
                        self._ingest(payload, self.tenant)
                        
                if current_size >= self._payload_limit:
                    logger.debug(f"Sending out batch... {len(payload)} events")
                    if isinstance(self.tenant, list):
                        with ThreadPoolExecutor(max_workers=len(self.tenant)) as executor:
                            for tenant in self.tenant:
                                executor.submit(self._ingest, payload, tenant)
                    else:
                        self._ingest(payload, self.tenant)

                    break
                
def load():
    """Returns an instance of the plugin"""
    return SCSOutputPlugin