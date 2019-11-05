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

import logging
import requests
from datetime import datetime as dt
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

	self.f = open("/root/test-eventgen/logs/output_%s" % (os.getpid()), 'a+')

    def flush(self, events):
        # ingest events to api endpoint
        # @para events : List

        headers = {
            'Authorization' : 'Bearer %s' % getattr(self._sample, "access_token"),
            'Content-Type' : "application/json"
        }

        data = json.dumps(events)

        # request data format should be a string of a JSON array 
        # e.g. [{"body" : "test1"}, {"body": "test2"}, ...]
	while True:
            try:
                res = requests.post(self.api_url, headers=headers, data=data, timeout=3)
    
                while res.status_code != 200:
                    start_time = time.time()
                    #logger.error("status %s %s\n" % (res.status_code, res.text))                
		    self.f.write("%s status %s %s\n" % (dt.now(), res.status_code, res.text))
                    #if res.status_code != 429 and res.status_code != 500:
                    # skip errors that caused by too many requests and internal server error
                        #logger.error("status %s %s\n" % (res.status_code, res.text))
                        # sys.exit()
                        # self._stop(force_stop=True)
                    if res.status_code == 401 or res.status_code == 403:
                        #logger.error("authrization issue occurs")
			self.f.write("%s authrization issue occurs\n" % dt.now())
    
                    time.sleep(0.1)
    
                    res = requests.post(
                            self.api_url, 
                            headers={
                                'Authorization' : 'Bearer %s' % getattr(self._sample, "access_token"),
                            'Content-Type' : "application/json"
                            }, 
                            data=data,
			    timeout=3
                        )
	    
            except Exception as e:
                #logger.error(e)
		time.sleep(0.1)
      	        #logger.info("Re-ingesting events...")
		self.f.write("%s Connection Error: %s\n" % (dt.now(), e))
		countinue
 	    finally:
	        #logger.debug("Writting events locally...")
		"""
	        for event in events:
		    if event.get('body') is None or event['body'] == '\n':
			#logger.error("No body!?!?")
		    #logger.debug(event)
		"""
	        #logger.info("Successfully sent out %d events of %s" % (len(events), self._sample.name))
		self.f.write("%s Successfully sent out %d events of %s\n" % (dt.now(), len(events), self._sample.name))
		self.f.close()
		break

def load():
    """Returns an instance of the plugin"""
    return RESTOutputPlugin
