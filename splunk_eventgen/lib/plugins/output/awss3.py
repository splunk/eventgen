from __future__ import division
from outputplugin import OutputPlugin
import requests
try:
    import boto3
    import botocore.exceptions
    boto_imported = True
except ImportError:
    boto_imported = False
import uuid
import datetime
import threading
import logging


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


class AwsS3OutputPlugin(OutputPlugin):
    '''
    AwsS3 output will enable events that are generated to be sent directly
    to AWS S3 through the boto3 API.  In order to use this plugin,
    you will need to supply AWS setting in config file.
    '''
    name = 'awsS3'
    useOutputQueue = False
    # MAXQUEUELENGTH = 100
    validSettings = ['awsS3BucketName', 'awsS3CompressionType',
                     'awsS3EventType', 'awsS3ObjectPrefix',
                     'awsS3ObjectSuffix', 'awsRegion', 'awsKeyId',
                     'awsSecretKey', 'awsS3EventPerKey']
    defaultableSettings = ['awsKeyId', 'awsSecretKey', 'awsS3EventType',
                           'awsS3CompressionType', 'awsS3ObjectPrefix',
                           'awsS3ObjectSuffix']

    def __init__(self, sample):



        # Override maxQueueLength to EventPerKey so that each flush
        # will generate one aws key
        if sample.awsS3EventPerKey:
            sample.maxQueueLength = sample.awsS3EventPerKey

        OutputPlugin.__init__(self, sample)

        if not boto_imported:
            self.logger.error("There is no boto3 or botocore library available")
            return

        # disable any "requests" warnings
        requests.packages.urllib3.disable_warnings()

        # Bind passed in samples to the outputter.
        self.awsS3compressiontype = sample.awsS3CompressionType if hasattr(
            sample,
            'awsS3CompressionType') and sample.awsS3CompressionType else None
        self.awsS3eventtype = sample.awsS3EventType if hasattr(
            sample, 'awsS3EventType') and sample.awsS3EventType else 'syslog'
        self.awsS3objectprefix = sample.awsS3ObjectPrefix if hasattr(
            sample, 'awsS3ObjectPrefix') and sample.awsS3ObjectPrefix else ""
        self.awsS3objectsuffix = sample.awsS3ObjectSuffix if hasattr(
            sample, 'awsS3ObjectSuffix') and sample.awsS3ObjectSuffix else ""
        self.awsS3bucketname = sample.awsS3BucketName
        self.logger.debug("Setting up the connection pool for %s in %s" %
                     (self._sample.name, self._app))
        self._client = None
        self._createConnections(sample)
        self.logger.debug("Finished init of awsS3 plugin.")

    def _createConnections(self, sample):
        try:
            if hasattr(sample, 'awsKeyId') and hasattr(sample, 'awsSecretKey'):
                self._client = boto3.client(
                    "s3",
                    region_name=sample.awsRegion,
                    aws_access_key_id=sample.awsKeyId,
                    aws_secret_access_key=sample.awsSecretKey)
                if self._client is None:
                    msg = '''
                    [your_eventgen_stanza]
                    awsKeyId = YOUR_ACCESS_KEY
                    awsSecretKey = YOUR_SECRET_KEY
                    '''

                    self.logger.error(
                        "Failed for init boto3 client: %s, you should define correct 'awsKeyId'\
                        and 'awsSecretKey' in eventgen conf %s" % msg)
                    raise
            else:
                self._client = boto3.client('s3', region_name=sample.awsRegion)
        except Exception as e:
            self.logger.error("Failed for init boto3 client: exception =  %s" % e)
            raise e
        # Try list bucket method to validate if the connection works
        try:
            self._client.list_buckets()
        except botocore.exceptions.NoCredentialsError:
            msg = '''
            [default]
            aws_access_key_id = YOUR_ACCESS_KEY
            aws_secret_access_key = YOUR_SECRET_KEY
            '''

            self.logger.error("Failed for init boto3 client, you should create "
                         "'~/.aws/credentials' with credential info %s" % msg)
            raise
        self.logger.debug("Init conn done, conn = %s" % self._client)

    def _sendPayloads(self, payload):
        currentreadsize = 0
        currentreadevent = 0
        stringpayload = []
        totalbytesexpected = 0
        totalbytessent = 0
        numberevents = len(payload)
        self.logger.debug("Sending %s events to s3 key" % numberevents)
        self._transmitEvents(payload)

    def _transmitEvents(self, payloadstring):
        self.logger.debug("Transmission called with payloadstring event number: %d "
                     % len(payloadstring))
        records = "".join(payloadstring)
        # Different key prefix for different log type
        if self.awsS3eventtype == 'elbaccesslog':
            s3keyname = self.awsS3objectprefix + datetime.datetime.utcnow(
            ).strftime("%Y%m%dT%H%MZ") + '_' + str(uuid.uuid1(
            )) + self.awsS3objectsuffix
        elif self.awsS3eventtype == 's3accesslog':
            s3keyname = self.awsS3objectprefix + datetime.datetime.utcnow(
            ).strftime("%Y-%m-%d-%H-%M-%S") + '-' + str(uuid.uuid1()).replace(
                '-', '').upper()[0:15] + self.awsS3objectsuffix
        else:
            s3keyname = self.awsS3objectprefix + datetime.datetime.utcnow(
            ).isoformat() + str(uuid.uuid1()) + self.awsS3objectsuffix
        self.logger.debugv("Uploading %d events into s3 key: %s " %
                      (len(records), s3keyname))
        if self.awsS3compressiontype == 'gz':
            import StringIO
            import gzip
            out = StringIO.StringIO()
            with gzip.GzipFile(fileobj=out, mode="w") as f:
                f.write(records)
            records = out.getvalue()
        try:
            response = self._client.put_object(Bucket=self.awsS3bucketname,
                                               Key=s3keyname,
                                               Body=records)
            self.logger.debugv("response = %s" % response)
        except Exception as e:
            self.logger.error("Failed for exception: %s" % e)
            self.logger.debugv("Failed sending events to payload: %s" %
                          (payloadstring))
            raise e

    def flush(self, q):
        self.logger.debug("Flush called on awsS3 plugin with length %d" % len(q))
        if len(q) > 0:
            try:
                payload = []
                self.logger.debug("Currently being called with %d events" % len(q))
                for event in q:
                    if event.get('_raw') is None:
                        self.logger.error(
                            'failure outputting event, does not contain _raw')
                    else:
                        payload.append(event['_raw'])
                self.logger.debug(
                    "Finished processing events, sending all to AWS S3")
                self._sendPayloads(payload)
            except Exception as e:
                import traceback
                self.logger.error(traceback.print_exc())
                self.logger.error('failed sending events, reason: %s ' % e)

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')


def load():
    """Returns an instance of the plugin"""
    return AwsS3OutputPlugin
