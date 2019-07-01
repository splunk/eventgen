from api_blueprint import ApiBlueprint
import flask

class EventgenServerAPI(ApiBlueprint):
    def __init__(self):
        ApiBlueprint.__init__(self)
        self.bp = self._create_blueprint()
        self.message = 'hello'

    def _create_blueprint(self):
        bp = flask.Blueprint('server_api', __name__)

        @bp.route('/status', methods=['GET'])
        def status():
            return 'status is goodz'
        
        return bp
