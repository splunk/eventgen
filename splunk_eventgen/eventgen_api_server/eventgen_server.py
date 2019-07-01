from flask import Flask

class EventgenServer():

    def __init__(self, *args, **kwargs):
        self.app = self._create_app()

    def app_run(self):
        self.app.run(host="0.0.0.0", port=9500)
    
    def _create_app(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'does-not-exist'
        
        # register api endpoints
        # app.register_blueprint(CreateWorkflowApi(self.logger).get_blueprint())
        # app.register_blueprint(OtherApi(self.logger).get_blueprint())
        @app.route('/')
        def index():
            return "helloworld"
            
        return app
