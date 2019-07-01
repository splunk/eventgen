from flask import Flask

registered_routes = {}
def register_route(route):
    def inner(fn):
        registered_routes[route] = fn
        return fn
    return inner

class EventgenServer(Object):

    def __init__(self, *args, **kwargs):
        self.app = self._create_app()

    def _create_app(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'does-not-exist'
