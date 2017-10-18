from nameko.rpc import rpc
from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.web.handlers import http

class EventgenController(object):
    name = "eventgen_controller"

    dispatch = EventDispatcher()
    PAYLOAD = 'Payload'

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
            return "Index event dispatched to {}".format(nodes)
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    @rpc
    def status(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_status", self.PAYLOAD)
            else:
                self.dispatch("{}_status".format(nodes), self.PAYLOAD)
            return "Status event dispatched to {}".format(nodes)
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    @rpc
    def start(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_start", self.PAYLOAD)
            else:
                self.dispatch("{}_start".format(nodes), self.PAYLOAD)
            return "Start event dispatched to {}".format(nodes)
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    @rpc
    def stop(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_stop", self.PAYLOAD)
            else:
                self.dispatch("{}_stop".format(nodes), self.PAYLOAD)
            return "Stop event dispatched to {}".format(nodes)
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    @rpc
    def restart(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_restart", self.PAYLOAD)
            else:
                self.dispatch("{}_restart".format(nodes), self.PAYLOAD)
            return "Restart event dispatched to {}".format(nodes)
        except Exception as e:
            return '500', "Exception: {}".format(e.message)

    @rpc
    def get_conf(self, nodes):
        try:
            if nodes == "all":
                self.dispatch("all_get_conf", self.PAYLOAD)
            else:
                self.dispatch("{}_get_conf".format(nodes), self.PAYLOAD)
            return "Get_conf event dispatched to {}".format(nodes)
        except Exception as e:
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
                return "Pass in a valid configfile or custom_config_json"

            if nodes == "all":
                self.dispatch("all_set_conf", payload)
            else:
                self.dispatch("{}_set_conf".format(nodes), payload)
            return "Set_conf event dispatched to {}".format(nodes)
        except Exception as e:
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
            if pair[0] == "configfile":
                return self.set_conf(nodes=self.get_nodes(request), configfile=pair[1][0])
            elif "custom_config_json" in pair[0]:
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
