import logging
import os
import socket
import threading
import time

import requests
from flask import Flask

from splunk_eventgen.eventgen_api_server.eventgen_controller_api import (
    EventgenControllerAPI,
)
from splunk_eventgen.eventgen_api_server.redis_connector import RedisConnector

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
LOG_PATH = os.path.join(FILE_PATH, "..", "logs")


class EventgenController:
    def __init__(self, *args, **kwargs):
        self.env_vars = kwargs.get("env_vars")

        self.role = "controller"
        self.host = socket.gethostname() + self.role

        self.redis_connector = RedisConnector(
            host=self.env_vars.get("REDIS_HOST"), port=self.env_vars.get("REDIS_PORT")
        )
        self.redis_connector.register_myself(hostname=self.host, role=self.role)

        self._setup_loggers()
        self.connections_healthcheck()
        self.logger = logging.getLogger("eventgen_controller")
        self.logger.info(
            "Initialized Eventgen Controller: hostname [{}]".format(self.host)
        )

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
        app.register_blueprint(
            EventgenControllerAPI(
                redis_connector=self.redis_connector, host=self.host
            ).get_blueprint()
        )

        @app.route("/")
        def index():
            return "running_eventgen_controller"

        return app

    def connections_healthcheck(self):
        def start_checking():
            while True:
                time.sleep(60 * 30)
                try:
                    requests.get(
                        "http://{}:{}/healthcheck".format(
                            "0.0.0.0", int(self.env_vars.get("WEB_SERVER_PORT"))
                        )
                    )
                except Exception as e:
                    self.logger.error(str(e))

        thread = threading.Thread(target=start_checking)
        thread.daemon = True
        thread.start()

    def _setup_loggers(self):
        eventgen_controller_logger_path = os.path.join(
            LOG_PATH, "eventgen-controller.log"
        )
        eventgen_error_logger_path = os.path.join(LOG_PATH, "eventgen-error.log")

        log_format = (
            "%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s"
        )
        date_format = "%Y-%m-%d %H:%M:%S"
        detailed_formatter = logging.Formatter(log_format, datefmt=date_format)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(detailed_formatter)
        console_handler.setLevel(logging.DEBUG)

        eventgen_controller_file_handler = logging.handlers.RotatingFileHandler(
            eventgen_controller_logger_path, maxBytes=2500000, backupCount=20
        )
        eventgen_controller_file_handler.setFormatter(detailed_formatter)
        eventgen_controller_file_handler.setLevel(logging.DEBUG)

        error_file_handler = logging.handlers.RotatingFileHandler(
            eventgen_error_logger_path, maxBytes=2500000, backupCount=20
        )
        error_file_handler.setFormatter(detailed_formatter)
        error_file_handler.setLevel(logging.ERROR)

        logger = logging.getLogger("eventgen_controller")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.handlers = []
        logger.addHandler(eventgen_controller_file_handler)
        logger.addHandler(console_handler)
        logger.addHandler(error_file_handler)
