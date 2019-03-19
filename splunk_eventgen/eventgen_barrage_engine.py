import psutil
import time
import multiprocessing
import threading
import signal
import sys
import os
import requests
import json

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CounterObject():
    def __init__(self):
        self.num = 0

class EventgenBarrageEngine(object):
    def __init__(self, args=None):
        if not args:
            print "No arguments supplied. Exiting."
            sys.exit(1)

        self.cpu_threshold = 80
        self.multiprocessing_manager = multiprocessing.Manager()
        self.processes = []
        self.event_count = self.multiprocessing_manager.Value('i', 0)
        self.sample_lines = []
        self.preprocessed_payload_templates = []
        self.load_sample(args.sample_file)
        self.server_address = args.server_address
        self.server_port = args.server_port
        self.server_hec_token = args.server_hec_token
        self.server_protocol = args.server_protocol
        self.event_index = args.event_index
        self.event_source = args.event_source
        self.event_sourcetype = args.event_sourcetype
        self.event_host = args.event_host
        signal.signal(signal.SIGINT, self.handle_signal)

        self.payload_max_size = 9000

        self.url = "{protocol}://{server_address}:{server_port}/services/collector/event".format(protocol=self.server_protocol, server_address=self.server_address, server_port=self.server_port)
        self.header = {"Authorization": "Splunk {}".format(self.server_hec_token), "content-type": "application/json"}
        self.body = {"index": self.event_index, "sourcetype": self.event_sourcetype, "source": self.event_source, "host": self.event_host}

    def preprocess_payloads(self):
        current_payload_size = 0
        current_payload = ''
        while current_payload_size 
            


    def create_threads(self):
        counter = CounterObject()
        def generate_http_events(counter_object):
            current_line_index = 0
            sample_lines_length = len(self.sample_lines)
            current_time = round(time.time(), 3)
            while True:
                counter_object.num += 1
                if current_line_index >= sample_lines_length - 1:
                    current_line_index = 0
                else:
                    current_line_index += 1
                body = self.body
                body['event'] = self.sample_lines[current_line_index]
                
                try:
                    r = requests.post(self.url, headers=self.header, data=json.dumps(body), verify=False)
                    if r.status_code != 200:
                        print r.text
                except Exception as e:
                    print dir(e)
                    print e
                    continue
        threads = []
        for _ in range(20): # each Process creates a number of new Threads
            thread = threading.Thread(target=generate_http_events, args=(counter,)) 
            threads.append(thread)
        for thread in threads:
            thread.start()
        i = 0
        while True:
            if i % 10000 == 0:
                self.event_count.value += counter.num
                counter.num = 0
            i += 1
    
    def start(self):
        while True:
            cpu_usage = EventgenBarrageEngine._get_current_cpu_usage()
            if  cpu_usage <= self.cpu_threshold - 5:
                p = multiprocessing.Process(target=self.create_threads)
                self.processes.append(p)
                p.start()
            elif cpu_usage >= 95 and len(self.processes) > 0:
                last_pid = self.processes[-1].pid
                os.kill(last_pid, 9)
                self.processes.pop()
            print '{0} process in action. CPU usage: {1}%'.format(len(self.processes), cpu_usage)
            print "Generated {} Events".format(self.event_count.value)
            time.sleep(5)
    
    def handle_signal(self, signum, frame):
        pids = [process.pid for process in self.processes]
        if os.getpid() not in pids:
            # Iteratively kill all child processes if the current process is the parent process
            for p in self.processes:
                os.kill(p.pid, 9)
        sys.exit(0)

    def load_sample(self, sample_file):
        current_dir_path = os.path.dirname(os.path.realpath(__file__))
        sample_file_path = os.path.realpath(os.path.join(current_dir_path, '..', sample_file))
        if not os.path.isfile(sample_file_path):
            print "Sample file does not exist in a current working directory. Exiting."
            sys.exit(1)
        else:
            with open(sample_file_path, "r") as f:
                lines = f.readlines()
                for line in lines:
                    self.sample_lines.append(line.strip())
                print "Loaded a sample file"

    @staticmethod
    def _get_current_cpu_usage():
        cpu_percent_sum = psutil.cpu_percent()
        return int(cpu_percent_sum)