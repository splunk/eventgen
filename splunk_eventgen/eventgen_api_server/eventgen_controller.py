from flask import Flask, request

from eventgen_controller_api import EventgenControllerAPI

class EventgenController():

    def __init__(self, *args, **kwargs):
        self.app = self._create_app()

    def app_run(self):
        self.app.run(host="0.0.0.0", port=9500, threaded=True)
    
    def _create_app(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'does-not-exist'
        
        # register api endpoints
        app.register_blueprint(EventgenControllerAPI().get_blueprint())

        @app.route('/')
        def index():
            return "hellocontrollerworld"
            
        return app
