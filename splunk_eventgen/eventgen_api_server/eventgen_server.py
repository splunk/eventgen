from flask import Flask
import eventgen_core_object

class EventgenServer():

    def __init__(self, *args, **kwargs):
        self.app = self._create_app()
        self.eventgen = eventgen_core_object.EventgenCoreObject() 

    def app_run(self):
        self.app.run(host="0.0.0.0", port=9500)
    
    def _create_app(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'does-not-exist'

        # app.register_blueprint(CreateWorkflowApi(self.logger).get_blueprint())
        # app.register_blueprint(OtherApi(self.logger).get_blueprint())

        @app.route('/')
        def index():
            return "helloworld"
            
        return app
