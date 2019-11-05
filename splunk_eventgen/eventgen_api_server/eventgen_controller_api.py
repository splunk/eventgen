import atexit
from flask import Blueprint, Response, request
import os
import socket
import time
import json
import requests
import logging

INTERNAL_ERROR_RESPONSE = json.dumps({"message": "Internal Error Occurred"})

class EventgenControllerAPI():

    def __init__(self, redis_connector, host):
        self.bp = self.__create_blueprint()
        self.redis_connector = redis_connector
        self.host = host

        self.logger = logging.getLogger("eventgen_controller")
        self.logger.info("Initialized the EventgenControllerAPI Blueprint")

        self.interval = 0.001
    
    def get_blueprint(self):
        return self.bp
    
    def __create_blueprint(self):
        bp = Blueprint('api', __name__)

        def format_message(job, request_method, body=None, target='all'):
            return json.dumps({'job': job, 'target': target, 'body': body, 'request_method': request_method})
        
        def gather_response(response_number_target=0):
            response = {}
            if not response_number_target:
                response_number_target = int(self.redis_connector.message_connection.pubsub_numsub(self.redis_connector.servers_channel)[0][1])
            response_num = 0
            countdown = 60 / self.interval
            for i in range(0, int(countdown)):
                if response_num == response_number_target:
                    break
                else:
                    time.sleep(self.interval)
                    message = self.redis_connector.pubsub.get_message()
                    if message and type(message.get('data')) == str:
                        status_response = json.loads(message.get('data'))
                        response[status_response['host']] = status_response['response']
                        response_num += 1
            return response

        @bp.route('/index', methods=['GET'])
        def index():
            home_page = '''*** Eventgen Controller ***
Host: {0}
Connected Servers: {1}
You are running Eventgen Controller.\n'''
            host = self.host
            return home_page.format(host, self.redis_connector.get_registered_servers())

        @bp.route('/status', methods=['GET'])
        def http_all_status():
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('status', request.method, target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/status/<string:target>', methods=['GET'])
        def http_target_status(target):
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('status', request.method, target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/conf', methods=['GET', 'POST', 'PUT'])
        def http_all_conf():
            try:
                body = None if request.method == 'GET' else request.get_json(force=True)
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('conf', request.method, body=body, target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/conf/<string:target>', methods=['GET', 'POST', 'PUT'])
        def http_target_conf(target):
            try:
                body = None if request.method == 'GET' else request.get_json(force=True)
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('conf', request.method, body=body, target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/bundle', methods=['POST'])
        def http_all_bundle():
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('bundle', request.method, body=request.get_json(force=True), target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/bundle/<string:target>', methods=['POST'])
        def http_target_bundle(target):
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('bundle', request.method, body=request.get_json(force=True), target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/setup', methods=['POST'])
        def http_all_setup():
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('setup', request.method, body=request.get_json(force=True), target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/setup/<string:target>', methods=['POST'])
        def http_target_setup(target):
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('setup', request.method, body=request.get_json(force=True), target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/volume', methods=['GET', 'POST'])
        def http_all_volume():
            try:
                body = None if request.method == 'GET' else request.get_json(force=True)
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('volume', request.method, body=body, target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/volume/<string:target>', methods=['GET', 'POST'])
        def http_target_volume(target):
            try:
                body = None if request.method == 'GET' else request.get_json(force=True)
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('volume', request.method, body=body, target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/start', methods=['POST'])
        def http_all_start():
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('start', request.method, target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/start/<string:target>', methods=['POST'])
        def http_target_start(target):
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('start', request.method, target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/stop', methods=['POST'])
        def http_all_stop():
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('stop', request.method, target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/stop/<string:target>', methods=['POST'])
        def http_target_stop(target):
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('stop', request.method, target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/restart', methods=['POST'])
        def http_all_restart():
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('restart', request.method, target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/restart/<string:target>', methods=['POST'])
        def http_target_restart(target):
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('restart', request.method, target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/reset', methods=['POST'])
        def http_all_reset():
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('reset', request.method, target='all'))
                return Response(json.dumps(gather_response()), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
        
        @bp.route('/reset/<string:target>', methods=['POST'])
        def http_target_reset(target):
            try:
                self.redis_connector.message_connection.publish(self.redis_connector.servers_channel, format_message('reset', request.method, target=target))
                return Response(json.dumps(gather_response(response_number_target=1)), mimetype='application/json', status=200)
            except Exception as e:
                self.logger.error(e)
                return Response(INTERNAL_ERROR_RESPONSE, mimetype='application/json', status=500)
            
        return bp

    def __make_error_response(self, status, message):
        return Response(json.dumps({'message': message}), status=status)
