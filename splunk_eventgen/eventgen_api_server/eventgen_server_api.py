import collections
import configparser
import glob
import json
import logging
import os
import shutil
import socket
import tarfile
import threading
import time
import zipfile

import flask
import requests
from flask import Response, request

from splunk_eventgen.eventgen_api_server import eventgen_core_object

INTERNAL_ERROR_RESPONSE = json.dumps({"message": "Internal Error Occurred"})

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_PATH = os.path.realpath(os.path.join(FILE_PATH, "..", "default"))
SAMPLE_DIR_PATH = os.path.realpath(os.path.join(FILE_PATH, "..", "serverSamples"))


class EventgenServerAPI:
    def __init__(self, eventgen, redis_connector, host, mode="standalone"):
        self.bp = self._create_blueprint()
        self.eventgen = eventgen
        self.logger = logging.getLogger("eventgen_server")
        self.logger.info("Initialized the EventgenServerAPI Blueprint")

        self.total_volume = 0.0
        self.host = host

        self.interval = 0.01
        self.mode = mode
        if self.mode != "standalone":
            self.redis_connector = redis_connector
            self._channel_listener()
            self.logger.info("Initialized the channel listener. Cluster mode ready.")

    def get_blueprint(self):
        return self.bp

    def _channel_listener(self):
        def start_listening(self):
            while True:
                message = self.redis_connector.pubsub.get_message()
                if message and type(message.get("data")) == bytes:
                    data = json.loads(message.get("data"))
                    self.logger.info("Message Recieved {}".format(message["data"]))
                    if data["target"] == "all" or data["target"] == self.host:
                        thread = threading.Thread(
                            target=self._delegate_jobs,
                            args=(
                                data.get("job"),
                                data.get("request_method"),
                                data.get("body"),
                                data.get("message_uuid"),
                            ),
                        )
                        thread.daemon = True
                        thread.start()
                time.sleep(self.interval)

        thread = threading.Thread(target=start_listening, args=(self,))
        thread.daemon = True
        thread.start()

    def format_message(self, job, request_method, response, message_uuid):
        return json.dumps(
            {
                "job": job,
                "request_method": request_method,
                "response": response,
                "host": self.host,
                "message_uuid": message_uuid,
            }
        )

    def _delegate_jobs(self, job, request_method, body, message_uuid):
        if not job:
            return
        else:
            self.logger.info(
                "Delegated {} {} {} {}".format(job, request_method, body, message_uuid)
            )
            if job == "status":
                response = self.get_status()
                message = self.format_message(
                    "status",
                    request_method,
                    response=response,
                    message_uuid=message_uuid,
                )
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel, message
                )
            elif job == "conf":
                if request_method == "POST":
                    self.set_conf(body)
                elif request_method == "PUT":
                    self.edit_conf(body)
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "conf",
                        request_method,
                        response=self.get_conf(),
                        message_uuid=message_uuid,
                    ),
                )
            elif job == "bundle":
                self.set_bundle(body.get("url", ""))
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "bundle",
                        request_method,
                        response=self.get_conf(),
                        message_uuid=message_uuid,
                    ),
                )
            elif job == "setup":
                self.clean_bundle_conf()
                self.setup_http(body)
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "setup",
                        request_method,
                        response=self.get_conf(),
                        message_uuid=message_uuid,
                    ),
                )
            elif job == "volume":
                if request_method == "POST":
                    self.set_volume(body.get("perDayVolume", 0.0))
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "volume",
                        request_method,
                        response=self.get_volume(),
                        message_uuid=message_uuid,
                    ),
                )
            elif job == "start":
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "start",
                        request_method,
                        response=self.start(),
                        message_uuid=message_uuid,
                    ),
                )
            elif job == "stop":
                message = {
                    "message": "Eventgen is stopping. Might take some time to terminate all processes."
                }
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "stop",
                        request_method,
                        response=message,
                        message_uuid=message_uuid,
                    ),
                )
                self.stop(force_stop=True)
            elif job == "restart":
                message = {
                    "message": "Eventgen is restarting. Might take some time to restart."
                }
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "restart",
                        request_method,
                        response=message,
                        message_uuid=message_uuid,
                    ),
                )
                self.restart()
            elif job == "reset":
                message = {
                    "message": "Eventgen is resetting. Might take some time to reset."
                }
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel,
                    self.format_message(
                        "reset",
                        request_method,
                        response=message,
                        message_uuid=message_uuid,
                    ),
                )
                self.reset()
            elif job == "healthcheck":
                response = self.healthcheck()
                message = self.format_message(
                    "healthcheck",
                    request_method,
                    response=response,
                    message_uuid=message_uuid,
                )
                self.redis_connector.message_connection.publish(
                    self.redis_connector.controller_channel, message
                )

    def _create_blueprint(self):
        bp = flask.Blueprint("server_api", __name__)

        @bp.route("/index", methods=["GET"])
        def http_get_index():
            return self.get_index()

        @bp.route("/status", methods=["GET"])
        def http_get_status():
            try:
                response = self.get_status()
                return Response(
                    json.dumps(response), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/conf", methods=["GET", "POST", "PUT"])
        def http_conf():
            try:
                if request.method == "POST":
                    self.set_conf(request.get_json(force=True))
                elif request.method == "PUT":
                    self.edit_conf(request.get_json(force=True))
                return Response(
                    json.dumps(self.get_conf()), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/volume", methods=["GET"])
        def http_get_volume():
            try:
                response = self.get_volume()
                return Response(
                    json.dumps(response), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/volume", methods=["POST"])
        def http_post_volume():
            try:
                self.set_volume(request.get_json(force=True).get("perDayVolume", 0.0))
                return Response(
                    json.dumps(self.get_volume()),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/start", methods=["POST"])
        def http_post_start():
            try:
                response = self.start()
                return Response(
                    json.dumps(response), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/stop", methods=["POST"])
        def http_post_stop():
            try:
                response = self.stop(force_stop=True)
                self.eventgen.refresh_eventgen_core_object()
                return Response(
                    json.dumps(response), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/restart", methods=["POST"])
        def http_post_restart():
            try:
                response = self.restart()
                return Response(
                    json.dumps(response), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/reset", methods=["POST"])
        def http_post_reset():
            try:
                response = self.reset()
                return Response(
                    json.dumps(response), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/bundle", methods=["POST"])
        def http_post_bundle():
            try:
                self.set_bundle(request.get_json(force=True).get("url", ""))
                self.clean_bundle_conf()
                return Response(
                    json.dumps(self.get_conf()), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/setup", methods=["POST"])
        def http_post_setup():
            try:
                self.stop(force_stop=True)
                self.clean_bundle_conf()
                self.setup_http(request.get_json(force=True))
                return Response(
                    json.dumps(self.get_conf()), mimetype="application/json", status=200
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        @bp.route("/healthcheck", methods=["GET"])
        def http_get_healthcheck():
            try:
                return Response(
                    json.dumps(self.healthcheck()),
                    mimetype="application/json",
                    status=200,
                )
            except Exception as e:
                self.logger.error(e)
                return Response(
                    INTERNAL_ERROR_RESPONSE, mimetype="application/json", status=500
                )

        return bp

    def get_index(self):
        home_page = """*** Eventgen WSGI ***
Host: {0}
Eventgen Status: {1}
Eventgen Config file exists: {2}
Eventgen Config file path: {3}
Total volume: {4}
Worker Queue Status: {5}
Sample Queue Status: {6}
Output Queue Status: {7}
"""
        status = self.get_status()
        eventgen_status = "running" if status["EVENTGEN_STATUS"] else "stopped"
        host = status["EVENTGEN_HOST"]
        configured = status["CONFIGURED"]
        config_file = status["CONFIG_FILE"]
        total_volume = status["TOTAL_VOLUME"]
        worker_queue_status = status["QUEUE_STATUS"]["WORKER_QUEUE"]
        sample_queue_status = status["QUEUE_STATUS"]["SAMPLE_QUEUE"]
        output_queue_status = status["QUEUE_STATUS"]["OUTPUT_QUEUE"]
        return home_page.format(
            host,
            eventgen_status,
            configured,
            config_file,
            total_volume,
            worker_queue_status,
            sample_queue_status,
            output_queue_status,
        )

    def get_conf(self):
        response = collections.OrderedDict()
        if self.eventgen.configured:
            config = configparser.RawConfigParser()
            config.optionxform = str
            config_path = self.eventgen.configfile
            if os.path.isfile(config_path):
                config.read(config_path)
                for section in config.sections():
                    response[section] = collections.OrderedDict()
                    for k, v in config.items(section):
                        response[section][k] = v
        return response

    def set_conf(self, request_body):
        config = configparser.RawConfigParser({}, collections.OrderedDict)
        config.optionxform = str

        for sample in request_body.items():
            config.add_section(sample[0])
            for pair in sample[1].items():
                value = pair[1]
                if type(value) == dict:
                    value = json.dumps(value)
                config.set(sample[0], pair[0], str(value))

        with open(eventgen_core_object.CUSTOM_CONFIG_PATH, "w+") as conf_content:
            config.write(conf_content)

        self.eventgen.refresh_eventgen_core_object()

    def edit_conf(self, request_body):
        conf_dict = self.get_conf()

        for stanza, kv_pairs in request_body.items():
            for key, value in kv_pairs.items():
                if stanza not in conf_dict:
                    conf_dict[stanza] = {}
                if stanza == "global" and key == "index":
                    for stanza, kv_pairs in conf_dict.items():
                        conf_dict[stanza]["index"] = value
                conf_dict[stanza][key] = value

        self.set_conf(conf_dict)

    def get_status(self):
        response = dict()
        if self.eventgen.eventgen_core_object.check_running():
            status = (
                1 if not self.eventgen.eventgen_core_object.check_done() else 2
            )  # 1 is running and 2 is done
        else:
            status = 0  # not start yet
        response["EVENTGEN_STATUS"] = status
        response["EVENTGEN_HOST"] = self.host
        response["CONFIGURED"] = self.eventgen.configured
        response["CONFIG_FILE"] = self.eventgen.configfile
        response["TOTAL_VOLUME"] = self.total_volume
        response["QUEUE_STATUS"] = {
            "SAMPLE_QUEUE": {"UNFINISHED_TASK": "N/A", "QUEUE_LENGTH": "N/A"},
            "OUTPUT_QUEUE": {"UNFINISHED_TASK": "N/A", "QUEUE_LENGTH": "N/A"},
            "WORKER_QUEUE": {"UNFINISHED_TASK": "N/A", "QUEUE_LENGTH": "N/A"},
        }
        response["THROUGHPUT_STATUS"] = self.get_throughput()
        if hasattr(self.eventgen.eventgen_core_object, "sampleQueue"):
            response["QUEUE_STATUS"]["SAMPLE_QUEUE"][
                "UNFINISHED_TASK"
            ] = self.eventgen.eventgen_core_object.sampleQueue.unfinished_tasks
            response["QUEUE_STATUS"]["SAMPLE_QUEUE"][
                "QUEUE_LENGTH"
            ] = self.eventgen.eventgen_core_object.sampleQueue.qsize()
        if hasattr(self.eventgen.eventgen_core_object, "outputQueue"):
            try:
                response["QUEUE_STATUS"]["OUTPUT_QUEUE"][
                    "UNFINISHED_TASK"
                ] = self.eventgen.eventgen_core_object.outputQueue.unfinished_tasks
            except:
                response["QUEUE_STATUS"]["OUTPUT_QUEUE"]["UNFINISHED_TASK"] = "N/A"
            try:
                response["QUEUE_STATUS"]["OUTPUT_QUEUE"][
                    "QUEUE_LENGTH"
                ] = self.eventgen.eventgen_core_object.outputQueue.qsize()
            except:
                response["QUEUE_STATUS"]["OUTPUT_QUEUE"]["QUEUE_LENGTH"] = "N/A"
        if hasattr(self.eventgen.eventgen_core_object, "workerQueue"):
            try:
                response["QUEUE_STATUS"]["WORKER_QUEUE"][
                    "UNFINISHED_TASK"
                ] = self.eventgen.eventgen_core_object.workerQueue.unfinished_tasks
            except:
                response["QUEUE_STATUS"]["WORKER_QUEUE"]["UNFINISHED_TASK"] = "N/A"
            try:
                response["QUEUE_STATUS"]["WORKER_QUEUE"][
                    "QUEUE_LENGTH"
                ] = self.eventgen.eventgen_core_object.workerQueue.qsize()
            except:
                response["QUEUE_STATUS"]["WORKER_QUEUE"]["QUEUE_LENGTH"] = "N/A"
        return response

    def get_throughput(self):
        empty_throughput = {
            "TOTAL_VOLUME_MB": 0,
            "TOTAL_COUNT": 0,
            "THROUGHPUT_VOLUME_KB": 0,
            "THROUGHPUT_COUNT": 0,
        }
        if hasattr(self.eventgen.eventgen_core_object, "output_counters"):
            total_volume = 0
            total_count = 0
            throughput_volume = 0
            throughput_count = 0
            for output_counter in self.eventgen.eventgen_core_object.output_counters:
                total_volume += output_counter.total_output_volume
                total_count += output_counter.total_output_count
                throughput_volume += output_counter.throughput_volume
                throughput_count += output_counter.throughput_count
            return {
                "TOTAL_VOLUME_MB": total_volume / (1024 * 1024),
                "TOTAL_COUNT": total_count,
                "THROUGHPUT_VOLUME_KB": throughput_volume / (1024),
                "THROUGHPUT_COUNT": throughput_count,
            }
        else:
            return empty_throughput

    def get_volume(self):
        response = dict()
        config = self.get_conf()
        total_volume = 0.0
        volume_distribution = {}
        for stanza in list(config.keys()):
            if isinstance(config[stanza], dict) and "perDayVolume" in list(
                config[stanza].keys()
            ):
                total_volume += float(config[stanza]["perDayVolume"])
                volume_distribution[stanza] = float(config[stanza]["perDayVolume"])

        if total_volume:
            self.total_volume = total_volume
        response["perDayVolume"] = self.total_volume
        response["volume_distribution"] = volume_distribution
        return response

    def set_volume(self, target_volume):
        conf_dict = self.get_conf()
        if self.get_volume()["perDayVolume"] != 0:
            ratio = float(target_volume) / float(self.total_volume)
            for stanza, kv_pair in conf_dict.items():
                if isinstance(kv_pair, dict):
                    if ".*" not in stanza and "perDayVolume" in list(kv_pair.keys()):
                        conf_dict[stanza]["perDayVolume"] = round(
                            float(conf_dict[stanza]["perDayVolume"]) * ratio, 2
                        )
        else:
            # If there is no total_volume existing, divide the volume equally into stanzas
            stanza_num = len(list(conf_dict.keys()))
            if ".*" in conf_dict:
                stanza_num -= 1
            if "global" in conf_dict:
                stanza_num -= 1
            divided_volume = float(target_volume) / stanza_num
            for stanza, kv_pair in conf_dict.items():
                if (
                    isinstance(kv_pair, dict)
                    and stanza != "global"
                    and ".*" not in stanza
                ):
                    conf_dict[stanza]["perDayVolume"] = divided_volume

        self.set_conf(conf_dict)
        self.total_volume = round(float(target_volume), 2)

    def start(self):
        response = {}
        if not self.eventgen.configured:
            response["message"] = "Eventgen is not configured."
        elif self.eventgen.eventgen_core_object.check_running():
            response["message"] = "Eventgen already started."
        else:
            self.eventgen.eventgen_core_object.start(join_after_start=False)
            response["message"] = "Eventgen has successfully started."
        return response

    def stop(self, force_stop=False):
        response = {}
        if self.eventgen.eventgen_core_object.check_running():
            try:
                self.eventgen.eventgen_core_object.stop(force_stop=force_stop)
            except:
                pass
            response["message"] = "Eventgen is stopped."
        else:
            response["message"] = "There is no Eventgen process running."
        return response

    def restart(self):
        response = {}
        if self.eventgen.eventgen_core_object.check_running():
            self.reset()
            self.start()
            response["message"] = "Eventgen has successfully restarted."
        else:
            self.start()
            response["message"] = "Eventgen was not running. Starting Eventgen."
        return response

    def reset(self):
        response = {}
        self.stop(force_stop=True)
        time.sleep(0.1)
        self.eventgen.refresh_eventgen_core_object()
        self.get_volume()
        response["message"] = "Eventgen has been reset."
        return response

    def healthcheck(self):
        response = {}
        if self.mode != "standalone":
            try:
                self.redis_connector.pubsub.check_health()
                response["message"] = "Connections are healthy"
            except Exception as e:
                self.logger.error(
                    "Connection to Redis failed: {}, re-registering".format(str(e))
                )
                self.redis_connector.register_myself(hostname=self.host, role="server")
                response[
                    "message"
                ] = "Connections unhealthy - re-established connections"
        else:
            response["message"] = "Standalone {} is healthy".format(self.host)
        return response

    def set_bundle(self, url):
        if not url:
            return

        bundle_dir = self.unarchive_bundle(self.download_bundle(url))

        if os.path.isdir(os.path.join(bundle_dir, "samples")):
            if not os.path.exists(SAMPLE_DIR_PATH):
                os.makedirs(SAMPLE_DIR_PATH)
            for file in glob.glob(os.path.join(bundle_dir, "samples", "*")):
                shutil.copy(file, SAMPLE_DIR_PATH)
            self.logger.info("Copied all samples to the sample directory.")

        if os.path.isfile(os.path.join(bundle_dir, "default", "eventgen.conf")):
            self.eventgen.configured = False
            config = configparser.RawConfigParser()
            config.optionxform = str
            config.read(os.path.join(bundle_dir, "default", "eventgen.conf"))
            config_dict = {
                s: collections.OrderedDict(config.items(s)) for s in config.sections()
            }
            self.set_conf(config_dict)
            self.eventgen.configured = True
            self.logger.info("Configured Eventgen with the downloaded bundle.")

    def download_bundle(self, url):
        bundle_path = os.path.join(DEFAULT_PATH, "eg-bundle.tgz")
        try:
            os.remove(bundle_path)
            shutil.rmtree(os.path.join(os.path.dirname(bundle_path), "eg-bundle"))
        except:
            pass
        r = requests.get(url, stream=True)
        with open(bundle_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    f.write(chunk)
        r.close()
        self.logger.info("Downloaded bundle to the path {}".format(bundle_path))
        return bundle_path

    def unarchive_bundle(self, path):
        output = ""
        if tarfile.is_tarfile(path):
            tar = tarfile.open(path)
            foldername = ""
            for name in tar.getnames():
                if "/" not in name:
                    foldername = name
                    break
            output = os.path.join(
                os.path.dirname(path), os.path.commonprefix(tar.getnames())
            )
            tar.extractall(path=os.path.dirname(path))
            tar.close()
            if foldername:
                os.rename(
                    os.path.join(os.path.dirname(path), foldername),
                    os.path.join(os.path.dirname(path), "eg-bundle"),
                )
                output = os.path.join(os.path.dirname(path), "eg-bundle")
        elif zipfile.is_zipfile(path):
            zipf = zipfile.ZipFile(path)
            for info in zipf.infolist():
                info.filename = "eg-bundle/" + info.filename
                zipf.extract(info, os.path.dirname(path))
            output = os.path.join(os.path.dirname(path), "eg-bundle")
            zipf.close()
        else:
            msg = "Unknown archive format!"
            raise Exception(msg)
        self.logger.info("Unarchived bundle to the path {}".format(path))
        return output

    def clean_bundle_conf(self):
        conf_dict = self.get_conf()

        if ".*" not in conf_dict:
            conf_dict[".*"] = {}

        # 1. Remove sampleDir from individual stanza and set a global sampleDir
        # 2. Change token sample path to a local sample path
        for stanza, kv_pair in conf_dict.items():
            if stanza != ".*":
                if "sampleDir" in kv_pair:
                    del kv_pair["sampleDir"]

            for key, value in kv_pair.items():
                if "replacementType" in key and value in ["file", "mvfile", "seqfile"]:
                    token_num = key[key.find(".") + 1 : key.rfind(".")]
                    if not token_num:
                        continue
                    else:
                        existing_path = kv_pair[
                            "token.{}.replacement".format(token_num)
                        ]
                        kv_pair[
                            "token.{}.replacement".format(token_num)
                        ] = os.path.join(
                            SAMPLE_DIR_PATH,
                            existing_path[existing_path.rfind("/") + 1 :],
                        )

        conf_dict[".*"]["sampleDir"] = SAMPLE_DIR_PATH
        self.set_conf(conf_dict)

    def setup_http(self, data):
        if data.get("servers"):
            conf_dict = self.get_conf()
            if "global" not in conf_dict:
                conf_dict["global"] = {}
            for stanza, kv_pair in conf_dict.items():
                if "outputMode" in kv_pair:
                    del kv_pair["outputMode"]
                if "httpeventServers" in kv_pair:
                    del kv_pair["httpeventServers"]
            conf_dict["global"]["threading"] = "process"
            conf_dict["global"]["httpeventMaxPayloadSize"] = "256000"
            conf_dict["global"]["outputMode"] = (
                data.get("outputMode") if data.get("outputMode") else "httpevent"
            )
            conf_dict["global"]["httpeventServers"] = {"servers": data.get("servers")}
            self.set_conf(conf_dict)
        else:
            # If hec_servers information doesn't exist, do service discovery
            hostname_template = data.get("hostname_template", "idx{0}")
            hosts = data.get("other_hosts", [])
            protocol = data.get("protocol", "https")
            key = data.get("key", "00000000-0000-0000-0000-000000000000")
            key_name = data.get("key_name", "eventgen") + "_" + self.host
            password = data.get("password", "Chang3d!")
            hec_port = int(data.get("hec_port", 8088))
            mgmt_port = int(data.get("mgmt_port", 8089))
            new_key = bool(data.get("new_key", True))

            def create_new_hec_key(hostname):
                requests.post(
                    "https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http/http".format(
                        hostname, mgmt_port
                    ),
                    auth=("admin", password),
                    data={"disabled": "0"},
                    verify=False,
                )
                requests.delete(
                    "https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http/{2}".format(
                        hostname, mgmt_port, key_name
                    ),
                    verify=False,
                    auth=("admin", password),
                )
                requests.post(
                    "https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http?output_mode=json".format(
                        hostname, mgmt_port
                    ),
                    verify=False,
                    auth=("admin", password),
                    data={"name": key_name},
                )
                r = requests.post(
                    "https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http/{2}?output_mode=json".format(
                        hostname, mgmt_port, key_name
                    ),
                    verify=False,
                    auth=("admin", password),
                )
                return str(json.loads(r.text)["entry"][0]["content"]["token"])

            self.discovered_servers = []
            for host in hosts:
                try:
                    if new_key:
                        key = create_new_hec_key(host)
                except (socket.gaierror, requests.ConnectionError):
                    self.logger.warning("failed to reach %s, skip..." % host)
                    continue
                except (ValueError, KeyError):
                    self.logger.warning(
                        "failed to setup hec token for %s, skip..." % host
                    )
                    continue

                self.discovered_servers.append(
                    {
                        "protocol": str(protocol),
                        "address": str(host),
                        "port": str(hec_port),
                        "key": str(key),
                    }
                )

            counter = 1
            while True:
                try:
                    formatted_hostname = socket.gethostbyname(
                        hostname_template.format(counter)
                    )
                    if new_key:
                        key = create_new_hec_key(formatted_hostname)

                    self.discovered_servers.append(
                        {
                            "protocol": str(protocol),
                            "address": str(formatted_hostname),
                            "port": str(hec_port),
                            "key": str(key),
                        }
                    )
                    counter += 1
                except socket.gaierror:
                    break

            conf_dict = self.get_conf()
            if "global" not in conf_dict:
                conf_dict["global"] = {}
            for stanza, kv_pair in conf_dict.items():
                if "outputMode" in kv_pair:
                    del kv_pair["outputMode"]
                if "httpeventServers" in kv_pair:
                    del kv_pair["httpeventServers"]
            conf_dict["global"]["threading"] = "process"
            conf_dict["global"]["httpeventMaxPayloadSize"] = "256000"
            conf_dict["global"]["outputMode"] = (
                data.get("outputMode") if data.get("outputMode") else "httpevent"
            )
            conf_dict["global"]["httpeventServers"] = {
                "servers": self.discovered_servers
            }
            self.set_conf(conf_dict)
