import logging
import socket

from flask import Flask

from splunk_eventgen.eventgen_api_server import eventgen_core_object
from splunk_eventgen.eventgen_api_server.eventgen_server_api import EventgenServerAPI


class EventgenServer:
    def __init__(self, *args, **kwargs):
        self.env_vars = kwargs.get("env_vars")
        self.eventgen = eventgen_core_object.EventgenCoreObject(
            mutithread=self.env_vars.get("multithread", False)
        )
        self.mode = kwargs.get("mode", "standalone")
        self.host = socket.gethostname()
        self.role = "server"

        self.logger = logging.getLogger("eventgen_server")
        self.logger.info("Initialized Eventgen Server: hostname [{}]".format(self.host))

        if self.mode != "standalone":
            from splunk_eventgen.eventgen_api_server.redis_connector import (
                RedisConnector,
            )

            self.redis_connector = RedisConnector(
                host=self.env_vars.get("REDIS_HOST"),
                port=self.env_vars.get("REDIS_PORT"),
            )
            self.redis_connector.register_myself(hostname=self.host, role=self.role)
        self.app = self._create_app()

    def app_run(self):
        self.app.run(
            host="0.0.0.0",
            port=int(self.env_vars.get("WEB_SERVER_PORT")),
            threaded=True,
        )

    def _create_app(self):
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "does-not-exist"
        if self.mode == "standalone":
            app.register_blueprint(
                EventgenServerAPI(
                    eventgen=self.eventgen, redis_connector=None, host=self.host
                ).get_blueprint()
            )
        else:
            app.register_blueprint(
                EventgenServerAPI(
                    eventgen=self.eventgen,
                    redis_connector=self.redis_connector,
                    host=self.host,
                    mode=self.mode,
                ).get_blueprint()
            )

        @app.route("/")
        def index():
            return "running_eventgen_server"

        return app
