"""
Output plugin for SCP REST endpoint

Author: Ericsson(Che-Lun) Tsao from Performance Engineering (ctsao@splunk.com)

[README]
In the global section of configuration file, one has to specify client credentials(in json format) and auth api
=> client_credentials = {"client_id" : "***************","client_secret" : "*************","grant_type" : "client_credentials"}
=> auth_url = https://auth.playground.scp.splunk.com/token

As for stanza section, api url has to be specified, e.g...
=> generator = scpgen
=> outputMode = httpevent_scp
=> api_url = https://api.playground.scp.splunk.com/mytenant/ingest/v1beta2/events
"""

from __future__ import division

from outputplugin import OutputPlugin

import logging
import requests
import time
import sys
import os

from logging_config import logger

try:
    import ujson as json
except:
    import json

class NoAPIEndpoint(Exception):
    pass

class RESTOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = 'httpevent_scp'
    MAXQUEUELENGTH = 1000

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self.api_url = getattr(self._sample, "api_url")

        if self.api_url is None:
            raise NoAPIEndpoint("Please speccify your REST endpoint of SCP")

    def flush(self, events):
        """
        :param events: a list of multiple payloads, format of payload refers to "temp_event" of "lib/plugin/generator/scpgenplugin.py"
        """

        data = json.dumps(events) # A JSON array per SCP ingest API requirement

        n_retry = 0

        while True:
            n_retry += 1
            if n_retry > 100:
                logger.info("Have been resending events over 100 times, now exiting...")
                break

            headers = {
                'Authorization' : 'Bearer %s' % getattr(self._sample, "access_token"),
                'Content-Type' : "application/json"
            }

            try:
                res = requests.post(self.api_url, headers=headers, data=data, timeout=3)

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
                logger.debug("Successfully sent out %d events of %s" % (len(events), self._sample.name))
                break


def load():
    """Returns an instance of the plugin"""
    return RESTOutputPlugin
