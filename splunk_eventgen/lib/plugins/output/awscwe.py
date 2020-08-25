from splunk_eventgen.lib.outputplugin import OutputPlugin
import boto3
import time
import re
import json

class AWSCloudWatchEventOutOutputPlugin(OutputPlugin):
    useOutputQueue = False
    name = "awscwe"
    MAXQUEUELENGTH = 10000
    listRE = re.compile(r'list(\[[^\]]+\])', re.I)

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

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
            client = boto3.client("events", aws_access_key_id=self.aws_access_key_id_list[i], aws_secret_access_key=self.aws_secret_key_list[i], region_name="us-east-1")
            self.boto_clients.append(client)


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

        for client in self.boto_clients:
            response = client.put_events(
                Entries=events
            )

            print(response)


def load():
    """Returns an instance of the plugin"""
    return AWSCloudWatchEventOutOutputPlugin
