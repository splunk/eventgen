import json
import logging
import time
import uuid

from flask import Blueprint, Response, request

INTERNAL_ERROR_RESPONSE = json.dumps({"message": "Internal Error Occurred"})


class EventgenControllerAPI:
    def __init__(self, redis_connector, host):
        self.bp = self.__create_blueprint()
        self.redis_connector = redis_connector
        self.host = host
        self.logger = logging.getLogger("eventgen_controller")
        self.logger.info("Initialized the EventgenControllerAPI Blueprint")
        self.interval = 0.001

        self.server_responses = {}

    def get_blueprint(self):
        return self.bp

    def __create_blueprint(self):
        bp = Blueprint("api", __name__)

        def publish_message(job, request_method, body=None, target="all"):
            message_uuid = str(uuid.uuid4())
            formatted_message = json.dumps(
                {
                    "job": job,
                    "target": target,
                    "body": body,
                    "request_method": request_method,
                    "message_uuid": message_uuid,
                }
            )
            self.redis_connector.message_connection.publish(
                self.redis_connector.servers_channel, formatted_message
            )
            self.logger.info("Published {}".format(formatted_message))
            return message_uuid

        def gather_response(target_job, message_uuid, response_number_target=0):
            if not response_number_target:
                response_number_target = int(
                    self.redis_connector.message_connection.pubsub_numsub(
                        self.redis_connector.servers_channel
                    )[0][1]
                )
            if target_job == "bundle":
                countdown = 120
            elif target_job == "status":
                countdown = 15
            else:
                countdown = 5
            for i in range(0, int(countdown / self.interval)):
                response_num = len(
                    list(self.server_responses.get(message_uuid, {}).keys())
                )
                if response_num == response_number_target:
                    break
                else:
                    time.sleep(self.interval)
                    message = self.redis_connector.pubsub.get_message()
                    if message and type(message.get("data")) == bytes:
                        server_response = json.loads(message.get("data"))
                        self.logger.info(server_response)
                        response_message_uuid = server_response.get("message_uuid")
                        if response_message_uuid:
                            if response_message_uuid not in self.server_responses:
                                self.server_responses[response_message_uuid] = {}
                            self.server_responses[response_message_uuid][
                                server_response["host"]
                            ] = server_response["response"]
            return self.server_responses.get(message_uuid, {})

        @bp.route("/index", methods=["GET"])
        def index():
            home_page = """*** Eventgen Controller ***
Host: {0}
Connected Servers: {1}
You are running Eventgen Controller.\n"""
            host = self.host
            return home_page.format(host, self.redis_connector.get_registered_servers())

        @bp.route("/status", methods=["GET"], defaults={"target": "all"})
        @bp.route("/status/<string:target>", methods=["GET"])
        def http_status(target):
            try:
                message_uuid = publish_message("status", request.method, target=target)
                return Response(
                    json.dumps(
                        gather_response(
                            "status",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/conf", methods=["GET", "POST", "PUT"], defaults={"target": "all"})
        @bp.route("/conf/<string:target>", methods=["GET", "POST", "PUT"])
        def http_conf(target):
            try:
                body = None if request.method == "GET" else request.get_json(force=True)
                message_uuid = publish_message(
                    "conf", request.method, body=body, target=target
                )
                return Response(
                    json.dumps(
                        gather_response(
                            "conf",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/bundle", methods=["POST"], defaults={"target": "all"})
        @bp.route("/bundle/<string:target>", methods=["POST"])
        def http_bundle(target):
            try:
                message_uuid = publish_message(
                    "bundle",
                    request.method,
                    body=request.get_json(force=True),
                    target=target,
                )
                return Response(
                    json.dumps(
                        gather_response(
                            "bundle",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/setup", methods=["POST"], defaults={"target": "all"})
        @bp.route("/setup/<string:target>", methods=["POST"])
        def http_setup(target):
            try:
                message_uuid = publish_message(
                    "setup",
                    request.method,
                    body=request.get_json(force=True),
                    target=target,
                )
                return Response(
                    json.dumps(
                        gather_response(
                            "setup",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/volume", methods=["GET", "POST"], defaults={"target": "all"})
        @bp.route("/volume/<string:target>", methods=["GET", "POST"])
        def http_volume(target):
            try:
                body = None if request.method == "GET" else request.get_json(force=True)
                message_uuid = publish_message(
                    "volume", request.method, body=body, target=target
                )
                return Response(
                    json.dumps(
                        gather_response(
                            "volume",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/start", methods=["POST"], defaults={"target": "all"})
        @bp.route("/start/<string:target>", methods=["POST"])
        def http_start(target):
            try:
                message_uuid = publish_message("start", request.method, target=target)
                return Response(
                    json.dumps(
                        gather_response(
                            "start",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/stop", methods=["POST"], defaults={"target": "all"})
        @bp.route("/stop/<string:target>", methods=["POST"])
        def http_stop(target):
            try:
                message_uuid = publish_message("stop", request.method, target=target)
                return Response(
                    json.dumps(
                        gather_response(
                            "stop",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/restart", methods=["POST"], defaults={"target": "all"})
        @bp.route("/restart/<string:target>", methods=["POST"])
        def http_restart(target):
            try:
                message_uuid = publish_message("restart", request.method, target=target)
                return Response(
                    json.dumps(
                        gather_response(
                            "restart",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/reset", methods=["POST"], defaults={"target": "all"})
        @bp.route("/reset/<string:target>", methods=["POST"])
        def http_reset(target):
            try:
                message_uuid = publish_message("reset", request.method, target=target)
                return Response(
                    json.dumps(
                        gather_response(
                            "reset",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/healthcheck", methods=["GET"], defaults={"target": "all"})
        @bp.route("/healthcheck/<string:target>", methods=["GET"])
        def http_healthcheck(target):
            try:
                self.redis_connector.pubsub.check_health()
            except Exception as e:
                self.logger.info(
                    "Connection to Redis failed: {}, re-registering".format(str(e))
                )
                try:
                    self.redis_connector.register_myself(
                        hostname=self.host, role="controller"
                    )
                except Exception as connection_error:
                    self.logger.error(connection_error)
                    return Response(
                        INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                    )
            try:
                message_uuid = publish_message(
                    "healthcheck", request.method, target=target
                )
                return Response(
                    json.dumps(
                        gather_response(
                            "healthcheck",
                            message_uuid=message_uuid,
                            response_number_target=0 if target == "all" else 1,
                        )
                    ),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        return bp

    def __make_error_response(self, status, message):
        return Response(json.dumps({"message": message}), status=status)
