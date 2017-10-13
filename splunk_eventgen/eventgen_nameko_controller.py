from nameko.rpc import rpc
from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.web.handlers import http
import nameko

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
    def set_conf(self, nodes, configfile):
        try:
            if nodes == "all":
                self.dispatch("all_set_conf", configfile)
            else:
                self.dispatch("{}_set_conf".format(nodes), configfile)
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
        else:
            return '400', 'POST body should be configfile=YOUR_CONFIG_FILE.'

    ##############################################
    ############### Helper Methods ###############
    ##############################################

    def get_nodes(self, request):
        for pair in request.values.lists():
            if pair[0] == "nodes":
                return pair[1][0]
        return "all"
