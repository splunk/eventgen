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

        access_key = getattr(self._sample, "awsAccessKey", None)
        secret_access_eky = getattr(self._sample, "awsSecretAccessKey", None)
        self.log_group = getattr(self._sample, "awsLogGroup", None)
        self.log_stream = getattr(self._sample, "awsLogStream", None)
        aws_region = getattr(self._sample, "awsRegion", None)

        if access_key is None or secret_access_eky is None or aws_region is None:
            logger.error("Please specify the correct awsAccessKey/awsSecretAccessKey/awsRegion")

        self.boto_client = boto3.client("logs", aws_access_key_id=access_key, aws_secret_access_key=secret_access_eky, region_name=aws_region)

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
                self.target_process(self.boto_client, self.log_group, self.log_stream, events)
                events = []
                current_batch_total_bytes = 0

            events.append(event)
            current_batch_total_bytes += len(json.dumps(event))

        if events:
            self.target_process(self.boto_client, self.log_group, self.log_stream, events)


def load():
    """Returns an instance of the plugin"""
    return AWSCloudWatchLogOutputPlugin