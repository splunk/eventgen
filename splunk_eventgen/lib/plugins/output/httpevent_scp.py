"""
Custom plugin for REST API endpoint

Author: Ericsson Tsao

Ingest API
Code	Description
200	The event was sent successfully.
400	The request isn't valid.
401	The user isn't authenticated.
403	The operation is unauthorized.
404	The resource wasn't found.
422	Unprocessable entity in request.
429	Too many requests were sent.
500	An internal service error occurred.

"""

from __future__ import division

from outputplugin import OutputPlugin

from logging_config import logger
from datetime import datetime as dt
import requests
import time
import sys
import os

try:
    import ujson as json
except:
    import json

class RESTOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = 'httpevent_scp'
    MAXQUEUELENGTH = 1000

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        self.api_url = getattr(self._sample, "api_url", "https://api.playground.scp.splunk.com/botest4/ingest/v1beta2/events")

    def flush(self, events):
        # ingest events to api endpoint
        # @para events : List


        data = json.dumps(events)

	n_retry = 0

        # request data format should be a string of a JSON array 
        # e.g. [{"body" : "test1"}, {"body": "test2"}, ...]
	while True:
	    n_retry += 1
	    if n_retry > 100:
		logger.info("Have resent events over 100 times, aborting...")
		break

            headers = {
                'Authorization' : 'Bearer %s' % getattr(self._sample, "access_token"),
                'Content-Type' : "application/json"
            }

            try:
                res = requests.post(self.api_url, headers=headers, data=data, timeout=3)

    		if res.status_code != 200:
		    logger.error('status %s %s' % (res.status_code, res.text))

		    if res.status_code == 401 or res.status_code == 403:
			logger.error('authrization error!')

                    time.sleep(0.1)

		    continue
    
            except Exception as e:
                logger.error(e)
		time.sleep(0.1)
      	        logger.info("Re-ingesting events...")
		continue

 	    finally:
	        logger.debug("Successfully sent out %d events of %s" % (len(events), self._sample.name))
		break

def load():
    """Returns an instance of the plugin"""
    return RESTOutputPlugin
