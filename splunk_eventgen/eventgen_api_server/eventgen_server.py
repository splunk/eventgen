from flask import Flask
from eventgen_server_api import EventgenServerAPI
import os


class EventgenServer():

    def __init__(self, *args, **kwargs):        
        self.app = self._create_app()
        self.mode = kwargs.get('mode', 'standalone')

    def app_run(self):
        osvars, config = dict(os.environ), {}
        test = osvars.get("EVENTGEN_CONTROLLER", "localhost")
        port = 9500
        # if test == 'localhost':
        #     port = 9501
        self.app.run(host="0.0.0.0", port=port, threaded=True)
    
    def _create_app(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'does-not-exist'

        app.register_blueprint(EventgenServerAPI().get_blueprint())

        @app.route('/')
        def index():
            return "helloworld"
            
        return app
