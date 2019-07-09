import atexit
from flask import Blueprint, Response, request
from pyrabbit.api import Client
import os
import socket
import time
import json
import requests
import logging

from api_types import ApiTypes
from api_blueprint import ApiBlueprint


def exit_handler(client, hostname, logger):
    client.delete_vhost(hostname)
    # logger.info("Deleted vhost {}. Shutting down.".format(hostname))

class Servers():
    def __init__(self):
        self.servers = set()

    def register(self, hostname):
        if hostname != None:
            print('adding server with hostname {}...'.format(hostname))
            self.servers.add(hostname)
            print('new servers set is {}'.format(self.servers))
            return self.servers
        else:
            raise Exception('ip can\'t be None')

    def __call(self, hostname, verb, method, body=None, headers=None):
        action = getattr(requests, verb, None)
        if action:
            action(headers=self.headers, url='http://{0}:{1}/{2}'.format(hostname, 9500, method))

    def status(self, target):
        if target == "all":
            for server in self.servers:
                self.__call(server, 'GET', 'status')
        else:
            pass            

class EventgenControllerAPI(ApiBlueprint):

    def __init__(self):
        ApiBlueprint.__init__(self)
        self.bp = self.__create_blueprint()
        
        self.name = "eventgen_controller"
        self.servers = Servers()
        # logging.config.dictConfig(controller_logger_config)
        log = logging.getLogger(self.name)
        log.info("Logger set as eventgen_controller")

        ### self.__setup_pyrabbit()

        ### Garbage #### atexit.register(exit_handler, client=self.pyrabbit_cl, hostname=self.host, logger=None)#log)

    def __create_blueprint(self):
        bp = Blueprint('api', __name__)

        # define apis
        @bp.route('/ping')
        def ping():
            return 'I\'m here!'

        @bp.route('/register', methods=['POST'])
        def register_server():
            print('test')
            data = request.get_json(force=True) #should this be force?
            self.servers.register(data['hostname'])
            return 'successfully registered hostname'

        @bp.route('/status', methods=['GET'])
        def all_status():
            print('test')
            return json.dumps(self.__get_rpc_responses(ApiTypes.status))
        return bp





    ### Garbage can ###


    def __setup_pyrabbit(self):
        self.host = 'controller' #socket.gethostname() + '_controller'
        self.exchangeName = 'requests'

        osvars, config = dict(os.environ), {}
        config["AMQP_HOST"] = osvars.get("EVENTGEN_AMQP_HOST", "localhost")
        config["AMQP_WEBPORT"] = osvars.get("EVENTGEN_AMQP_WEBPORT", 15672)
        config["AMQP_USER"] = osvars.get("EVENTGEN_AMQP_URI", "guest")
        config["AMQP_PASS"] = osvars.get("EVENTGEN_AMQP_PASS", "guest")

        print('make client...')
        self.pyrabbit_cl = Client('{0}:{1}'.format(config['AMQP_HOST'], config['AMQP_WEBPORT']),
                            '{0}'.format(config['AMQP_USER']), '{0}'.format(config['AMQP_PASS']))
        rabbit_started = False
        while(not rabbit_started):
            try:
                print('is this alive?...')
                print(self.pyrabbit_cl.is_alive())
                rabbit_started = True
            except:
                rabbit_started = False
        print('create vhost with hostname{}...'.format(self.host))
        print(Client.json_headers)
        self.pyrabbit_cl.create_vhost(self.host)
        print('create exchange...')
        self.pyrabbit_cl.create_exchange(self.host, self.exchangeName, 'fanout')
        print('create queue...')
        self.queue_name = 'controller_queue'
        self.pyrabbit_cl.create_queue(self.host, self.queue_name)
        # log.info("Vhost set to {}".format(host))
        # log.info("Current Vhosts are {}".format(pyrabbit_cl.get_vhost_names()))

    def __get_rpc_responses(self, apiType, servers='all', num_retries=15, delay=0.3):
        print(apiType.value)
        self.pyrabbit_cl.publish(self.host, self.exchangeName, '', apiType.value, 'string', {'reply_to': 'controller_queue'})
        messages = []
        servers = self.get_current_server_vhosts()
        current_retries = 0
        while len(messages) < len(servers) and current_retries < num_retries:
            time.sleep(delay)
            messages.append(self.pyrabbit_cl.get_messages(self.host, self.queue_name))
            current_retries += 1
        return messages

    def get_current_server_vhosts(self):
        current_vhosts = self.pyrabbit_cl.get_vhost_names()
        return [name for name in current_vhosts if name != '/' and name != self.host]