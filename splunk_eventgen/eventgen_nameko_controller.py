from nameko.rpc import rpc
from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.web.handlers import http
import ConfigParser
import logging
import os
import socket
from logger.logger_config import controller_logger_config
from logger import splunk_hec_logging_handler
import time
import json

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
EVENTGEN_ENGINE_CONF_PATH = os.path.abspath(os.path.join(FILE_PATH, "default", "eventgen_engine.conf"))

def get_hec_info_from_conf():
    hec_info = [None, None]
    config = ConfigParser.ConfigParser()
    if os.path.isfile(EVENTGEN_ENGINE_CONF_PATH):
        config.read(EVENTGEN_ENGINE_CONF_PATH)
        hec_info[0] = config.get('heclogger', 'hec_url', 1)
        hec_info[1] = config.get('heclogger', 'hec_key', 1)
    return hec_info

class EventgenController(object):
    name = "eventgen_controller"

    dispatch = EventDispatcher()
    PAYLOAD = 'Payload'
    logging.config.dictConfig(controller_logger_config)
    log = logging.getLogger(name)
    hec_info = get_hec_info_from_conf()
    handler = splunk_hec_logging_handler.SplunkHECHandler(targetserver=hec_info[0], hec_token=hec_info[1], eventgen_name=name)
    log.addHandler(handler)
    log.info("Logger set as eventgen_controller")

    server_status = {}
    server_confs = {}

    ##############################################
    ################ RPC Methods #################
    ##############################################

    @event_handler("eventgen_listener", "server_status", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_server_status(self, payload):
        return self.receive_status(payload)

    @event_handler("eventgen_listener", "server_conf", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_server_conf(self, payload):
        return self.receive_conf(payload)

    @rpc
    def index(self, target):
        try:
            if target == "all":
                self.dispatch("all_index", self.PAYLOAD)
            else:
                self.dispatch("{}_index".format(target), self.PAYLOAD)
            self.log.info("Index event dispatched to {}".format(target))
            return "Index event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def status(self, target):
        try:
            if target == "all":
                self.dispatch("all_status", self.PAYLOAD)
            else:
                self.dispatch("{}_status".format(target), self.PAYLOAD)
            self.log.info("Status event dispatched to {}".format(target))
            return "Status event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def start(self, target):
        try:
            if target == "all":
                self.dispatch("all_start", self.PAYLOAD)
            else:
                self.dispatch("{}_start".format(target), self.PAYLOAD)
            self.log.info("Start event dispatched to {}".format(target))
            return "Start event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def stop(self, target):
        try:
            if target == "all":
                self.dispatch("all_stop", self.PAYLOAD)
            else:
                self.dispatch("{}_stop".format(target), self.PAYLOAD)
            self.log.info("Stop event dispatched to {}".format(target))
            return "Stop event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def restart(self, target):
        try:
            if target == "all":
                self.dispatch("all_restart", self.PAYLOAD)
            else:
                self.dispatch("{}_restart".format(target), self.PAYLOAD)
            self.log.info("Restart event dispatched to {}".format(target))
            return "Restart event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def get_conf(self, target):
        try:
            if target == "all":
                self.dispatch("all_get_conf", self.PAYLOAD)
            else:
                self.dispatch("{}_get_conf".format(target), self.PAYLOAD)
            self.log.info("Get_conf event dispatched to {}".format(target))
            return "Get_conf event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def set_conf(self, target, data):
        try:
            payload = data
            if target == "all":
                self.dispatch("all_set_conf", payload)
            else:
                self.dispatch("{}_set_conf".format(target), payload)
            self.log.info("Set_conf event dispatched to {}".format(target))
            return "Set_conf event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def edit_conf(self, target, data):
        try:
            print data
            payload = data
            if target == "all":
                self.dispatch("all_edit_conf", payload)
            else:
                self.dispatch("{}_edit_conf".format(target), payload)
            self.log.info("Edit_conf event dispatched to {}".format(target))
            return "Edit_conf event dispatched to {}".format(target)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def bundle(self, nodes, payload):
        url = None
        try:
            payload = json.loads(payload)
            url = payload["url"]
        except ValueError:
            url = payload
        if not url:
            self.log.error("No URL specified in /bundle POST")
        try:
            if nodes == "all":
                self.dispatch("all_bundle", {"url": url})
            else:
                self.dispatch("{}_bundle".format(nodes), {"url": url})
            msg = "Bundle event dispatched to {} with url {}".format(nodes, url)
            self.log.info(msg)
            return msg
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    ##############################################
    ################ HTTP Methods ################
    ##############################################

    @http('GET', '/')
    def root_page(self, request):
        self.log.info("index method called")
        home_page = '''*** Eventgen Controller ***
Host: {0}
You are running Eventgen Controller.\n'''
        host = socket.gethostname()
        return home_page.format(host)

    @http('GET', '/index')
    def http_index(self, request):
        self.index(target=self.get_target(request))
        return self.root_page(request)

    @http('GET', '/status')
    def http_status(self, request):
        self.status(target=self.get_target(request))
        time.sleep(0.5)
        return self.format_status()

    @http('POST', '/start')
    def http_start(self, request):
        return self.start(target=self.get_target(request))

    @http('POST', '/stop')
    def http_stop(self, request):
        return self.stop(target=self.get_target(request))

    @http('POST', '/restart')
    def http_restart(self, request):
        return self.restart(target=self.get_target(request))

    @http('GET', '/conf')
    def http_get_conf(self, request):
        self.get_conf(target=self.get_target(request))
        time.sleep(0.5)
        return self.format_confs()

    @http('POST', '/conf')
    def http_set_conf(self, request):
        data = request.get_data()
        if data:
            self.set_conf(target=self.get_target(request), data=data)
            return self.http_get_conf(request)
        else:
            return '400', 'Please pass valid config data.'

    @http('PUT', '/conf')
    def http_edit_conf(self, request):
        data = request.get_data()
        if data:
            self.edit_conf(target=self.get_target(request), data=data)
            return self.http_get_conf(request)
        else:
            return '400', 'Please pass valid config data.'

    #http('POST', '/bundle')
    def http_bundle(self, request):
        payload = request.get_data(as_text=True)
        self.log.info(payload)
        self.log.info(json.loads(payload))
        return self.bundle(nodes=self.get_nodes(request), payload=request.get_data(as_text=True))

    ##############################################
    ############### Helper Methods ###############
    ##############################################

    def get_target(self, request):
        data = request.get_data()
        if data:
            data = json.loads(data)
        if 'target' in data:
            return data['target']
        else:
            return "all"

    def receive_status(self, data):
        if data['server_name'] and data['server_status']:
            self.server_status[data['server_name']] = data['server_status']

    def receive_conf(self, data):
        if data['server_name'] and data['server_conf']:
            print data, '**'
            self.server_confs[data['server_name']] = data['server_conf']

    def format_status(self):
        return json.dumps(self.server_status, indent=4)
<<<<<<< HEAD
=======

    def format_confs(self):
        return json.dumps(self.server_confs, indent=4)

>>>>>>> schema_change
