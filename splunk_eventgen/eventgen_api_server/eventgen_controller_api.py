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
import ast
try:
    from requests import Session
    from requests_futures.sessions import FuturesSession
    from concurrent.futures import ThreadPoolExecutor
except:
    raise Exception("couldn't import our own stuff?")

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
LOG_PATH = os.path.join(FILE_PATH, '..', 'logs')

def exit_handler(client, hostname, logger):
    client.delete_vhost(hostname)
    # logger.info("Deleted vhost {}. Shutting down.".format(hostname))

class Servers():
    def __init__(self):
        self.servers = set()
        self.logger = logging.getLogger("eventgen_server")
        self.session = FuturesSession(session=Session(), executor=ThreadPoolExecutor(max_workers=20))
        self.port = 9500

    def registeredServersList(self):
        return list(self.servers)

    def isRegistered(self, hostname):
        if hostname != None:
            return hostname in self.servers
        else:
            return False

    def register(self, hostname):
        if hostname != None:
            self.servers.add(hostname)
            return self.servers
        else:
            raise Exception('ip can\'t be None')

    def __single_call(self, hostname, verb, method, body=None, headers=None, retries=1, interval=1):
        action = getattr(requests, verb, None)
        if action:
            osvars, config = dict(os.environ), {}
            response = action(headers=headers, url='http://{0}:{1}/{2}'.format(hostname, self.port, method), data=json.dumps(body))
            if response.status_code == 200:
                return response.json()
            else:
                raise(Exception('Server returned a bad status'))


    def __async_multi_call(self, hostnames, verb, method, body=None, headers=None, retries=1, interval=1):
        action = getattr(self.session, verb, None)
        if action:
            active_sessions = []
            for hostname in hostnames:
                osvars, config = dict(os.environ), {}
                active_sessions.append(action(headers=headers, url='http://{0}:{1}/{2}'.format(hostname, self.port, method), data=json.dumps(body)))
            response_data = []
            failed_requests = []
            for session in active_sessions:
                try:
                    response = session.result()
                    if not response.raise_for_status():
                        try:
                            response_data.append(response.json())
                        except:
                            response_data.append(response.content)
                        self.logger.debug("Payload successfully sent to httpevent server.")
                    else:
                        self.logger.error("Server returned an error while trying to send, response code: %s" %
                                            response.status_code)
                        raise BadConnection(
                            "Server returned an error while sending, response code: %s" % response.status_code)
                except Exception as e:
                    failed_requests.append(session)
            return response_data
        else:
            return verb + ' is not a valid verb'

    def __call(self, target, verb, method, body=None, headers=None, retries=1, interval=1):
        if target == "all":
            responses = self.__async_multi_call(self.servers, verb, method, body, headers, retries, interval)
            return responses
        else:
            response = self.__single_call(target, verb, method, body, headers, retries, interval)
            return response

    def index(self, target):
        return self.__call(target, 'get', 'index')

    def status(self, target):
        return self.__call(target, 'get', 'status')

    def get_conf(self, target):
        return self.__call(target, 'get', 'conf')

    def set_conf(self, target, body):
        return self.__call(target, 'post', 'conf', body=body)

    def update_conf(self, target, body):
        return self.__call(target, 'put', 'conf', body=body)

    def set_bundle(self, target, body):
        return self.__call(target, 'post', 'bundle', body=body)

    def start(self, target):
        return self.__call(target, 'post', 'start')

    def stop(self, target, body):
        return self.__call(target, 'post', 'stop', body=body)

    def restart(self, target):
        return self.__call(target, 'post', 'restart')

    def reset(self, target):
        return self.__call(target, 'post', 'reset')

    def get_volume(self, target):
        return self.__call(target, 'get', 'volume')

    def set_volume(self, target, body):
        return self.__call(target, 'post', 'volume', body=body)


class EventgenControllerAPI(ApiBlueprint):

    def __init__(self):
        ApiBlueprint.__init__(self)
        self.bp = self.__create_blueprint()

        self.servers = Servers()
        # logging.config.dictConfig(controller_logger_config)
        self._setup_loggers()
        self.logger = logging.getLogger("eventgen_controller")
        self.logger.info("Logger set as eventgen_controller")

        ### self.__setup_pyrabbit()

        ### Garbage #### atexit.register(exit_handler, client=self.pyrabbit_cl, hostname=self.host, logger=None)#log)
    
    def _setup_loggers(self):
        log_path = os.path.join(FILE_PATH, 'logs')
        eventgen_controller_logger_path = os.path.join(LOG_PATH, 'eventgen-controller.log')
        eventgen_error_logger_path = os.path.join(LOG_PATH, 'eventgen-error.log')
        
        log_format = '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        detailed_formatter = logging.Formatter(log_format, datefmt=date_format)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(detailed_formatter)
        console_handler.setLevel(logging.DEBUG)

        eventgen_controller_file_handler = logging.handlers.RotatingFileHandler(eventgen_controller_logger_path, maxBytes=2500000, backupCount=20)
        eventgen_controller_file_handler.setFormatter(detailed_formatter)
        eventgen_controller_file_handler.setLevel(logging.DEBUG)

        error_file_handler = logging.handlers.RotatingFileHandler(eventgen_error_logger_path, maxBytes=2500000, backupCount=20)
        error_file_handler.setFormatter(detailed_formatter)
        error_file_handler.setLevel(logging.ERROR)

        logger = logging.getLogger('eventgen_controller')
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.handlers = []
        logger.addHandler(eventgen_controller_file_handler)
        logger.addHandler(console_handler)
        logger.addHandler(error_file_handler)

    def __create_blueprint(self):
        bp = Blueprint('api', __name__)

        # define apis
        @bp.route('/ping')
        def ping():
            return 'I\'m here!'

        @bp.route('/register', methods=['POST'])
        def register_server():
            data = request.get_json(force=True) #should this be force?
            self.servers.register(data['hostname'])
            return 'successfully registered hostname'

        @bp.route('/index', methods=['GET'])
        def index():
            home_page = '''*** Eventgen Controller ***
Host: {0}
Connected Servers: {1}
You are running Eventgen Controller.\n'''
            host = socket.gethostname()
            return home_page.format(host, self.servers.registeredServersList())

        @bp.route('/status', methods=['GET'])
        def all_status():
            return json.dumps(self.servers.status('all'))

        @bp.route('/status/<string:target>', methods=['GET'])
        def http_status_target(target="all"):
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.status(target))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/conf', methods=['GET'])
        def http_get_conf():
            return json.dumps(self.servers.get_conf('all'), indent=4)

        @bp.route('/conf/<string:target>', methods=['GET'])
        def http_get_conf_target(target="all"):
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.get_conf(target))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/conf', methods=['POST'])
        def http_set_conf():
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass valid config data.")
            
            return json.dumps(self.servers.set_conf(target="all", body=data))

        @bp.route('/conf/<string:target>', methods=['POST'])
        def http_set_conf_target(target):
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass valid config data.")

            if self.servers.isRegistered(target):
                return json.dumps(self.servers.set_conf(target=target, body=data))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/conf', methods=['PUT'])
        def http_update_conf():
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass valid config data.")

            return json.dumps(self.servers.update_conf(target="all", body=data))

        @bp.route('/conf/<string:target>', methods=['PUT'])
        def http_update_conf_target(target):
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass valid config data.")
                
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.update_conf(target=target, body=data))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/bundle', methods=['POST'])
        def http_set_bundle():
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass in a valid object with bundle URL.")

            return json.dumps(self.servers.set_bundle(target="all", body=data))

        @bp.route('/bundle/<string:target>', methods=['POST'])
        def http_set_bundle_target(target):
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass in a valid object with bundle URL.")

            if self.servers.isRegistered(target):
                return json.dumps(self.servers.set_bundle(target=target, body=data))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/setup', methods=['POST'])
        def http_update_setup():
            data = request.get_json()
            return json.dumps(self.servers.set_bundle(target="all", body=data))

        @bp.route('/setup/<string:target>', methods=['POST'])
        def http_update_setup_target(target):
            data = request.get_json()
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.set_bundle(target=target, body=data))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/volume', methods=['GET'])
        def http_get_volume():
            return json.dumps(self.servers.get_volume('all'), indent=4)

        @bp.route('/volume/<string:target>', methods=['GET'])
        def http_get_volume_target(target="all"):
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.get_volume(target))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/volume', methods=['POST'])
        def http_set_volume():
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass in a valid object with volume.")

            return json.dumps(self.servers.set_volume(target="all", body=data))

        @bp.route('/volume/<string:target>', methods=['POST'])
        def http_set_volume_target(target):
            data = None
            try:
                data = request.get_json()
            except:
                return self.__make_error_response(400, "Please pass in a valid object with volume.")
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.set_volume(target=target, body=data))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/start', methods=['POST'])
        def http_start():
            return json.dumps(self.servers.start(target="all"))

        @bp.route('/start/<string:target>', methods=['POST'])
        def http_start_target(target="all"):
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.start(target=target))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/stop', methods=['POST'])
        def http_stop():
            data = request.get_json()
            return json.dumps(self.servers.stop(target="all", body=data))

        @bp.route('/stop/<string:target>', methods=['POST'])
        def http_stop_target(target="all"):
            data = request.get_json()
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.stop(target=target, body=data))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/restart', methods=['POST'])
        def http_restart():
            return json.dumps(self.servers.restart(target="all"))

        @bp.route('/restart/<string:target>', methods=['POST'])
        def http_restart_target(target="all"):
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.restart(target=target))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        @bp.route('/reset', methods=['POST'])
        def http_reset():
            return json.dumps(self.servers.reset(target="all"))

        @bp.route('/reset/<string:target>', methods=['POST'])
        def http_reset_target(target="all"):
            if self.servers.isRegistered(target):
                return json.dumps(self.servers.reset(target=target))
            else:
                return self.__make_error_response(404, json.dumps("Target not available.", indent=4))

        return bp

    def __make_error_response(self, status, message):
        return Response(json.dumps({'message': message}), status=status)
