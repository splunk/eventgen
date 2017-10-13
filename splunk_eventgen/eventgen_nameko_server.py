from nameko.web.handlers import http
from nameko.events import EventDispatcher, event_handler, BROADCAST
import ConfigParser
import yaml
import json
import os
import socket
import time
import eventgen_nameko_dependency

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
EVENTGEN_DIR = os.path.realpath(os.path.join(FILE_PATH, ".."))

def get_eventgen_name_from_conf():
    with open(os.path.abspath(os.path.join(FILE_PATH, "listener_conf.yml"))) as config_yml:
        loaded_yml = yaml.load(config_yml)
        return loaded_yml['EVENTGEN_NAME'] if 'EVENTGEN_NAME' in loaded_yml else 'Noname'

class EventgenListener:
    name = "eventgen_listner"

    eventgen_dependency = eventgen_nameko_dependency.EventgenDependency()
    eventgen_name = get_eventgen_name_from_conf()
    print "Eventgen_name is {}".format(eventgen_name)

    def __init__(self):
        self.host = socket.gethostname()

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
        print "index method called"
        home_page = '''
        <h1>Eventgen WSGI</h1>
        <p>Host: {0}</p>
        <p>Eventgen Status: {1}</p>
        <p>Eventgen Config file exists: {2}</p>
        <p>Eventgen Config file path: {3}</p>
        <p>Worker Queue Status: {4}</p>
        <p>Sample Queue Status: {5}</p>
        <p>Output Queue Status: {6}</p>
        '''
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
        print 'Status method called.'
        return json.dumps(self.get_status(), indent=4)

    def start(self):
        print "start method called. Config is {}".format(self.eventgen_dependency.configfile)
        try:
            if not self.eventgen_dependency.configured:
                return "There is not config file known to eventgen. Pass in the config file to /conf before you start."
            if self.eventgen_dependency.eventgen.check_running():
                return "Eventgen already started."
            self.eventgen_dependency.eventgen.start(join_after_start=False)
            return "Eventgen has successfully started."
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    def stop(self):
        print "stop method called"
        try:
            if self.eventgen_dependency.eventgen.check_running():
                self.eventgen_dependency.eventgen.stop()
                return "Eventgen is stopped."
            return "There is no eventgen process running."
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    def restart(self):
        print "restart method called."
        self.stop()
        time.sleep(2)
        self.start()

    def get_conf(self):
        print "get_conf method called."
        try:
            if self.eventgen_dependency.configured:
                config = ConfigParser.ConfigParser()
                config.read(os.path.abspath(os.path.join(EVENTGEN_DIR, self.eventgen_dependency.configfile)))
                out_json = dict()
                for section in config.sections():
                    out_json[section] = dict()
                    for k, v in config.items(section):
                        out_json[section][k] = v
                return json.dumps(out_json, indent=4)
            return "N/A"
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    def set_conf(self, configfile=None):
        print configfile
        print "set_conf method called"
        if not configfile or not os.path.isfile(os.path.abspath(os.path.join(EVENTGEN_DIR, configfile))):
            return 'Provide the correct config file.'
        else:
            try:
                modified_path_configfile = os.path.join('..', configfile)
                self.eventgen_dependency.eventgen.reload_conf(modified_path_configfile)
                self.eventgen_dependency.configfile = configfile
                self.eventgen_dependency.configured = True
                return 'Loaded the conf file: {}'.format(configfile)
            except Exception as e:
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
        return self.set_conf(configfile=payload)

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
        return self.set_conf(configfile=payload)


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
        else:
            return '404', 'POST body should be configfile=YOUR_CONFIG_FILE.'


