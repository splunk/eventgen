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
import requests
import requests_futures
from requests import Session
from lib.requests_futures.sessions import FuturesSession
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor

class CounterObject():
    def __init__(self):
        self.num = 0

class EventgenBarrageEngine(object):
    def __init__(self, args=None):
        if not args:
            print "No arguments supplied. Exiting."
            sys.exit(1)
        
        # Load data from a sample file
        self.sample_lines = []
        self.load_sample(args.sample_file)

        # Set default thresholds
        self.cpu_threshold = 80
        self.payload_max_size = 10000

        # Set variables needed for data processing and sharing
        self.multiprocessing_manager = multiprocessing.Manager()
        self.event_count = self.multiprocessing_manager.Value('i', 0)
        self.processes = list()
        self.preprocessed_payload_templates = list()

        # Set Event related variables
        self.event_index = args.event_index
        self.event_source = args.event_source
        self.event_sourcetype = args.event_sourcetype
        self.event_host = args.event_host
        
        # Set HTTP End Point variables
        self.server_address = args.server_address
        self.server_port = args.server_port
        self.server_hec_token = args.server_hec_token
        self.server_protocol = args.server_protocol
        self.server_endpoint_url = "{protocol}://{server_address}:{server_port}/services/collector/event".format(protocol=self.server_protocol, server_address=self.server_address, server_port=self.server_port)
        self.request_header = {"Authorization": "Splunk {}".format(self.server_hec_token), "content-type": "application/json"}
        self.request_body = {"index": self.event_index, "sourcetype": self.event_sourcetype, "source": self.event_source, "host": self.event_host}

        self.preprocess_payloads()

        signal.signal(signal.SIGINT, self.handle_signal)
    
    def preprocess_payloads(self):
        current_payload = ''
        current_sample_line_index = 0
        ready_to_quit = False
        all_events_size = 0
        while 1:
            self.request_body['event'] = self.sample_lines[current_sample_line_index]
            payload = json.dumps(self.request_body)
            if len(current_payload) + len(payload) < self.payload_max_size:
                current_payload += payload
                all_events_size += len(self.sample_lines[current_sample_line_index])
            else:
                self.preprocessed_payload_templates.append(current_payload)
                current_payload = payload
                if ready_to_quit:
                    break
            current_sample_line_index += 1
            if current_sample_line_index == len(self.sample_lines):
                current_sample_line_index = 0
                ready_to_quit = True

        for i in self.preprocessed_payload_templates:
            print len(i)
        
        self.all_events_size = all_events_size
        print "All events size is {}".format(self.all_events_size)

    def _setup_REST_workers(self, session=None, max_workers=50):
        requests.packages.urllib3.disable_warnings()
        if not session:
            session = Session()
        self.session = FuturesSession(session=session, executor=ThreadPoolExecutor(max_workers=max_workers))

    def create_threads(self):
        def generate_http_events(counter_object):
            preprocessed_payload_templates = self.preprocessed_payload_templates
            while 1:
                for payload_template in preprocessed_payload_templates:
                    try:
                        self.session.post(url=self.server_endpoint_url, headers=self.request_header, data=payload_template, verify=False)
                    except Exception as e:
                        continue
                # counter.num += 1

        counter = CounterObject()
        self._setup_REST_workers()

        threads = []
        for _ in range(20):
            thread = threading.Thread(target=generate_http_events, args=(counter,)) 
            threads.append(thread)
        for thread in threads:
            thread.start()
        
        # Count the number of iterations and reset the counter
        while 1:
            time.sleep(10)
            # if counter.num > 10000:
            #     self.event_count.value += counter.num
            #     counter.num = 0
    
    def start(self):
        while 1:
            cpu_usage = EventgenBarrageEngine._get_current_cpu_usage()
            if  cpu_usage <= self.cpu_threshold:
                p = multiprocessing.Process(target=self.create_threads)
                self.processes.append(p)
                p.start()
            elif cpu_usage >= 90 and len(self.processes) > 0:
                last_pid = self.processes[0].pid
                os.kill(last_pid, 9)
                self.processes.pop(0)
            print '{0} process in action. CPU usage: {1}%'.format(len(self.processes), cpu_usage)
            # print "Generated {} iterations".format(self.event_count.value)
            # print "Generated {}gb data so far".format(round(self.event_count.value * self.all_events_size)/1024/1024/1024.0, 2)
            time.sleep(5)

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
                    self.sample_lines.append(line.rstrip('\n'))
            if not self.sample_lines:
                print "Found a sample file, but did not find any lines. Exiting."
                sys.exit(1)
            else:
                print "Loaded {0} lines from {1}".format(len(self.sample_lines), sample_file_path)
    
    def handle_signal(self, signum, frame):
        pids = [process.pid for process in self.processes]
        if os.getpid() not in pids:
            # Iteratively kill all child processes if the current process is the parent process
            for p in self.processes:
                os.kill(p.pid, 9)
        sys.exit(0)

    @staticmethod
    def _get_current_cpu_usage():
        cpu_percent_sum = psutil.cpu_percent()
        return int(cpu_percent_sum)