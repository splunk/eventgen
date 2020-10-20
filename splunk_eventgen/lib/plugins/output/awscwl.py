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

class AWSCloudWatchLogOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "awscwl"
    MAXQUEUELENGTH = 10000
    MAXBATCHBYTES = 1048576

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)
        # self.aws_log_group_name = getattr(self._sample, "awsLogGroupName")
        # self.aws_log_stream_name = getattr(self._sample, "awsLogStreamName")
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
            # log_group_names = acct.get("logGroupNames")
            # log_group_stream_names = acct.get("logGroupStreamNames")
            # regions = acct.get('regions')
            acc_key = acct.get("access_key")
            as_key = acct.get("secret_access_key")
            awscwl = acct.get("awscwl")
            if not acc_key or not as_key or not awscwl:
                logger.error("No credentials or no awscwl-related info provided for this account")
                sys.exit(1)

            for lg in awscwl:
                region = lg.get("region")
                lg_name = lg.get("logGroupName")
                lg_snames = lg.get("logGroupStreamNames")
                for lg_sname in lg_snames:
                    boto_clients.append({
                        "client": boto3.client("logs", aws_access_key_id=acc_key, aws_secret_access_key=as_key, region_name=region),
                        "lg_name": lg_name,
                        "lg_sname": lg_sname
                    })

        return boto_clients

    def target_process(self, client, lg_name, lg_sname, events):
        while True:
            response = client.describe_log_streams(logGroupName=lg_name, logStreamNamePrefix=lg_sname)
            # since we provide the full name of the log stream, the first item should be it
            matched_stream = response['logStreams'][0]
            # sequence token isn't needed for any new stream so None will be set in such case to avoid KeyError
            sequenceToken = matched_stream.get('uploadSequenceToken', None)

            try:
                if sequenceToken is None:
                    response = client.put_log_events(
                        logGroupName=lg_name,
                        logStreamName=lg_sname,
                        logEvents=events
                    )
                else:
                    response = client.put_log_events(
                        logGroupName=lg_name,
                        logStreamName=lg_sname,
                        logEvents=events,
                        sequenceToken=sequenceToken
                    )
            except client.exceptions.InvalidSequenceTokenException as e:
                logger.info("Refetching SequenceToken after 3 seconds")
                time.sleep(3)
            except Exception as e:
                # drop events if encounter other type of exception here
                logger.error(e)
                break
            else:
                break

    def send_events(self, events):
        n_clients = len(self.clients)
        if n_clients > 1:
            with ThreadPoolExecutor(max_workers=n_clients) as executor:
                for e in self.clients:
                    executor.submit(self.target_process, client=e["client"], lg_name=e["lg_name"], lg_sname=e["lg_sname"], events=events)
        else:
            only_client = self.clients[0]
            self.target_process(client=only_client["client"], lg_name=only_client["lg_name"], lg_sname=only_client["lg_sname"], events=events)


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
                events = []
                current_batch_total_bytes = 0

            events.append(event)
            current_batch_total_bytes += len(json.dumps(event))

        if events:
            self.send_events(events)


def load():
    """Returns an instance of the plugin"""
    return AWSCloudWatchLogOutputPlugin