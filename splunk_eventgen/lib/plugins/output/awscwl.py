from splunk_eventgen.lib.outputplugin import OutputPlugin
import boto3
import time
import re
import json

class AWSCloudWatchLogOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "awscwl"
    MAXQUEUELENGTH = 10000
    listRE = re.compile(r'list(\[[^\]]+\])', re.I)

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)
        
        self.aws_log_group_name = getattr(self._sample, "awsLogGroupName")
        self.aws_log_stream_name = getattr(self._sample, "awsLogStreamName")
        self.aws_access_key_id_list = getattr(self._sample, "awsAccessKeyIdList", "[]")
        self.aws_secret_key_list = getattr(self._sample, "awsSecretKeyList", "[]")

        aws_access_key_id_list_match = self.listRE.match(self.aws_access_key_id_list)
        if aws_access_key_id_list_match:
            self.aws_access_key_id_list = json.loads(aws_access_key_id_list_match.group(1))

        aws_secret_key_list_match = self.listRE.match(self.aws_secret_key_list)
        if aws_secret_key_list_match:
            self.aws_secret_key_list = json.loads(aws_secret_key_list_match.group(1))
        
        self._create_boto_clients()

    def _create_boto_clients(self):
        self.boto_clients = []
        for i in range(len(self.aws_access_key_id_list)):
            client = boto3.client("logs", aws_access_key_id=self.aws_access_key_id_list[i], aws_secret_access_key=self.aws_secret_key_list[i], region_name="us-east-1")
            self.boto_clients.append(client)

    def flush(self, q):
        events = []
        for x in q:
            event = {
                "timestamp": int(time.time() * 1000),
                "message": x['_raw']
            }
            events.append(event)

        for client in self.boto_clients:
            # get sequenceToken
            response = client.describe_log_streams(logGroupName=self.aws_log_group_name, logStreamNamePrefix=self.aws_log_stream_name)
            sequenceToken = response['logStreams'][0]['uploadSequenceToken']
            print("sequenceToken: {}".format(sequenceToken))

            response = client.put_log_events(
                logGroupName=self.aws_log_group_name,
                logStreamName=self.aws_log_stream_name,
                logEvents=events,
                sequenceToken=sequenceToken
            )

            print(response)


def load():
    """Returns an instance of the plugin"""
    return AWSCloudWatchLogOutputPlugin
