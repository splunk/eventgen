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
        
        self.aws_credentials = self._get_aws_credentials()
        self.clients = self._create_boto_clients()

    def _get_aws_credentials(self):
        path = getattr(self._sample, "awsCredentialsJson")
        try:
            path = Path(path)
        except Exception as e:
            logger.error(e)

        with open(path) as f:
            aws_credentials = json.load(f)

        return aws_credentials

    def _create_boto_clients(self):
        """
        Return: A list of boto logs clients
        """
        boto_clients = []
        for acct in self.aws_credentials:
            awscwe = acct.get("awscwe")
            if not awscwe or ("regions" not in awscwe):
                logger.error("No awscwe-related info provided or incomplete")
                sys.exit(1)
            regions = awscwe.get("regions")
            for region in regions:
                client = boto3.client("events", aws_access_key_id=acct['access_key'], aws_secret_access_key=acct['secret_access_key'], region_name=region)
                boto_clients.append(client)

        return boto_clients

    def target_process(self, client, events):
        try:
            response = client.put_events(Entries=events)
        except Exception as e:
            logger.error(e)
        else:
            logger.debug(response)

    def send_events(self, events):
        n_clients = len(self.clients)

        if n_clients > 1:
            with ThreadPoolExecutor(max_workers=n_clients) as executor:
                for client in self.clients:
                    executor.submit(self.target_process, client=client, events=events)
        else:
            self.target_process(client=self.clients[0], events=events)

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
