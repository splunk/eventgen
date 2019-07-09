from flask import Flask
import os
import threading
import socket
import logging
import json
import time

from eventgen_server_api import EventgenServerAPI
from constants import Constants

consts = Constants()

class EventgenServer():

    def __init__(self, *args, **kwargs):        
        self.app = self._create_app()
        self.mode = kwargs.get('mode', 'standalone')
        self.port = 9500
        self.host = socket.gethostname()

        self.logger = logging.getLogger('eventgen_server')
        self.logger.info(self.host)

    def app_run(self):
        osvars, config = dict(os.environ), {}
        domain = osvars.get("EVENTGEN_CONTROLLER", "localhost")
        if self.mode != 'standalone':
            self._create_health_check()
        self.app.run(host="0.0.0.0", port=self.port, threaded=True)
    
    def _create_app(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'does-not-exist'

        app.register_blueprint(EventgenServerAPI().get_blueprint())

        @app.route('/')
        def index():
            return "helloworld"
            
        return app

    def _create_health_check(self):
        def health_check():
            while True:
                self.reRegister()
                time.sleep(consts.PING_TIME) # need a time interval for this
            
        thread = threading.Thread(target=health_check)
        thread.daemon = True
        thread.start()

    def reRegister(self):
        osvars, config = dict(os.environ), {}
        config["EVENTGEN_CONTROLLER"] = osvars.get("EVENTGEN_CONTROLLER", "localhost")
        self.logger.info(config["EVENTGEN_CONTROLLER"])
        payload = {'hostname': self.host}
        data = json.dumps(payload)
        headers = {'content-type': 'application/json'}

        registered = False
        maxBackoff = consts.BACKOFF_MAX # these should be set somewhere probably
        currentBackoff = consts.BACKOFF_START
        while not registered:
            try:
                requests.post('http://{0}:{1}/{2}'.format(config["EVENTGEN_CONTROLLER"], 9500, 'register'), data=data, headers=headers)
                registered = True
            except:
                self.logger.info('could not reach controller... retrying in {} seconds'.format(currentBackoff))
                time.sleep(currentBackoff)
                currentBackoff *= 2
                currentBackoff = min(maxBackoff, currentBackoff)
