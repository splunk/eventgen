from nameko.web.handlers import http
from nameko.events import EventDispatcher, event_handler, BROADCAST
import ConfigParser
import yaml
import json
import os
import socket
import time
import eventgen_nameko_dependency
import logging

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
EVENTGEN_DIR = os.path.realpath(os.path.join(FILE_PATH, ".."))
CUSTOM_CONFIG_PATH = os.path.realpath(os.path.join(FILE_PATH, "default/eventgen_wsgi.conf"))
EVENTGEN_ENGINE_CONF_PATH = os.path.abspath(os.path.join(FILE_PATH, "default", "eventgen_engine.conf"))

def get_eventgen_name_from_conf():
    with open(os.path.abspath(os.path.join(FILE_PATH, "listener_conf.yml"))) as config_yml:
        loaded_yml = yaml.load(config_yml)
        return loaded_yml['EVENTGEN_NAME'] if 'EVENTGEN_NAME' in loaded_yml else None
    return None

class EventgenListener:
    name = "eventgen_listener"

    eventgen_dependency = eventgen_nameko_dependency.EventgenDependency()
    eventgen_name = get_eventgen_name_from_conf()
    host = socket.gethostname()
    _log = logging.getLogger(name)
    _log.info("Eventgen name is set to [{}] at host [{}]".format(eventgen_name, host))

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
        res["CUSTOMCONFIGURED"] = self.eventgen_dependency.customconfigured
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
        self._log.info("index method called")
        home_page = '''
        <h1>Eventgen WSGI</h1>
        <p>Host: {0}</p>
        <p>Eventgen Status: {1}</p>
        <p>Eventgen Config file exists: {2}</p>
        <p>Eventgen Custom Configured?: {3}</p>
        <p>Eventgen Config file path: {4}</p>
        <p>Worker Queue Status: {5}</p>
        <p>Sample Queue Status: {6}</p>
        <p>Output Queue Status: {7}</p>
        '''
        status = self.get_status()
        eventgen_status = "running" if status["EVENTGEN_STATUS"] else "stopped"
        host = status["EVENTGEN_HOST"]
        configured = status["CONFIGURED"]
        config_file = status["CONFIG_FILE"]
        custom_configured = status["CUSTOMCONFIGURED"]
        worker_queue_status = status["QUEUE_STATUS"]["WORKER_QUEUE"]
        sample_queue_status = status["QUEUE_STATUS"]["SAMPLE_QUEUE"]
        output_queue_status = status["QUEUE_STATUS"]["OUTPUT_QUEUE"]

        return home_page.format(host,
                                eventgen_status,
                                configured,
                                custom_configured,
                                config_file,
                                worker_queue_status,
                                sample_queue_status,
                                output_queue_status)

    def status(self):
        self._log.info('Status method called.')
        return json.dumps(self.get_status(), indent=4)

    def start(self):
        self._log.info("start method called. Config is {}".format(self.eventgen_dependency.configfile))
        try:
            if not self.eventgen_dependency.configured:
                return "There is not config file known to eventgen. Pass in the config file to /conf before you start."
            if self.eventgen_dependency.eventgen.check_running():
                return "Eventgen already started."
            self.eventgen_dependency.eventgen.start(join_after_start=False)
            return "Eventgen has successfully started."
        except Exception as e:
            self._log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def stop(self):
        self._log.info("stop method called")
        try:
            if self.eventgen_dependency.eventgen.check_running():
                self.eventgen_dependency.eventgen.stop()
                return "Eventgen is stopped."
            return "There is no eventgen process running."
        except Exception as e:
            self._log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def restart(self):
        self._log.info("restart method called.")
        self.stop()
        time.sleep(2)
        self.start()

    def get_conf(self):
        self._log.info("get_conf method called.")
        try:
            if self.eventgen_dependency.configured:
                config = ConfigParser.ConfigParser()
                config.optionxform = str
                config_path = self.eventgen_dependency.configfile
                if os.path.isfile(config_path):
                    config.read(config_path)
                    out_json = dict()
                    for section in config.sections():
                        out_json[section] = dict()
                        for k, v in config.items(section):
                            out_json[section][k] = v
                    self._log.info(out_json)
                    return json.dumps(out_json, indent=4)
            return "N/A"
        except Exception as e:
            self._log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def set_conf(self, configfile=None, custom_config_json={}):
        '''

        customconfig data format
        {sample: {key: value}, sample2: {key: value}}
        '''
        self._log.info("set_conf method called")
        try:
            if configfile and os.path.isfile(os.path.abspath(os.path.join(EVENTGEN_DIR, configfile))):
                modified_path_configfile = os.path.join('..', configfile)
                self.eventgen_dependency.eventgen.reload_conf(modified_path_configfile)
                self.eventgen_dependency.configured = True
                self.eventgen_dependency.customconfigured = False
                self.eventgen_dependency.configfile = configfile
                msg = 'Loaded the conf file: {}'.format(configfile)
                self._log.info(msg)
                return msg
            elif custom_config_json:
                config = ConfigParser.ConfigParser()
                config.optionxform = str
                custom_config_json = json.loads(custom_config_json)
                for sample in custom_config_json.iteritems():
                    sample_name = sample[0]
                    sample_key_value_pairs = sample[1]
                    config.add_section(sample_name)
                    for pair in sample_key_value_pairs.iteritems():
                        config.set(sample_name, pair[0], pair[1])
                with open(CUSTOM_CONFIG_PATH, 'wb') as customconfigfile:
                    config.write(customconfigfile)
                self.eventgen_dependency.configured = True
                self.eventgen_dependency.customconfigured = True
                self.eventgen_dependency.configfile = CUSTOM_CONFIG_PATH
                self.eventgen_dependency.eventgen.reload_conf(CUSTOM_CONFIG_PATH)
                self._log.info("custom_config_json is {}".format(custom_config_json))
                return 'Loaded the custom conf file: {}'.format(CUSTOM_CONFIG_PATH)
        except Exception as e:
            self._log.exception(e)
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
        if payload['type'] == 'configfile':
            return self.set_conf(configfile=payload['data'])
        elif payload['type'] == 'custom_config_json':
            return self.set_conf(custom_config_json=payload['data'])

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
        if payload['type'] == 'configfile':
            return self.set_conf(configfile=payload['data'])
        elif payload['type'] == 'custom_config_json':
            return self.set_conf(custom_config_json=payload['data'])


    ##############################################
    ################ HTTP Methods ################
    ##############################################

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
        for pair in request.values.lists():
            if pair[0] == "configfile":
                return self.set_conf(configfile=pair[1][0])
            elif "custom_config_json" in pair[0]:
                return self.set_conf(custom_config_json=pair[1][0])
        else:
            self._log.exception(e)
            return '400', 'Please pass the valid parameters.'
