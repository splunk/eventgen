from nameko.rpc import rpc
from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.web.handlers import http
import ConfigParser
import logging
import os
from logger.logger_config import controller_logger_config
from logger import splunk_hec_logging_handler

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

    ##############################################
    ################ RPC Methods #################
    ##############################################

    @rpc
    def index(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_index", self.PAYLOAD)
            else:
                self.dispatch("{}_index".format(nodes), self.PAYLOAD)
            self.log.info("Index event dispatched to {}".format(nodes))
            return "Index event dispatched to {}".format(nodes)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def status(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_status", self.PAYLOAD)
            else:
                self.dispatch("{}_status".format(nodes), self.PAYLOAD)
            self.log.info("Status event dispatched to {}".format(nodes))
            return "Status event dispatched to {}".format(nodes)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def start(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_start", self.PAYLOAD)
            else:
                self.dispatch("{}_start".format(nodes), self.PAYLOAD)
            self.log.info("Start event dispatched to {}".format(nodes))
            return "Start event dispatched to {}".format(nodes)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def stop(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_stop", self.PAYLOAD)
            else:
                self.dispatch("{}_stop".format(nodes), self.PAYLOAD)
            self.log.info("Stop event dispatched to {}".format(nodes))
            return "Stop event dispatched to {}".format(nodes)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def restart(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_restart", self.PAYLOAD)
            else:
                self.dispatch("{}_restart".format(nodes), self.PAYLOAD)
            self.log.info("Restart event dispatched to {}".format(nodes))
            return "Restart event dispatched to {}".format(nodes)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def get_conf(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_get_conf", self.PAYLOAD)
            else:
                self.dispatch("{}_get_conf".format(nodes), self.PAYLOAD)
            self.log.info("Get_conf event dispatched to {}".format(nodes))
            return "Get_conf event dispatched to {}".format(nodes)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def set_conf(self, nodes, configfile=None, custom_config_json=None):
        try:
            payload = {}
            if configfile:
                payload['type'] = 'configfile'
                payload['data'] = configfile
            elif custom_config_json:
                payload['type'] = 'custom_config_json'
                payload['data'] = custom_config_json
            else:
                self.log.info("Pass in a valid configfile or custom_config_json")
                return "Pass in a valid configfile or custom_config_json"

            if nodes == "all":
                self.dispatch("all_set_conf", payload)
            else:
                self.dispatch("{}_set_conf".format(nodes), payload)
            self.log.info("Set_conf event dispatched to {}".format(nodes))
            return "Set_conf event dispatched to {}".format(nodes)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    ##############################################
    ################ HTTP Methods ################
    ##############################################

    @http('GET', '/index')
    def http_index(self, request):
        self.get_nodes(request)
        return self.index(nodes=self.get_nodes(request))

    @http('GET', '/status')
    def http_status(self, request):
        return self.status(nodes=self.get_nodes(request))

    @http('POST', '/start')
    def http_start(self, request):
        return self.start(nodes=self.get_nodes(request))

    @http('POST', '/stop')
    def http_stop(self, request):
        return self.stop(nodes=self.get_nodes(request))

    @http('POST', '/restart')
    def http_restart(self, request):
        return self.restart(nodes=self.get_nodes(request))

    @http('GET', '/conf')
    def http_get_conf(self, request):
        return self.get_conf(nodes=self.get_nodes(request))

    @http('POST', '/conf')
    def http_set_conf(self, request):
        for pair in request.values.lists():
            print pair, type(pair[0])
            if "configfile" == pair[0]:
                return self.set_conf(nodes=self.get_nodes(request), configfile=pair[1][0])
            elif "custom_config_json" == pair[0]:
                return self.set_conf(nodes=self.get_nodes(request), custom_config_json=pair[1][0])
        return '400', 'Please pass the valid parameters.'

    ##############################################
    ############### Helper Methods ###############
    ##############################################

    def get_nodes(self, request):
        for pair in request.values.lists():
            if pair[0] == "nodes":
                return pair[1][0]
        return "all"
