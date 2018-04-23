from nameko.rpc import rpc
from nameko.web.handlers import http
from nameko.events import EventDispatcher, event_handler, BROADCAST
from pyrabbit.api import Client
import atexit
import ConfigParser
import yaml
import json
import os
import socket
import time
import requests
import glob
import tarfile
import zipfile
import shutil
import eventgen_nameko_dependency
import logging

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
EVENTGEN_DIR = os.path.realpath(os.path.join(FILE_PATH, ".."))
CUSTOM_CONFIG_PATH = os.path.realpath(os.path.join(FILE_PATH, "default", "eventgen_wsgi.conf"))
EVENTGEN_DEFAULT_CONF_PATH = os.path.abspath(os.path.join(FILE_PATH, "default", "eventgen.conf"))


def get_eventgen_name_from_conf():
    with open(os.path.abspath(os.path.join(FILE_PATH, "server_conf.yml"))) as config_yml:
        loaded_yml = yaml.load(config_yml)
        return loaded_yml['EVENTGEN_NAME'] if 'EVENTGEN_NAME' in loaded_yml else socket.gethostname()
    return None


def exit_handler(client, hostname, logger):
    client.delete_vhost(hostname)
    logger.info("Deleted vhost {}. Shutting down.".format(hostname))


class EventgenServer(object):
    name = "eventgen_server"

    dispatch = EventDispatcher()

    eventgen_dependency = eventgen_nameko_dependency.EventgenDependency()
    eventgen_name = get_eventgen_name_from_conf()
    host = socket.gethostname()
    log = logging.getLogger(name)
    log.info("Eventgen name is set to [{}] at host [{}]".format(eventgen_name, host))

    osvars, config = dict(os.environ), {}
    config["AMQP_HOST"] = osvars.get("EVENTGEN_AMQP_HOST", "localhost")
    config["AMQP_WEBPORT"] = osvars.get("EVENTGEN_AMQP_WEBPORT", 15672)
    config["AMQP_USER"] = osvars.get("EVENTGEN_AMQP_URI", "guest")
    config["AMQP_PASS"] = osvars.get("EVENTGEN_AMQP_PASS", "guest")

    pyrabbit_cl = Client('{0}:{1}'.format(config['AMQP_HOST'], config['AMQP_WEBPORT']),
                         '{0}'.format(config['AMQP_USER']),
                         '{0}'.format(config['AMQP_PASS']))
    pyrabbit_cl.create_vhost(host)
    log.info("Vhost set to {}".format(host))

    atexit.register(exit_handler, client=pyrabbit_cl, hostname=host, logger=log)
    total_volume = 0.0

    def get_status(self):
        '''
        Get status of eventgen

        return value structure
        {
            "EVENTGEN_STATUS" :
            "EVENTGEN_HOST" :
            "CONFIGURED" :
            "CONFIG_FILE" :
            "TOTAL_VOLUME" :
            "QUEUE_STATUS" : { "SAMPLE_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': },
                               "OUTPUT_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': },
                               "WORKER_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': }}
        }
        '''
        res = dict()
        if self.eventgen_dependency.eventgen.check_running():
            status = 1
        else:
            status = 0
        res["EVENTGEN_STATUS"] = status
        res["EVENTGEN_HOST"] = self.host
        res["CONFIGURED"] = self.eventgen_dependency.configured
        res["CONFIG_FILE"] = self.eventgen_dependency.configfile
        res["TOTAL_VOLUME"] = self.total_volume
        res["QUEUE_STATUS"] = {'SAMPLE_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'},
                               'OUTPUT_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'},
                               'WORKER_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'}}

        if hasattr(self.eventgen_dependency.eventgen, "sampleQueue"):
            res["QUEUE_STATUS"]['SAMPLE_QUEUE'][
                'UNFINISHED_TASK'] = self.eventgen_dependency.eventgen.sampleQueue.unfinished_tasks
            res["QUEUE_STATUS"]['SAMPLE_QUEUE']['QUEUE_LENGTH'] = self.eventgen_dependency.eventgen.sampleQueue.qsize()
        if hasattr(self.eventgen_dependency.eventgen, "outputQueue"):
            res["QUEUE_STATUS"]['OUTPUT_QUEUE'][
                'UNFINISHED_TASK'] = self.eventgen_dependency.eventgen.outputQueue.unfinished_tasks
            res["QUEUE_STATUS"]['OUTPUT_QUEUE']['QUEUE_LENGTH'] = self.eventgen_dependency.eventgen.outputQueue.qsize()
        if hasattr(self.eventgen_dependency.eventgen, "workerQueue"):
            res["QUEUE_STATUS"]['WORKER_QUEUE'][
                'UNFINISHED_TASK'] = self.eventgen_dependency.eventgen.workerQueue.unfinished_tasks
            res["QUEUE_STATUS"]['WORKER_QUEUE']['QUEUE_LENGTH'] = self.eventgen_dependency.eventgen.workerQueue.qsize()
        return res

    ##############################################
    ############### Real Methods #################
    ##############################################

    def index(self):
        self.log.info("index method called")
        home_page = '''*** Eventgen WSGI ***
Host: {0}
Eventgen Status: {1}
Eventgen Config file exists: {2}
Eventgen Config file path: {3}
Total volume: {4}
Worker Queue Status: {5}
Sample Queue Status: {6}
Output Queue Status: {7}\n'''
        status = self.get_status()
        eventgen_status = "running" if status["EVENTGEN_STATUS"] else "stopped"
        host = status["EVENTGEN_HOST"]
        configured = status["CONFIGURED"]
        config_file = status["CONFIG_FILE"]
        total_volume = status["TOTAL_VOLUME"]
        worker_queue_status = status["QUEUE_STATUS"]["WORKER_QUEUE"]
        sample_queue_status = status["QUEUE_STATUS"]["SAMPLE_QUEUE"]
        output_queue_status = status["QUEUE_STATUS"]["OUTPUT_QUEUE"]

        return home_page.format(host,
                                eventgen_status,
                                configured,
                                config_file,
                                total_volume,
                                worker_queue_status,
                                sample_queue_status,
                                output_queue_status)

    def status(self):
        self.log.info('Status method called.')
        status = self.get_status()
        self.log.info(status)
        self.send_status_to_controller(server_status=status)
        return json.dumps(status, indent=4)

    @rpc
    def send_status_to_controller(self, server_status):
        data = {}
        data['server_name'] = self.eventgen_name
        data['server_status'] = server_status
        self.dispatch("server_status", data)

    def start(self):
        self.log.info("start method called. Config is {}".format(self.eventgen_dependency.configfile))
        try:
            if not self.eventgen_dependency.configured:
                return "There is not config file known to eventgen. Pass in the config file to /conf before you start."
            if self.eventgen_dependency.eventgen.check_running():
                return "Eventgen already started."
            self.eventgen_dependency.eventgen.start(join_after_start=False)
            return "Eventgen has successfully started."
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def stop(self):
        self.log.info("stop method called")
        try:
            if self.eventgen_dependency.eventgen.check_running():
                self.eventgen_dependency.eventgen.stop()
                return "Eventgen is stopped."
            return "There is no eventgen process running."
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def restart(self):
        try:
            self.log.info("restart method called.")
            self.stop()
            time.sleep(2)
            self.start()
            return "Eventgen restarted."
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def get_conf(self):
        self.log.info("get_conf method called.")
        try:
            if self.eventgen_dependency.configured:
                config = ConfigParser.ConfigParser()
                config.optionxform = str
                config_path = CUSTOM_CONFIG_PATH

                if os.path.isfile(config_path):
                    config.read(config_path)
                    out_json = dict()
                    for section in config.sections():
                        out_json[section] = dict()
                        for k, v in config.items(section):
                            out_json[section][k] = v
                    # self.log.info(out_json)
                    self.send_conf_to_controller(server_conf=out_json)
                    return json.dumps(out_json, indent=4)
            else:
                self.send_conf_to_controller(server_conf={})
                return json.dumps({}, indent=4)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def send_conf_to_controller(self, server_conf):
        data = {}
        data['server_name'] = self.eventgen_name
        data['server_conf'] = server_conf
        self.dispatch("server_conf", data)

    def set_conf(self, conf):
        '''

        customconfig data format
        {sample: {key: value}, sample2: {key: value}}
        '''
        self.log.info("set_conf method called with {}".format(json.loads(conf)))
        try:
            config = ConfigParser.ConfigParser()
            config.optionxform = str
            conf_content = json.loads(conf)

            for sample in conf_content.iteritems():
                sample_name = sample[0]
                sample_key_value_pairs = sample[1]
                config.add_section(sample_name)
                for pair in sample_key_value_pairs.iteritems():
                    value = pair[1]
                    if type(value) == dict:
                        value = json.dumps(value)
                    config.set(sample_name, pair[0], value)

            with open(CUSTOM_CONFIG_PATH, 'wb') as conf_content:
                config.write(conf_content)

            self.eventgen_dependency.configured = True
            self.eventgen_dependency.configfile = CUSTOM_CONFIG_PATH
            self.eventgen_dependency.eventgen.reload_conf(CUSTOM_CONFIG_PATH)
            self.log.info("custom_config_json is {}".format(conf_content))
            return self.get_conf()
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def edit_conf(self, conf):
        self.log.info("edit_conf method called with {}".format(json.loads(conf)))
        try:
            config = ConfigParser.ConfigParser()
            config.optionxform = str
            conf_content = json.loads(conf)
            config.read(CUSTOM_CONFIG_PATH)

            for stanza, kv_pairs in conf_content.iteritems():
                for k, v in kv_pairs.iteritems():
                    try:
                        config.get(stanza, k)
                        config.set(stanza, k, v)
                    except Exception as e:
                        if type(e) == ConfigParser.NoSectionError:
                            config.add_section(stanza)
                        config.set(stanza, k, v)

            with open(CUSTOM_CONFIG_PATH, 'wb') as conf_content:
                config.write(conf_content)

            self.eventgen_dependency.configured = True
            self.eventgen_dependency.configfile = CUSTOM_CONFIG_PATH
            self.eventgen_dependency.eventgen.reload_conf(CUSTOM_CONFIG_PATH)
            return self.get_conf()
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def bundle(self, url):
        # Set these parameters to notify that eventgen is in the process of configuration
        self.eventgen_dependency.configured = False
        try:
            # Download the bundle
            bundle_path = self.download_bundle(url)
            # Extract bundle
            bundle_dir = self.unarchive_bundle(bundle_path)
            # Move sample files
            self.log.info("Detecting sample files...")
            if os.path.isdir(os.path.join(bundle_dir, "samples")):
                self.log.info("Moving sample files...")
                for file in glob.glob(os.path.join(bundle_dir, "samples", "*")):
                    shutil.copy(file, os.path.join(FILE_PATH, "samples"))
                self.log.info("Sample files moved!")
            # Read eventgen.conf
            self.log.info("Detecting eventgen.conf...")
            if os.path.isfile(os.path.join(bundle_dir, "default", "eventgen.conf")):
                self.log.info("Reading eventgen.conf...")
                config_dict = self.parse_eventgen_conf(os.path.join(bundle_dir, "default", "eventgen.conf"))
                # If an eventgen.conf exists, enable the configured flag
                self.eventgen_dependency.configured = True
                return self.set_conf(json.dumps(config_dict))
            else:
                return self.get_conf()
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def setup(self, data):
        if not data:
            data = {}
        if type(data) != dict:
            data = json.loads(data)
        try:
            # set default values that follow default ORCA setting
            mode = data.get("mode", "roundrobin")
            hostname_template = data.get("hostname_template", "idx{0}")
            protocol = data.get("protocol", "https")
            key = data.get("key", "00000000-0000-0000-0000-000000000000")
            key_name = data.get("key_name", "eventgen")
            password = data.get("password", "Chang3d!")
            hec_port = int(data.get("hec_port", 8088))
            mgmt_port = int(data.get("mgmt_port", 8089))
            new_key = bool(data.get("new_key", True))

            self.discovered_servers = []
            counter = 1
            while True:
                try:
                    formatted_hostname = socket.gethostbyname(hostname_template.format(counter))
                    if new_key:
                        requests.post("https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http/http".format(
                            formatted_hostname, mgmt_port),
                                      auth=("admin", password),
                                      data={"disabled": "0"},
                                      verify=False)
                        requests.post(
                            "https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http?output_mode=json".format(
                                formatted_hostname, mgmt_port),
                            verify=False,
                            auth=("admin", password),
                            data={"name": key_name})
                        r = requests.post(
                            "https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http/{2}?output_mode=json".format(
                                formatted_hostname, mgmt_port, key_name),
                            verify=False,
                            auth=("admin", password))
                        key = str(json.loads(r.text)["entry"][0]["content"]["token"])
                    self.discovered_servers.append({"protocol": str(protocol),
                                                    "address": str(formatted_hostname),
                                                    "port": str(hec_port),
                                                    "key": str(key)})
                    counter += 1
                except socket.gaierror:
                    break

            config = ConfigParser.ConfigParser()
            config.optionxform = str
            config.read(EVENTGEN_DEFAULT_CONF_PATH)
            try:
                config.get("global", "httpeventServers")
            except Exception as e:
                if type(e) == ConfigParser.NoSectionError:
                    config.add_section("global")
            config.set("global", "httpeventServers", json.dumps({"servers": self.discovered_servers}))
            config.set("global", "httpeventOutputMode", mode)
            config.set("global", "outputMode", "httpevent")

            with open(EVENTGEN_DEFAULT_CONF_PATH, 'wb') as conf_content:
                config.write(conf_content)

            return self.get_conf()
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def get_volume(self):
        self.log.info("get_volume method called")
        try:
            config = json.loads(self.get_conf())
            self.log.info(config)
            self.total_volume = float(self.get_data_volumes(config))
            self.send_volume_to_controller(total_volume=self.total_volume)
            return str(self.total_volume)
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    @rpc
    def send_volume_to_controller(self, total_volume):
        data = {}
        data['server_name'] = self.eventgen_name
        data['total_volume'] = total_volume
        self.dispatch("server_volume", data)

    def set_volume(self, volume):
        self.log.info("set_volume method called")
        try:
            config = json.loads(self.get_conf())
            # Initial total volume check
            self.get_volume()
            if not self.total_volume:
                self.log.warn("There is no stanza found with perDayVolume")
                return self.get_conf()
            ratio = float(volume) / float(self.total_volume)
            update_json = {}
            for stanza in config.keys():
                if "perDayVolume" in config[stanza].keys():
                    divided_value = float(config[stanza]["perDayVolume"]) * ratio
                    update_json[stanza] = {"perDayVolume": divided_value}
            output = self.edit_conf(json.dumps(update_json))
            self.get_volume()
            return output
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    def reset(self):
        self.log.info("reset method called")
        try:
            self.stop()
            self.eventgen_dependency.refresh_eventgen()
            return "Eventgen Refreshed"
        except Exception as e:
            self.log.exception(e)
            return '500', "Exception: {}".format(e.message)

    ##############################################
    ############ Event Handler Methods ###########
    ##############################################

    @event_handler("eventgen_controller", "all_index", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_index(self, payload):
        return self.index()

    @event_handler("eventgen_controller", "all_status", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_status(self, payload):
        return self.status()

    @event_handler("eventgen_controller", "all_start", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_start(self, payload):
        return self.start()

    @event_handler("eventgen_controller", "all_stop", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_stop(self, payload):
        return self.stop()

    @event_handler("eventgen_controller", "all_restart", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_restart(self, payload):
        return self.restart()

    @event_handler("eventgen_controller", "all_get_conf", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_get_conf(self, payload):
        return self.get_conf()

    @event_handler("eventgen_controller", "all_set_conf", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_set_conf(self, payload):
        return self.set_conf(conf=payload)

    @event_handler("eventgen_controller", "all_edit_conf", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_edit_conf(self, payload):
        return self.edit_conf(conf=payload)

    @event_handler("eventgen_controller", "all_bundle", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_bundle(self, payload):
        if payload['url']:
            return self.bundle(payload['url'])

    @event_handler("eventgen_controller", "all_setup", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_setup(self, payload):
        return self.setup(data=payload)

    @event_handler("eventgen_controller", "all_get_volume", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_get_volume(self, payload):
        return self.get_volume()

    @event_handler("eventgen_controller", "all_set_volume", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_set_volume(self, payload):
        if payload['perDayVolume']:
            return self.set_volume(payload['perDayVolume'])

    @event_handler("eventgen_controller", "all_reset", handler_type=BROADCAST, reliable_delivery=False)
    def event_handler_all_reset(self, payload):
        return self.reset()

    @event_handler("eventgen_controller", "{}_index".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_index(self, payload):
        return self.index()

    @event_handler("eventgen_controller", "{}_status".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_status(self, payload):
        return self.status()

    @event_handler("eventgen_controller", "{}_start".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_start(self, payload):
        return self.start()

    @event_handler("eventgen_controller", "{}_stop".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_stop(self, payload):
        return self.stop()

    @event_handler("eventgen_controller", "{}_restart".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_restart(self, payload):
        return self.restart()

    @event_handler("eventgen_controller", "{}_get_conf".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_get_conf(self, payload):
        return self.get_conf()

    @event_handler("eventgen_controller", "{}_set_conf".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_set_conf(self, payload):
        return self.set_conf(conf=payload)

    @event_handler("eventgen_controller", "{}_edit_conf".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_edit_conf(self, payload):
        return self.edit_conf(conf=payload)

    @event_handler("eventgen_controller", "{}_bundle".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_bundle(self, payload):
        if payload['url']:
            return self.bundle(payload['url'])

    @event_handler("eventgen_controller", "{}_setup".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_setup(self, payload):
        return self.setup(data=payload)

    @event_handler("eventgen_controller", "{}_get_volume".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_get_volume(self):
        return self.get_volume()

    @event_handler("eventgen_controller", "{}_set_volume".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_set_volume(self, payload):
        if payload['perDayVolume']:
            return self.set_volume(payload['perDayVolume'])

    @event_handler("eventgen_controller", "{}_reset".format(eventgen_name), handler_type=BROADCAST,
                   reliable_delivery=False)
    def event_handler_reset(self, payload):
        return self.reset()

    ##############################################
    ################ HTTP Methods ################
    ##############################################

    @http('GET', '/')
    def http_root(self, request):
        return self.index()

    @http('GET', '/index')
    def http_index(self, request):
        return self.index()

    @http('GET', '/status')
    def http_status(self, request):
        return self.status()

    @http('POST', '/start')
    def http_start(self, request):
        return json.dumps(self.start())

    @http('POST', '/stop')
    def http_stop(self, request):
        return json.dumps(self.stop())

    @http('POST', '/restart')
    def http_restart(self, request):
        return json.dumps(self.restart())

    @http('GET', '/conf')
    def http_get_conf(self, request):
        output = self.get_conf()
        if type(output) == str:
            return output
        else:
            return json.dumps(output)

    @http('POST', '/conf')
    def http_set_conf(self, request):
        data = request.get_data()
        if data:
            return self.set_conf(data)
        else:
            return '400', 'Please pass the valid parameters.'

    @http('PUT', '/conf')
    def http_edit_conf(self, request):
        data = request.get_data()
        if data:
            return self.edit_conf(data)
        else:
            return '400', 'Please pass valid config data.'

    @http('POST', '/bundle')
    def http_bundle(self, request):
        data = request.get_data(as_text=True)
        try:
            data = json.loads(data)
            url = data["url"]
            return self.bundle(url)
        except ValueError as e:
            self.log.exception(e)
            return '400', "Please pass in a valid object with bundle URL"
        except Exception as e:
            self.log.exception(e)
            return '400', "Exception: {}".format(e.message)

    @http('POST', '/setup')
    def http_setup(self, request):
        data = request.get_data(as_text=True)
        try:
            return self.setup(data)
        except Exception as e:
            self.log.exception(e)
            return '400', "Exception: {}".format(e.message)

    @http('GET', '/volume')
    def http_get_volume(self, request):
        return self.get_volume()

    @http('POST', '/volume')
    def http_set_volume(self, request):
        data = request.get_data(as_text=True)
        try:
            data = json.loads(data)
            volume = data["perDayVolume"]
            return self.set_volume(volume)
        except Exception as e:
            self.log.exception(e)
            return '400', "Exception: {}".format(e.message)

    @http('POST', '/reset')
    def http_reset(self, request):
        return json.dumps(self.reset())

    ##############################################
    ################ Helper Methods ##############
    ##############################################

    def parse_eventgen_conf(self, path):
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        config.read(path)
        config_dict = {s: dict(config.items(s)) for s in config.sections()}
        return config_dict

    def download_bundle(self, url):
        self.log.info("Downloading bundle at {}...".format(url))
        # Use SPLUNK_HOME if defined
        if "SPLUNK_HOME" in os.environ:
            bundle_path = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", "eg-bundle.tgz")
        else:
            bundle_path = os.path.join(os.getcwd(), "eg-bundle.tgz")
        r = requests.get(url, stream=True)
        with open(bundle_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    f.write(chunk)
        r.close()
        self.log.info("Download complete!")
        return bundle_path

    def unarchive_bundle(self, path):
        self.log.info("Extracting bundle {}...".format(path))
        output = None
        # Use tarfile or zipfile, depending on the bundle
        if tarfile.is_tarfile(path):
            tar = tarfile.open(path)
            output = os.path.join(os.path.dirname(path), os.path.commonprefix(tar.getnames()))
            tar.extractall(path=os.path.dirname(path))
            tar.close()
        elif zipfile.is_zipfile(path):
            zipf = zipfile.ZipFile(path)
            output = os.path.join(os.path.dirname(path), "eg-bundle")
            zipf.extractall(path=output)
            zipf.close()
        else:
            msg = "Unknown archive format!"
            self.log.exception(msg)
            raise Exception(msg)
        self.log.info("Extraction complete!")
        return output

    def get_data_volumes(self, config):
        '''
        This method updates the total volume from the eventgen.conf

        :param config: (dict) object representing the current state of the server's eventgen.conf
        '''
        total_volume = 0
        for stanza in config.keys():
            if "perDayVolume" in config[stanza].keys():
                total_volume += float(config[stanza]["perDayVolume"])
        self.log.info("Total volume is currently {}".format(total_volume))
        return total_volume
