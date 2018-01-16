from nameko.rpc import rpc
from nameko.web.handlers import http
from nameko.events import EventDispatcher, event_handler, BROADCAST
import ConfigParser
import yaml
import json
import os
import socket
import time
import requests
import glob
import tarfile
import shutil
import eventgen_nameko_dependency
import logging

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
EVENTGEN_DIR = os.path.realpath(os.path.join(FILE_PATH, ".."))
CUSTOM_CONFIG_PATH = os.path.realpath(os.path.join(FILE_PATH, "default", "eventgen_wsgi.conf"))
EVENTGEN_ENGINE_CONF_PATH = os.path.abspath(os.path.join(FILE_PATH, "default", "eventgen_engine.conf"))

def get_eventgen_name_from_conf():
    with open(os.path.abspath(os.path.join(FILE_PATH, "server_conf.yml"))) as config_yml:
        loaded_yml = yaml.load(config_yml)
        return loaded_yml['EVENTGEN_NAME'] if 'EVENTGEN_NAME' in loaded_yml else socket.gethostname()
    return None

class EventgenListener:
    name = "eventgen_listener"

    dispatch = EventDispatcher()

    eventgen_dependency = eventgen_nameko_dependency.EventgenDependency()
    eventgen_name = get_eventgen_name_from_conf()
    host = socket.gethostname()
    log = logging.getLogger(name)
    log.info("Eventgen name is set to [{}] at host [{}]".format(eventgen_name, host))

    def get_status(self):
        '''
        Get status of eventgen

        return value structure
        {
            "EVENTGEN_STATUS" :
            "EVENTGEN_HOST" :
            "CONFIGURED" :
            "CONFIG_FILE" :
            "QUEUE_STATUS" : { "SAMPLE_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': },
                               "OUTPUT_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': },
                               "WORKER_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': }}
        }
        '''
        res = dict()
        if self.eventgen_dependency.eventgen.check_running():
            status = 1
        else:
            status = 0
        res["EVENTGEN_STATUS"] = status
        res["EVENTGEN_HOST"] = self.host
        res["CONFIGURED"] = self.eventgen_dependency.configured
        res["CONFIG_FILE"] = self.eventgen_dependency.configfile
        res["QUEUE_STATUS"] = {'SAMPLE_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'},
                               'OUTPUT_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'},
                               'WORKER_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'}}

        if hasattr(self.eventgen_dependency.eventgen, "sampleQueue"):
            res["QUEUE_STATUS"]['SAMPLE_QUEUE']['UNFINISHED_TASK'] = self.eventgen_dependency.eventgen.sampleQueue.unfinished_tasks
            res["QUEUE_STATUS"]['SAMPLE_QUEUE']['QUEUE_LENGTH'] = self.eventgen_dependency.eventgen.sampleQueue.qsize()
        if hasattr(self.eventgen_dependency.eventgen, "outputQueue"):
            res["QUEUE_STATUS"]['OUTPUT_QUEUE']['UNFINISHED_TASK'] = self.eventgen_dependency.eventgen.outputQueue.unfinished_tasks
            res["QUEUE_STATUS"]['OUTPUT_QUEUE']['QUEUE_LENGTH'] = self.eventgen_dependency.eventgen.outputQueue.qsize()
        if hasattr(self.eventgen_dependency.eventgen, "workerQueue"):
            res["QUEUE_STATUS"]['WORKER_QUEUE']['UNFINISHED_TASK'] = self.eventgen_dependency.eventgen.workerQueue.unfinished_tasks
            res["QUEUE_STATUS"]['WORKER_QUEUE']['QUEUE_LENGTH'] = self.eventgen_dependency.eventgen.workerQueue.qsize()
        return res

    ##############################################
    ############### Real Methods #################
    ##############################################

    def index(self):
        self.log.info("index method called")
        home_page = '''*** Eventgen WSGI ***
Host: {0}
Eventgen Status: {1}
Eventgen Config file exists: {2}
Eventgen Config file path: {3}
Worker Queue Status: {4}
Sample Queue Status: {5}
Output Queue Status: {6}\n'''
        status = self.get_status()
        eventgen_status = "running" if status["EVENTGEN_STATUS"] else "stopped"
        host = status["EVENTGEN_HOST"]
        configured = status["CONFIGURED"]
        config_file = status["CONFIG_FILE"]
        worker_queue_status = status["QUEUE_STATUS"]["WORKER_QUEUE"]
        sample_queue_status = status["QUEUE_STATUS"]["SAMPLE_QUEUE"]
        output_queue_status = status["QUEUE_STATUS"]["OUTPUT_QUEUE"]

        return home_page.format(host,
                                eventgen_status,
                                configured,
                                config_file,
                                worker_queue_status,
                                sample_queue_status,
                                output_queue_status)

    def status(self):
        self.log.info('Status method called.')
        status = self.get_status()
        self.log.info(status)
        self.send_status_to_controller(server_status=status)
        return json.dumps(status, indent=4)

    @rpc
    def send_status_to_controller(self, server_status):
        data = {}
        data['server_name'] = self.eventgen_name
        data['server_status'] = server_status
        self.dispatch("server_status", data)

    def start(self):
        self.log.info("start method called. Config is {}".format(self.eventgen_dependency.configfile))
        try:
            if not self.eventgen_dependency.configured:
                return "There is not config file known to eventgen. Pass in the config file to /conf before you start."
            if self.eventgen_dependency.eventgen.check_running():
                return "Eventgen already started."
            self.eventgen_dependency.eventgen.start(join_after_start=False)
            return "Eventgen has successfully started."
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def stop(self):
        self.log.info("stop method called")
        try:
            if self.eventgen_dependency.eventgen.check_running():
                self.eventgen_dependency.eventgen.stop()
                return "Eventgen is stopped."
            return "There is no eventgen process running."
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def restart(self):
        self.log.info("restart method called.")
        self.stop()
        time.sleep(2)
        self.start()

    def get_conf(self):
        self.log.info("get_conf method called.")
        try:
            if self.eventgen_dependency.configured:
                config = ConfigParser.ConfigParser()
                config.optionxform = str
                config_path = CUSTOM_CONFIG_PATH
                if os.path.isfile(config_path):
                    config.read(config_path)
                    out_json = dict()
                    for section in config.sections():
                        out_json[section] = dict()
                        for k, v in config.items(section):
                            out_json[section][k] = v
                    self.log.info(out_json)
                    self.send_conf_to_controller(server_conf=out_json)
                    return json.dumps(out_json, indent=4)
            return "N/A"
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def send_conf_to_controller(self, server_conf):
        data = {}
        data['server_name'] = self.eventgen_name
        data['server_conf'] = server_conf
        self.dispatch("server_conf", data)

    def set_conf(self, conf):
        '''

        customconfig data format
        {sample: {key: value}, sample2: {key: value}}
        '''
        self.log.info("set_conf method called with {}".format(json.loads(conf)))
        try:
            config = ConfigParser.ConfigParser()
            config.optionxform = str
            conf_content = json.loads(conf)['content']

            for sample in conf_content.iteritems():
                sample_name = sample[0]
                sample_key_value_pairs = sample[1]
                config.add_section(sample_name)
                for pair in sample_key_value_pairs.iteritems():
                    value = pair[1]
                    if type(value) == dict:
                        value = json.dumps(value)
                    config.set(sample_name, pair[0], value)

            with open(CUSTOM_CONFIG_PATH, 'wb') as conf_content:
                config.write(conf_content)

            self.eventgen_dependency.configured = True
            self.eventgen_dependency.configfile = CUSTOM_CONFIG_PATH
            self.eventgen_dependency.eventgen.reload_conf(CUSTOM_CONFIG_PATH)
            self.log.info("custom_config_json is {}".format(conf_content))
            return self.get_conf()
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def edit_conf(self, conf):
        self.log.info("edit_conf method called with {}".format(json.loads(conf)))
        try:
            config = ConfigParser.ConfigParser()
            config.optionxform = str
            conf_content = json.loads(conf)['content']
            config.read(CUSTOM_CONFIG_PATH)

            for stanza, kv_pairs in conf_content.iteritems():
                for k, v in kv_pairs.iteritems():
                    try:
                        config.get(stanza, k)
                        config.set(stanza, k, v)
                    except Exception as e:
                        if type(e) == ConfigParser.NoSectionError:
                            config.add_section(stanza)
                        config.set(stanza, k, v)

            with open(CUSTOM_CONFIG_PATH, 'wb') as conf_content:
                config.write(conf_content)

            self.eventgen_dependency.configured = True
            self.eventgen_dependency.configfile = CUSTOM_CONFIG_PATH
            self.eventgen_dependency.eventgen.reload_conf(CUSTOM_CONFIG_PATH)
            return self.get_conf()
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def bundle(self, url):
        # Set these parameters to notify that eventgen is in the process of configuration
        self.eventgen_dependency.configured = False
        self.eventgen_dependency.customconfigured = False
        try:
            # Download the bundle
            self.log.info("Downloading bundle at {}...".format(url))
            bundle_path = os.path.join(FILE_PATH, "eg-bundle.tgz")
            r = requests.get(url, stream=True)
            with open(bundle_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        f.write(chunk)
            r.close()
            self.log.info("Downloading complete!")
            # Extract bundle
            self.log.info("Extracting bundle...")
            tar = tarfile.open(bundle_path)
            bundle_dir = os.path.commonprefix(tar.getnames())
            tar.extractall(path=os.path.dirname(bundle_path))
            tar.close()
            self.log.info("Extraction complete!")
            # Move sample files
            self.log.info("Detecting sample files...")
            if os.path.isdir(os.path.join(FILE_PATH, bundle_dir, "samples")):
                self.log.info("Moving sample files...")
                for file in glob.glob(os.path.join(FILE_PATH, bundle_dir, "samples", "*")):
                    shutil.copy(file, os.path.join(FILE_PATH, "samples"))
                self.log.info("Sample files moved!")
            # Read eventgen.conf
            self.log.info("Detecting eventgen.conf...")
            if os.path.isfile(os.path.join(FILE_PATH, bundle_dir, "default", "eventgen.conf")):
                self.log.info("Reading eventgen.conf...")
                config_dict = self.read_eventgen_conf(os.path.join(FILE_PATH, bundle_dir, "default", "eventgen.conf"))
                self.log.info("Config is {}".format(config_dict))
            # Set these parameters to notify that eventgen is finished with the configuration
            self.eventgen_dependency.configured = True
            self.eventgen_dependency.customconfigured = True
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    ##############################################
    ############ Event Handler Methods ###########
    ##############################################

    @event_handler("eventgen_controller", "all_index", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_index(self, payload):
        return self.index()

    @event_handler("eventgen_controller", "all_status", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_status(self, payload):
        return self.status()

    @event_handler("eventgen_controller", "all_start", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_start(self, payload):
        return self.start()

    @event_handler("eventgen_controller", "all_stop", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_stop(self, payload):
        return self.stop()

    @event_handler("eventgen_controller", "all_restart", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_restart(self, payload):
        return self.restart()

    @event_handler("eventgen_controller", "all_get_conf", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_get_conf(self, payload):
        return self.get_conf()

    @event_handler("eventgen_controller", "all_set_conf", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_set_conf(self, payload):
        return self.set_conf(conf=payload)

    @event_handler("eventgen_controller", "all_edit_conf", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_edit_conf(self, payload):
        return self.edit_conf(conf=payload)
    
    @event_handler("eventgen_controller", "all_bundle", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_bundle(self, payload):
        if payload['url']:
            return self.bundle(payload['url'])

    @event_handler("eventgen_controller", "{}_index".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_index(self, payload):
        return self.index()

    @event_handler("eventgen_controller", "{}_status".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_status(self, payload):
        return self.status()

    @event_handler("eventgen_controller", "{}_start".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_start(self, payload):
        return self.start()

    @event_handler("eventgen_controller", "{}_stop".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_stop(self, payload):
        return self.stop()

    @event_handler("eventgen_controller", "{}_restart".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_restart(self, payload):
        return self.restart()

    @event_handler("eventgen_controller", "{}_get_conf".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_get_conf(self, payload):
        return self.get_conf()

    @event_handler("eventgen_controller", "{}_set_conf".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_set_conf(self, payload):
        return self.set_conf(conf=payload)

    @event_handler("eventgen_controller", "{}_edit_conf".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_edit_conf(self, payload):
        return self.edit_conf(conf=payload)

    @event_handler("eventgen_controller", "{}_bundle".format(eventgen_name), handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_bundle(self, payload):
        if payload['url']:
            return self.bundle(payload['url'])

    ##############################################
    ################ HTTP Methods ################
    ##############################################

    @http('GET', '/')
    def http_root(self, request):
        return self.index()

    @http('GET', '/index')
    def http_index(self, request):
        return self.index()

    @http('GET', '/status')
    def http_status(self, request):
        return self.status()

    @http('POST', '/start')
    def http_start(self, request):
        return self.start()

    @http('POST', '/stop')
    def http_stop(self, request):
        return self.stop()

    @http('POST', '/restart')
    def http_restart(self, request):
        return self.restart()

    @http('GET', '/conf')
    def http_get_conf(self, request):
        return self.get_conf()

    @http('POST', '/conf')
    def http_set_conf(self, request):
        data = request.get_data()
        if data:
            return self.set_conf(data)
        else:
            return '400', 'Please pass the valid parameters.'
    
    @http('POST', '/bundle')
    def http_bundle(self, request):
        return self.bundle()

    @http('PUT', '/conf')
    def http_edit_conf(self, request):
        data = request.get_data()
        if data:
            return self.edit_conf(data)
        else:
            return '400', 'Please pass valid config data.'

    ##############################################
    ################ Helper Methods ##############
    ##############################################

    def is_custom_conf(self, conf):
        if conf[0] == '{' and conf[-1] == '}':
            return True
        else:
            return False

    def read_eventgen_conf(self, path):
        config = ConfigParser.ConfigParser()
        config.read(path)
        self.log.info(path)
        config_dict = {s:dict(config.items(s)) for s in config.sections()}
        self.log.info(config.sections())
        return config_dict
