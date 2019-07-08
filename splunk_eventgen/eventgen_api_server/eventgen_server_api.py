import flask
from flask import Response, request
import socket
import json
import ConfigParser
import os
import time
import requests
import zipfile
import tarfile
import glob
import shutil
import collections

from api_blueprint import ApiBlueprint
import eventgen_core_object

INTERNAL_ERROR_RESPONSE = json.dumps({"message": "Internal Error Occurred"})

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_PATH = os.path.realpath(os.path.join(FILE_PATH, "..", "default"))
SAMPLE_DIR_PATH = os.path.realpath(os.path.join(FILE_PATH, "..", "samples"))

class EventgenServerAPI(ApiBlueprint):
    def __init__(self):
        ApiBlueprint.__init__(self)
        self.bp = self._create_blueprint()

        self.total_volume = 0.0
        self.eventgen = eventgen_core_object.EventgenCoreObject()
        self.host = socket.gethostname()

    def _create_blueprint(self):
        bp = flask.Blueprint('server_api', __name__)

        @bp.route('/index', methods=['GET'])
        def http_get_index():
            return get_index()
            
        @bp.route('/status', methods=['GET'])
        def http_get_status():
            try:
                response = get_status()
                return Response(json.dumps(response), mimetype='application/json', status=200)
            except Exception as e:
                # log exeption
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
            
        @bp.route('/conf', methods=['GET'])
        def http_get_conf():
            try:
                response = get_conf()
                return Response(json.dumps(response), mimetype='application/json', status=200)
            except Exception as e:
                # log exeption
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/conf', methods=['POST'])
        def http_post_conf():
            try:
                set_conf(request.get_json(force=True))
                return Response(json.dumps(get_conf()), mimetype='application/json', status=200)
            except Exception as e:
                # log exeption
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/volume', methods=['GET'])
        def http_get_volume():
            try:
                response = get_volume()
                return Response(json.dumps(response), mimetype='application/json', status=200)
            except Exception as e:
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/volume', methods=['POST'])
        def http_post_volume():
            try:
                set_volume(request.get_json(force=True).get("total_volume", 0.0))
                return Response(json.dumps(get_volume()), mimetype='application/json', status=200)
            except Exception as e:
                raise e
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/start', methods=['POST'])
        def http_post_start():
            try:
                response = start()
                return Response(json.dumps(response), mimetype='application/json', status=200)
            except Exception as e:
                raise e
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/stop', methods=['POST'])
        def http_post_stop():
            try:
                response = stop()
                return Response(json.dumps(response), mimetype='application/json', status=200)
            except Exception as e:
                raise e
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/restart', methods=['POST'])
        def http_post_restart():
            try:
                response = restart()
                return Response(json.dumps(response), mimetype='application/json', status=200)
            except Exception as e:
                raise e
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/reset', methods=['POST'])
        def http_post_reset():
            try:
                response = reset()
                return Response(json.dumps(response), mimetype='application/json', status=200)
            except Exception as e:
                raise e
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/bundle', methods=['POST'])
        def http_post_bundle():
            try:
                set_bundle(request.get_json(force=True).get("url", ''))
                return Response(json.dumps(get_conf()), mimetype='application/json', status=200)
            except Exception as e:
                raise e
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/setup', methods=['POST'])
        def http_post_setup():
            try:
                clean_bundle_conf()
                return Response(json.dumps(get_conf()), mimetype='application/json', status=200)
            except Exception as e:
                raise e
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
                
        def get_index():
            home_page = '''*** Eventgen WSGI ***\nHost: {0}\nEventgen Status: {1}\nEventgen Config file exists: {2}\nEventgen Config file path: {3}\nTotal volume: {4}\nWorker Queue Status: {5}\nSample Queue Status: {6}\nOutput Queue Status: {7}\n'''
            status = get_status()
            eventgen_status = "running" if status["EVENTGEN_STATUS"] else "stopped"
            host = status["EVENTGEN_HOST"]
            configured = status["CONFIGURED"]
            config_file = status["CONFIG_FILE"]
            total_volume = status["TOTAL_VOLUME"]
            worker_queue_status = status["QUEUE_STATUS"]["WORKER_QUEUE"]
            sample_queue_status = status["QUEUE_STATUS"]["SAMPLE_QUEUE"]
            output_queue_status = status["QUEUE_STATUS"]["OUTPUT_QUEUE"]
            return home_page.format(host, eventgen_status, configured, config_file, total_volume, worker_queue_status,
                                    sample_queue_status, output_queue_status)

        def get_conf():
            response = collections.OrderedDict()
            if self.eventgen.configured:
                config = ConfigParser.ConfigParser()
                config.optionxform = str
                config_path = self.eventgen.configfile
                if os.path.isfile(config_path):
                    config.read(config_path)
                    for section in config.sections():
                        response[section] = collections.OrderedDict()
                        for k, v in config.items(section):
                            response[section][k] = v
            self.eventgen.check_and_configure_eventgen
            return response
        
        def set_conf(request_body):
            config = ConfigParser.ConfigParser({}, collections.OrderedDict)
            config.optionxform = str

            for sample in request_body.iteritems():
                config.add_section(sample[0])
                for pair in sample[1].iteritems():
                    value = pair[1]
                    if type(value) == dict:
                        value = json.dumps(value)
                    config.set(sample[0], pair[0], value)

            with open(eventgen_core_object.CUSTOM_CONFIG_PATH, 'w+') as conf_content:
                config.write(conf_content)

            self.eventgen.check_and_configure_eventgen()
        
        def get_status():
            response = dict()
            if self.eventgen.eventgen_core_object.check_running():
                status = 1 if not self.eventgen.eventgen_core_object.check_done() else 2 # 1 is running and 2 is done
            else: 
                status = 0 # not start yet
            response["EVENTGEN_STATUS"] = status
            response["EVENTGEN_HOST"] = self.host
            response["CONFIGURED"] = self.eventgen.configured
            response["CONFIG_FILE"] = self.eventgen.configfile
            response["TOTAL_VOLUME"] = self.total_volume
            response["QUEUE_STATUS"] = {
                'SAMPLE_QUEUE': {
                    'UNFINISHED_TASK': 'N/A', 
                    'QUEUE_LENGTH': 'N/A'}, 
                'OUTPUT_QUEUE': {
                    'UNFINISHED_TASK': 'N/A', 
                    'QUEUE_LENGTH': 'N/A'}, 
                'WORKER_QUEUE': {
                    'UNFINISHED_TASK': 'N/A', 
                    'QUEUE_LENGTH': 'N/A'}
                }
            response['THROUGHPUT_STATUS'] = get_throughput()
            if hasattr(self.eventgen.eventgen_core_object, "sampleQueue"):
                response["QUEUE_STATUS"]['SAMPLE_QUEUE']['UNFINISHED_TASK'] = self.eventgen.eventgen_core_object.sampleQueue.unfinished_tasks
                response["QUEUE_STATUS"]['SAMPLE_QUEUE']['QUEUE_LENGTH'] = self.eventgen.eventgen_core_object.sampleQueue.qsize()
            if hasattr(self.eventgen.eventgen_core_object, "outputQueue"):
                response["QUEUE_STATUS"]['OUTPUT_QUEUE']['UNFINISHED_TASK'] = self.eventgen.eventgen_core_object.outputQueue.unfinished_tasks
                response["QUEUE_STATUS"]['OUTPUT_QUEUE']['QUEUE_LENGTH'] = self.eventgen.eventgen_core_object.outputQueue.qsize()
            if hasattr(self.eventgen.eventgen_core_object, "workerQueue"):
                response["QUEUE_STATUS"]['WORKER_QUEUE']['UNFINISHED_TASK'] = self.eventgen.eventgen_core_object.workerQueue.unfinished_tasks
                response["QUEUE_STATUS"]['WORKER_QUEUE']['QUEUE_LENGTH'] = self.eventgen.eventgen_core_object.workerQueue.qsize()
            return response

        def get_throughput():
            empty_throughput = {'TOTAL_VOLUME_MB': 0, 'TOTAL_COUNT': 0, 'THROUGHPUT_VOLUME_KB': 0, 'THROUGHPUT_COUNT': 0}
            if hasattr(self.eventgen.eventgen_core_object, 'output_counters'):
                total_volume = 0
                total_count = 0
                throughput_volume = 0
                throughput_count = 0
                for output_counter in self.eventgen.eventgen_core_object.output_counters:
                    total_volume += output_counter.total_output_volume
                    total_count += output_counter.total_output_count
                    throughput_volume += output_counter.throughput_volume
                    throughput_count += output_counter.throughput_count
                return {
                    'TOTAL_VOLUME_MB': total_volume / (1024 * 1024), 
                    'TOTAL_COUNT': total_count, 
                    'THROUGHPUT_VOLUME_KB': throughput_volume / (1024), 
                    'THROUGHPUT_COUNT': throughput_count}
            else:
                return empty_throughput
        
        def get_volume():
            response = dict()
            config = get_conf()
            total_volume = 0.0
            volume_distribution = {}
            for stanza in config.keys():
                if isinstance(config[stanza], dict) and "perDayVolume" in config[stanza].keys():
                    total_volume += float(config[stanza]["perDayVolume"])
                    volume_distribution[stanza] = float(config[stanza]["perDayVolume"])

            if total_volume:
                self.total_volume = total_volume
            response['total_volume'] = self.total_volume
            response['volume_distribution'] = volume_distribution
            return response
        
        def set_volume(target_volume):
            conf_dict = get_conf()
            if get_volume()['total_volume'] != 0:
                ratio = float(target_volume) / float(self.total_volume)
                for stanza, kv_pair in conf_dict.iteritems():
                    if isinstance(kv_pair, dict):
                        if "perDayVolume" in kv_pair.keys():
                            conf_dict[stanza]["perDayVolume"] = round(float(conf_dict[stanza]["perDayVolume"]) * ratio, 2)
            else:
                # If there is no total_volume existing, divide the volume equally into stanzas
                divided_volume = float(target_volume) / len(conf_dict.keys())
                for stanza, kv_pair in conf_dict.iteritems():
                    if isinstance(kv_pair, dict):
                        conf_dict[stanza]["perDayVolume"] = divided_volume

            set_conf(conf_dict)
            self.total_volume = round(float(target_volume), 2)

        def start():
            response = {}
            if not self.eventgen.configured:
                response['message'] = "Eventgen is not configured."
            elif self.eventgen.eventgen_core_object.check_running():
                response['message'] = "Eventgen already started."
            else:
                self.eventgen.eventgen_core_object.start(join_after_start=False)
                response['message'] = "Eventgen has successfully started."
            return response
        
        def stop():
            response = {}
            if self.eventgen.eventgen_core_object.check_running():
                self.eventgen.eventgen_core_object.stop()
                response['message'] = "Eventgen is stopped."
            else:
                response['message'] = "There is no Eventgen process running."
            return response

        def restart():
            response = {}
            if self.eventgen.eventgen_core_object.check_running():
                stop()
                time.sleep(0.5)
                start()
                response['message'] = "Eventgen has successfully restarted."
            else:
                start()
                response['message'] = "Eventgen was not running. Starting Eventgen."
            return response

        def reset():
            response = {}
            self.stop()
            self.eventgen.refresh_eventgen_core_object()
            response['message'] = "Eventgen has been reset."
            return response

        def set_bundle(url):
            if not url:
                return 

            self.eventgen.configured = False
            bundle_dir = unarchive_bundle(download_bundle(url))

            if os.path.isdir(os.path.join(bundle_dir, "samples")):
                for file in glob.glob(os.path.join(bundle_dir, "samples", "*")):
                    shutil.copy(file, SAMPLE_DIR_PATH)

            if os.path.isfile(os.path.join(bundle_dir, "default", "eventgen.conf")):
                config = ConfigParser.ConfigParser()
                config.optionxform = str
                config.read(os.path.join(bundle_dir, "default", "eventgen.conf"))
                config_dict = {s: collections.OrderedDict(config.items(s)) for s in config.sections()}
                set_conf(config_dict)
                self.eventgen.configured = True

        def download_bundle(url):
            bundle_path = os.path.join(DEFAULT_PATH, "eg-bundle.tgz")
            r = requests.get(url, stream=True)
            with open(bundle_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        f.write(chunk)
            r.close()
            return bundle_path

        def unarchive_bundle(path):
            output = ''
            if tarfile.is_tarfile(path):
                tar = tarfile.open(path)
                output = os.path.join(os.path.dirname(path), os.path.commonprefix(tar.getnames()))
                tar.extractall(path=os.path.dirname(path))
                tar.close()
            elif zipfile.is_zipfile(path):
                zipf = zipfile.ZipFile(path)
                # output = 
                # zipf.extractall(path=os.path.dirname(path))
                for info in zipf.infolist():
                    old_file_name = info.filename
                    if info.filename.find('/') == len(info.filename) - 1:
                        info.filename = "eg-bundle/"
                    else:
                        info.filename = "eg-bundle/" + info.filename[info.filename.find('/') + 1:]
                    zipf.extract(info, os.path.dirname(path))
                output = os.path.join(os.path.dirname(path), 'eg-bundle')
                zipf.close()
            else:
                msg = "Unknown archive format!"
                raise Exception(msg)
            return output
        
        def clean_bundle_conf():
            conf_dict = get_conf()

            if ".*" not in conf_dict.keys():
                conf_dict['.*'] = {}

            # 1. Remove sampleDir from individual stanza and set a global sampleDir
            # 2. Remove outputMode from individual stanza and set a global outputMode to httpevent
            # 3. Change token sample path to a local sample path
            for stanza, kv_pair in conf_dict.iteritems():
                if stanza != ".*":
                    if 'sampleDir' in kv_pair:
                        del kv_pair['sampleDir']
                    if 'outputMode' in kv_pair:
                        del kv_pair['outputMode']
                for key, value in kv_pair.iteritems():
                    if 'replacementType' in key and value in ['file', 'mvfile', 'seqfile']:
                        token_num = key[key.find('.')+1:key.rfind('.')]
                        if not token_num: continue
                        else:
                            existing_path = kv_pair['token.{}.replacement'.format(token_num)]
                            kv_pair['token.{}.replacement'.format(token_num)] = os.path.join(SAMPLE_DIR_PATH, existing_path[existing_path.rfind('/')+1:])

            conf_dict['.*']['sampleDir'] = SAMPLE_DIR_PATH
            conf_dict['.*']['outputMode'] = 'httpevent'

            set_conf(conf_dict)

        return bp

