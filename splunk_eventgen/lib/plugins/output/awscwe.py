from splunk_eventgen.lib.outputplugin import OutputPlugin
from splunk_eventgen.lib.logging_config import logger
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import boto3
import time
import json
import logging

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('nose').setLevel(logging.WARNING)

class AWSCloudWatchEventOutOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "awscwe"
    MAXQUEUELENGTH = 10000
    MAXBATCHLENGTH = 10

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        access_key = getattr(self._sample, "awsAccessKey", None)
        secret_access_key = getattr(self._sample, "awsSecretAccessKey", None)
        aws_region = getattr(self._sample, "awsRegion", None)

        if access_key is None or secret_access_key is None or aws_region is None:
            logger.error("Please specify the correct awsAccessKey/awsSecretAccessKey/awsRegion")

        self.boto_client = boto3.client("events", aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, region_name=aws_region)
        
    def send_events(self, events):
        try:
            self.boto_client.put_events(Entries=events)
        except Exception as e:
            logger.error(e)

    def flush(self, q):
        events = []
        for x in q:
            event = {
                'Source': x['source'],
                'Resources': [],
                'DetailType': x['sourcetype'],
                'Detail': x['_raw'],
                'EventBusName': 'default'
            }

            events.append(event)

            if (len(events) == self.MAXBATCHLENGTH):
                self.send_events(events)
                events = []
                
        if events:
            self.send_events(events)


def load():
    """Returns an instance of the plugin"""
    return AWSCloudWatchEventOutOutputPlugin
