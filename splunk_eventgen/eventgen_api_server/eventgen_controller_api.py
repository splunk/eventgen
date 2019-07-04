from flask import Blueprint
from pyrabbit.api import Client
import os
import socket
import time

from api_types import ApiTypes
from api_blueprint import ApiBlueprint

class EventgenControllerAPI(ApiBlueprint):

    def __init__(self):
        ApiBlueprint.__init__(self)
        self.bp = self.__create_blueprint()
        self.exchangeName = 'requests'
        # connection = pika.BlockingConnection(pika.ConnectionParameters('localhost')) # how do I get the correct address?
        # self.channel = connection.channel()
        # self.channel.exchange_declare(exchange=self.exchangeName, exchange_type='fanout')
        # self.controller_queue = self.channel.queue_declare(queue='controller_queue')
        
        self.name = "eventgen_controller"

        # logging.config.dictConfig(controller_logger_config)
        # log = logging.getLogger(name)
        # log.info("Logger set as eventgen_controller")
        self.host = socket.gethostname() + '_controller'

        osvars, config = dict(os.environ), {}
        config["AMQP_HOST"] = osvars.get("EVENTGEN_AMQP_HOST", "localhost")
        config["AMQP_WEBPORT"] = osvars.get("EVENTGEN_AMQP_WEBPORT", 15672)
        config["AMQP_USER"] = osvars.get("EVENTGEN_AMQP_URI", "guest")
        config["AMQP_PASS"] = osvars.get("EVENTGEN_AMQP_PASS", "guest")

        print('make client...')
        self.pyrabbit_cl = Client('{0}:{1}'.format(config['AMQP_HOST'], config['AMQP_WEBPORT']),
                            '{0}'.format(config['AMQP_USER']), '{0}'.format(config['AMQP_PASS']))
        print('create vhost...')
        self.pyrabbit_cl.create_vhost(self.host)
        print('create exchange...')
        self.pyrabbit_cl.create_exchange(self.host, self.exchangeName, 'fanout')
        print('create queue...')
        self.pyrabbit_cl.create_queue(self.host, 'controller_queue')
        # log.info("Vhost set to {}".format(host))
        # log.info("Current Vhosts are {}".format(pyrabbit_cl.get_vhost_names()))

        atexit.register(exit_handler, client=pyrabbit_cl, hostname=host, logger=log)

    def __create_blueprint(self):
        bp = Blueprint('api', __name__)

        # define apis
        @bp.route('/status', methods=['GET'])
        def all_status():
            print('test')
            return self.__get_rpc_responses(ApiTypes.status)
        return bp

    def __get_rpc_responses(self, apiType, servers='all', num_retries=15, delay=0.3):
        self.pyrabbit_cl.publish(self.host, self.exchangeName, '', apiType, 'string', {reply_to: 'controller_queue'}, body=ApiTypes.status)
        messages = []
        servers = get_current_server_vhosts()
        current_retries = 0
        while len(messages) < len(servers) and current_retries < num_retries:
            time.sleep(delay)
            messages.concat(self.pyrabbit_cl.get_messages(self.host))
            current_retries += 1
        return messages

    def get_current_server_vhosts(self):
        current_vhosts = self.pyrabbit_cl.get_vhost_names()
        return [name for name in current_vhosts if name != '/' and name != self.host]