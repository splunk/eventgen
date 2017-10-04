import argparse
import cherrypy
import ConfigParser
import eventgenapi_common
import json
import os
import logging
import logging.config
import requests
import shutil
import socket
import subprocess
import tarfile
import time
import tempfile
import urllib
import eventgen_core

FILE_PATH = os.path.dirname(os.path.realpath(__file__))

# try:
#     SPLUNK_HOME = os.environ["SPLUNK_HOME"]
# except KeyError:
#     SPLUNK_HOME = os.path.join("/opt","splunk")
# EVENTGEN_PATH = os.path.join(SPLUNK_HOME,"etc","apps","SA-Eventgen")
# EVENTGEN_RESOURCES = os.path.join(EVENTGEN_PATH,"samples")
# EVENTGEN_CMD = os.path.join(EVENTGEN_PATH,"bin","eventgen.py")

# def parseArgs():
#     parser = argparse.ArgumentParser(prog='eventgen_server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#     parser.add_argument("--eventgencmd", type=str, default=EVENTGEN_CMD, help="name of eventgen python file")
#     parser.add_argument("--daemon", type=str, default=False, help="Run in a daemonized mode, daemon=True")
#     return parser.parse_args()
#
class NamedPart(cherrypy._cpreqbody.Part):
    def make_file(self):
        return tempfile.NamedTemporaryFile()

class EventgenApiServer(object):
    '''
    Provides a RESTful interface for controlling and managing Eventgen
    '''
    EVENTGEN_DIR = os.path.dirname(os.path.normpath(os.path.join(__file__, "..")))

    def __init__(self, args=None):
        self.args = args
        if args:
            self.configure_default_args()
        self.eventgen = eventgen_core.EventGenerator(args)
        self.host = socket.gethostname()
        self.configured = False
        self.configfile = 'N/A'
        self.setup_loggers()

    def configure_default_args(self):
        self.args.backfill = None
        self.args.count = None
        self.args.devnull = False
        self.args.disableOutputQueue = False
        self.args.end = None
        self.args.generatros = None
        self.args.interval = None
        self.args.keepoutput = False
        self.args.modinput = False
        self.args.multiprocess = False
        self.args.outputters = None
        self.args.profiler = False
        self.args.sample = None
        self.args.version = False
        self.args.subcommand = 'generate'
        self.args.verbosity = 1
        self.args.wsgi = True

    def setup_loggers(self):
        self.logger = logging.getLogger('eventgen_wsgi')

    @cherrypy.expose
    def index(self):
        if cherrypy.request.method == "GET":
            home_page = '''<h1>Eventgen WSGI</h1>
            <p>Host: {0}</p>
            <p>Eventgen Status: {1}</p>
            <p>Eventgen Config file exists: {2}</p>
            <p>Eventgen Config file path: {3}</p>
            <p>Worker Queue Status: {4}</p>
            <p>Sample Queue Status: {5}</p>
            <p>Output Queue Status: {6}</p>
            
            '''
            # appName = "None"
            # app_conf_path = os.path.join(self.data_path,"app","default","app.conf")
            # if os.path.isfile(app_conf_path):
            #     c = ConfigParser.ConfigParser()
            #     c.read(app_conf_path)
            #     try:
            #         appName = c.get("ui","label")
            #     except ConfigParser.NoOptionError:
            #         appName = "default"
            status = self.get_status()
            eventgen_status = "running" if status["EVENTGEN_STATUS"] else "stopped"
            host = status["EVENTGEN_HOST"]
            configured = status["CONFIGURED"]
            config_file = status["CONFIG_FILE"]
            worker_queue_status = status["QUEUE_STATUS"]["WORKER_QUEUE"]
            sample_queue_status = status["QUEUE_STATUS"]["SAMPLE_QUEUE"]
            output_queue_status = status["QUEUE_STATUS"]["OUTPUT_QUEUE"]

            return home_page.format(host,
                                    eventgen_status,
                                    configured,
                                    config_file,
                                    worker_queue_status,
                                    sample_queue_status,
                                    output_queue_status)
        else:
            cherrypy.response.status = 400
            return "Unsupported method. Please use GET."

    def get_status(self):
        '''
        Get status of eventgen

        return value structure
        {
            "EVENTGEN_STATUS" :
            "EVENTGEN_HOST" :
            "CONFIGURED" :
            "CONFIG_FILE" :
            "QUEUE_STATUS" : { "SAMPLE_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': },
                               "OUTPUT_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': },
                               "WORKER_QUEUE": {'UNFISHED_TASK': , 'QUEUE_LENGTH': }}
        }
        '''
        res = dict()
        if self.eventgen.check_running():
            status = 1
        else:
            status = 0
        res["EVENTGEN_STATUS"] = status
        res["EVENTGEN_HOST"] = self.host
        res["CONFIGURED"] = self.configured
        res["CONFIG_FILE"] = self.configfile
        res["QUEUE_STATUS"] = {'SAMPLE_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'},
                               'OUTPUT_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'},
                               'WORKER_QUEUE': {'UNFINISHED_TASK': 'N/A', 'QUEUE_LENGTH': 'N/A'}}

        if hasattr(self.eventgen, "sampleQueue"):
            res["QUEUE_STATUS"]['SAMPLE_QUEUE']['UNFINISHED_TASK'] = self.eventgen.sampleQueue.unfinished_tasks
            res["QUEUE_STATUS"]['SAMPLE_QUEUE']['QUEUE_LENGTH'] = self.eventgen.sampleQueue.qsize()
        if hasattr(self.eventgen, "outputQueue"):
            res["QUEUE_STATUS"]['OUTPUT_QUEUE']['UNFINISHED_TASK'] = self.eventgen.outputQueue.unfinished_tasks
            res["QUEUE_STATUS"]['OUTPUT_QUEUE']['QUEUE_LENGTH'] = self.eventgen.outputQueue.qsize()
        if hasattr(self.eventgen, "workerQueue"):
            res["QUEUE_STATUS"]['WORKER_QUEUE']['UNFINISHED_TASK'] = self.eventgen.workerQueue.unfinished_tasks
            res["QUEUE_STATUS"]['WORKER_QUEUE']['QUEUE_LENGTH'] = self.eventgen.workerQueue.qsize()
        return res

    @cherrypy.expose
    def status(self):
        '''
        Wrapper to convert dict to string
        :return: returns status
        :rtype: string
        '''
        if cherrypy.request.method == "GET":
            return json.dumps(self.get_status(), indent=4)
        else:
            cherrypy.response.status = 400
            return "Unsupported method. Please use GET."

    @cherrypy.expose
    def start(self):
        '''
        Starts eventgen process
        '''
        if cherrypy.request.method == "POST":
            if not self.configured:
                cherrypy.response.status = 400
                return "There is not config file known to eventgen. Pass in the config file to /conf before you start."
            if self.eventgen.check_running():
                cherrypy.response.status = 409
                return "Eventgen already started."
            try:
                self.eventgen.start(join_after_start=False)
                return "Eventgen has successfully started."
            except Exception as e:
                cherrypy.response.status = 500
                return "Exception: {}".format(e.message)
        else:
            cherrypy.response.status = 400
            return "Unsupported request method. Please use POST."

    @cherrypy.expose
    def stop(self):
        '''
        Stops the eventgen process
        '''
        if cherrypy.request.method == "POST":
            try:
                if self.eventgen.check_running():
                    self.eventgen.stop()
                    return "Eventgen is stopped."
                return "There is no eventgen process running."
            except Exception as e:
                cherrypy.response.status = 500
                return "Exception: {}".format(e.message)
        else:
            cherrypy.response.status = 400
            return "Unsupported request method. Please use POST."

    @cherrypy.expose
    def restart(self):
        '''
        Stops then starts the Eventgen process

        POST: no params
        '''
        if cherrypy.request.method == "POST":
            self.stop()
            time.sleep(2)
            self.start()
            return 'hello'
        else:
            cherrypy.response.status = 400
            return "Unsupported request method. Please use POST."

    @cherrypy.expose
    def conf(self, configfile=None):
        '''
        Manages the Eventgen config file

        GET: no params
        POST: configfile[string]: path to config file. i.e. tests/sample_eventgen_conf/windbag/eventgen.conf.windbag
        '''
        if cherrypy.request.method == "GET":
            try:
                if not self.configured:
                    cherrypy.response.status = 409
                    return "There is no conf file known to eventgen."
                config = ConfigParser.ConfigParser()
                config.read(os.path.abspath(os.path.join(EventgenApiServer.EVENTGEN_DIR, self.configfile)))
                out_json = dict()
                for section in config.sections():
                    out_json[section] = dict()
                    for k, v in config.items(section):
                        out_json[section][k] = v
                return json.dumps(out_json, indent=4)
            except Exception as e:
                cherrypy.response.status = 500
            return "Exception: {}".format(e.message)

        elif cherrypy.request.method == "POST":
            if not configfile or not os.path.isfile(
                os.path.abspath(os.path.join(EventgenApiServer.EVENTGEN_DIR, configfile))):
                cherrypy.response.status = 409
                return 'Provide the correct config file.'
            else:
                try:
                    cherrypy.response.status = 200
                    self.eventgen.reload_conf(configfile)
                    self.configfile = configfile
                    self.configured = True
                    return 'Loaded the conf file: {}'.format(self.configfile)
                except Exception as e:
                    cherrypy.response.status = 500
                    return "Exception: {}".format(e.message)

        else:
            cherrypy.response.status = 400
            return "Unsupported request method. Please use GET or POST."

    # def set_eventgen_executable(self, eventgencmd):
    #     self.eventgencmd = eventgencmd
    #     self.data_path = os.path.join(SPLUNK_HOME,"etc","apps","datamix")
    #     self.app_path = os.path.join(self.data_path,"app")
    #     self.state_path = os.path.join(self.app_path,"lookups")
    #     app_conf refers to app's eventgen.conf
    #     self.app_conf_path = os.path.join(self.app_path,"default","eventgen.conf")
    #     eventgen_conf refers to eventgen's eventgen.conf
    #     if not os.path.isdir(self.data_path):
    #         os.mkdir(self.data_path)
    #
    # def set_eventgen_baseoptions(self):
    #     self.load_eventgen_conf()
    #     self.load_app_conf()
    #     self.eventgen_conf.set("global","threading","process")
    #     self.eventgen_conf.set("global","outputMode","httpevent")
    #     self.eventgen_conf.set("global","httpeventOutputMode","roundrobin")
    #     self.eventgen_conf.set("global","useOutputQueue","false")
    #     self.eventgen_conf.set("global","maxQueueLength","438860800") #Splunk max is max_content_length = 838860800
    #     self.eventgen_conf.set("global","generatorWorkers","24")
    #     self.eventgen_conf.set("global","maxIntervalsBeforeFlush","1")
    #     self.servers = []
    #     self.save()
    #
    # def validate_app(self,app_path):
    #     '''
    #     Verifies the app has at least a eventgen.conf and samples folder. Returns false otherwise
    #     '''
    #     if not os.path.isfile(os.path.join(app_path,"default","eventgen.conf")):
    #         return False
    #     if not os.path.isdir(os.path.join(app_path,"samples")):
    #         return False
    #     return True
    #
    # def load_app_conf(self,clean=True):
    #     '''
    #     Loads the app eventgen.conf into a ConfigParser.
    #     clean=True resets ConfigParser and rereads the eventgen.conf instead of updating
    #     '''
    #     if clean:
    #         self.app_conf = ConfigParser.ConfigParser()
    #         self.app_conf.optionxform = str
    #     self.app_conf.read(self.app_conf_path)
    #
    # def load_eventgen_conf(self,clean=True):
    #     '''
    #     Loads the eventgen eventgen.conf into a ConfigParser.
    #     clean=True resets ConfigParser and rereads the eventgen.conf instead of updating
    #     '''
    #     if clean:
    #         self.eventgen_conf = ConfigParser.ConfigParser()
    #         self.eventgen_conf.optionxform = str
    #     self.eventgen_conf.read(self.eventgen_conf_path)
    #
    # def get_data_volumes(self):
    #     '''
    #     Updates the total volume from the eventgen.conf
    #     '''
    #     self.load_app_conf(clean=False)
    #     self.total_volume = 0
    #     for section in self.app_conf.sections():
    #         if "perDayVolume" in self.app_conf.options(section):
    #             self.total_volume += float(self.app_conf.get(section,"perDayVolume"))
    #     return self.total_volume
    #
    # @cherrypy.expose
    # def datavolume(self, gb=None):
    #     '''
    #     Returns the total data volume in gb/day
    #     '''
    #     if gb:
    #         self.setvolume(gb)
    #     return str(self.get_data_volumes())
    #
    # @cherrypy.expose
    # def setvolume(self,gb):
    #     '''
    #     Sets total volume per day to value specified by gb (units in GB/day).
    #     Scales the perDayVolumes in the stanzas to meet the total volume
    #     '''
    #     ratio = 1
    #     self.get_data_volumes()
    #     if self.total_volume>0:
    #         ratio = float(gb)/float(self.total_volume)
    #         for section in self.app_conf.sections():
    #             if "perDayVolume" in self.app_conf.options(section):
    #                 self.app_conf.set(section,"perDayVolume",float(self.app_conf.get(section,"perDayVolume"))*ratio)
    #     self.save()
    #     self.load_app_conf()
    #     return self.appconf()
    #
    # @cherrypy.expose
    # def save(self):
    #     '''
    #     Saves the eventgen.conf and restart eventgen
    #     '''
    #     with open(self.eventgen_conf_path,"wb") as conf:
    #         self.eventgen_conf.write(conf)
    #     if os.path.isfile(self.app_conf_path):
    #         with open(self.app_conf_path,"wb") as conf:
    #             self.app_conf.write(conf)
    #     if self.process:
    #         self.restart()
    #     return "Success"
    #
    # def untar_app(self,file_path):
    #     '''
    #     Untars the package. Does basic validation tests.
    #     '''
    #     with tarfile.open(file_path) as tmp_app:
    #         app_name = os.path.commonprefix(tmp_app.getnames())
    #         for name in tmp_app.getnames():
    #             if os.path.join(os.getcwd(),name) != os.path.abspath(name):
    #                 return "Unsafe file"
    #         tmp_app.extractall(self.data_path)
    #         if self.validate_app(os.path.join(self.data_path,app_name)):
    #             # Delete old app if it exists
    #             if os.path.isdir(self.app_path):
    #                 shutil.rmtree(self.app_path)
    #             os.rename(os.path.join(self.data_path,app_name),self.app_path)
    #         else:
    #             shutil.rmtree(os.path.join(self.data_path,app_name))
    #             return "Invalid app"
    #     os.remove(file_path)
    #
    # @cherrypy.expose
    # def upload(self,app,override=True):
    #     '''
    #     Endpoint to receive app. To use, POST app to endpoint.
    #     '''
    #     if override:
    #         tmp_path = os.path.join(self.data_path,"app.tgz")
    #         shutil.move(app.file.name,tmp_path)
    #         self.untar_app(tmp_path)
    #         self.load_app_conf(clean=True)
    #
    #         return "Success"
    #
    # @cherrypy.expose
    # def fetch(self,url,override=True):
    #     '''
    #     Grab the app from the specified url (i.e. https://www.splunk.com/file.tgz)
    #     '''
    #     if override:
    #         tmp_path = os.path.join(self.data_path,"app.tgz")
    #         shutil.move(urllib.urlretrieve(url)[0],tmp_path)
    #         self.untar_app(tmp_path)
    #         self.load_app_conf(clean=True)
    #         return "Success"
    #
    # @cherrypy.expose
    # def uploadsample(self,name,sample,override=True):
    #     '''
    #     Name (str): filename of the sample
    #     sample (str): content of the sample
    #     override (Boolean): True if you want to override the current sample if it exists
    #     '''
    #     sample_path = os.path.join(self.app_path,"samples",name)
    #     if override:
    #         if os.path.isfile(sample_path):
    #             os.remove(sample_path)
    #     else:
    #         if os.path.isfile(sample_path):
    #             return "Sample {0} already present".format(name)
    #     with open(sample_path,"wb") as f:
    #         f.write(sample)
    #     return "Success"
    #
    # @cherrypy.expose
    # def setup(self,mode="roundrobin", addr_template="idx{0}", protocol="https",key="00000000-0000-0000-0000-000000000000",key_name="eventgen",password="changed",hec_port=8088, mgmt_port=8089,auto_save=True, new_key=True):
    #     '''
    #     Point eventgen at all the indexers. Create HEC key if needed
    #     '''
    #     self.servers = []
    #     counter = 1
    #     while True:
    #         try:
    #             addr = socket.gethostbyname(addr_template.format(counter))
    #             if new_key:
    #                 requests.post("https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http?output_mode=json".format(addr,mgmt_port), verify=False, auth=("admin",password), data={"name":key_name})
    #                 r = requests.post("https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http/{2}?output_mode=json".format(addr,mgmt_port,key_name), verify=False, auth=("admin",password))
    #                 key = str(json.loads(r.text)["entry"][0]["content"]["token"])
    #             self.servers.append({"protocol":str(protocol), "address":str(addr), "port":str(hec_port), "key":str(key)})
    #             counter += 1
    #         except socket.gaierror:
    #             break
    #     self.eventgen_conf.set("global","httpeventServers",json.dumps({"servers": self.servers}))
    #     self.eventgen_conf.set("global","httpeventOutputMode",mode)
    #     if auto_save:
    #         self.save()
    #     cherrypy.response.status = 200
    #     return self.index()
    #
    # @cherrypy.expose
    # def addcluster(self, cluster_master="master", mode="roundrobin", protocol="https",key="00000000-0000-0000-0000-000000000000",key_name="eventgen",password="changed",hec_port=8088, mgmt_port=8089,auto_save=True, new_key=True):
    #     '''
    #     Forward to the indexers of a cluster master. should probably combine this with the add endpoint.
    #     '''
    #     try:
    #         r = requests.get("https://{0}:{1}/services/cluster/master/peers?output_mode=json".format(cluster_master,mgmt_port),auth=("admin",password),verify=False, timeout=30)
    #         r.raise_for_status()
    #     except requests.exceptions.HTTPError:
    #         r = requests.get("https://{0}:{1}/services/cluster/master/peers?output_mode=json".format("master1", mgmt_port),auth=("admin", password), verify=False, timeout=30)
    #         r.raise_for_status()
    #     except requests.exceptions.ConnectionError:
    #         r = requests.get("https://{0}:{1}/services/cluster/master/peers?output_mode=json".format("master1", mgmt_port),auth=("admin", password), verify=False, timeout=30)
    #         r.raise_for_status()
    #     peers = json.loads(r.text)["entry"]
    #     for peer in peers:
    #         host_port_pair = peer["content"]["host_port_pair"]
    #         addr,peer_mgmt_port = host_port_pair.split(":")
    #         requests.post("https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http?output_mode=json".format(addr,peer_mgmt_port), verify=False, auth=("admin",password), data={"name":key_name})
    #         r = requests.post("https://{0}:{1}/servicesNS/admin/splunk_httpinput/data/inputs/http/{2}?output_mode=json".format(addr,peer_mgmt_port,key_name), verify=False, auth=("admin",password))
    #         key = str(json.loads(r.text)["entry"][0]["content"]["token"])
    #         self.servers.append({"protocol":str(protocol), "address":str(addr), "port":str(hec_port), "key":str(key)})
    #     self.eventgen_conf.set("global","httpeventServers",json.dumps({"servers": self.servers}))
    #     self.eventgen_conf.set("global","httpeventOutputMode",mode)
    #     if auto_save:
    #         self.save()
    #     cherrypy.response.status = 200
    #     return self.index()
    #
    # @cherrypy.expose
    # def reset(self):
    #     '''
    #     Reset list of indexers being forwarded to
    #     '''
    #     self.servers = []
    #     self.eventgen_conf.set("global","httpeventServers",json.dumps({"servers": self.servers}))
    #     self.save()
    #     cherrypy.response.status = 200
    #     return self.index()
    #
    # @cherrypy.expose
    # def add(self,address,protocol="https",key="00000000-0000-0000-0000-000000000000",port=8088,auto_save=True):
    #     '''
    #     Add http event collector forwarding
    #     address (str): ip address or host name (i.e. server1). Submit multiple by delimiting address with ,
    #     protocol (str): https or http
    #     key (str): http event collector token
    #     port (int): http event collector port
    #     '''
    #     for addr in address.split(","):
    #         self.servers.append({"protocol":str(protocol), "address":str(addr), "port":str(port), "key":str(key)})
    #     self.eventgen_conf.set("global","httpeventServers",json.dumps({"servers": self.servers}))
    #     if auto_save:
    #         self.save()
    #     cherrypy.response.headers['Content-Type'] = "text"
    #     cherrypy.response.status = 200
    #     return str(self.servers)
    #
    # @cherrypy.expose
    # def appconf(self,sample=None,field="perDayVolume", value=0):
    #     '''
    #     Returns the contents of the app's eventgen.conf
    #     '''
    #     cherrypy.response.headers['Content-Type'] = "text"
    #     if sample:
    #         if field in self.app_conf.options(sample):
    #             self.app_conf.set(sample, field, value)
    #             self.save()
    #     try:
    #         f = open(self.app_conf_path, 'r')
    #         return f.read()
    #     except IOError:
    #         cherrypy.response.status = 404
    #         return "File not found"
