from flask import Flask
from eventgen_server_api import EventgenServerAPI


class EventgenServer():

    def __init__(self, *args, **kwargs):        
        self.app = self._create_app()
        self.mode = kwargs.get('mode', 'standalone')

    def app_run(self):
        self.app.run(host="0.0.0.0", port=9500, threaded=True)
    
    def _create_app(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'does-not-exist'

        app.register_blueprint(EventgenServerAPI().get_blueprint())

        @app.route('/')
        def index():
            return "helloworld"
            
        return app
