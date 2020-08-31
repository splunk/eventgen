from splunk_eventgen.lib.outputplugin import OutputPlugin
from splunk_eventgen.lib.logging_config import logger
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import boto3
import time
import re
import json

class AWSCloudWatchLogOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "awscwl"
    MAXQUEUELENGTH = 10000
    MAXBATCHBYTES = 1048576

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)
        self.aws_log_group_name = getattr(self._sample, "awsLogGroupName")
        self.aws_log_stream_name = getattr(self._sample, "awsLogStreamName")
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
            for region in acct['regions']:
                client = boto3.client("logs", aws_access_key_id=acct['access_key'], aws_secret_access_key=acct['secret_access_key'], region_name=region)
                boto_clients.append(client)

        return boto_clients

    def target_process(self, client, events):
        response = client.describe_log_streams(logGroupName=self.aws_log_group_name, logStreamNamePrefix=self.aws_log_stream_name)
        sequenceToken = response['logStreams'][0]['uploadSequenceToken']
        print(sequenceToken)

        try:
            response = client.put_log_events(
                logGroupName=self.aws_log_group_name,
                logStreamName=self.aws_log_stream_name,
                logEvents=events,
                sequenceToken=sequenceToken
            )
        except Exception as e:
            print(e)

    def send_events(self, events):
        n_clients = len(self.clients)

        if n_clients > 1:
            with ThreadPoolExecutor(max_workers=n_clients) as executor:
                for client in self.boto_clients:
                    executor.submit(self.target_process, client=client, events=events)
        else:
            self.target_process(client=self.clients[0], events=events)
        

    def flush(self, q):
        events = []
        current_batch_total_bytes = 0
        # preprocess each event for AWS API
        for x in q:
            event = {
                "timestamp": int(time.time() * 1000),
                "message": x['_raw']
            }

            if (len(events) + 1 > self.MAXQUEUELENGTH) or (current_batch_total_bytes + len(json.dumps(event)) >= self.MAXBATCHBYTES):
                self.send_events(events)
                print("triggered!")
                events = []
                current_batch_total_bytes = 0

            events.append(event)
            current_batch_total_bytes += len(json.dumps(event))

        if events:
            self.send_events(events)


def load():
    """Returns an instance of the plugin"""
    return AWSCloudWatchLogOutputPlugin
