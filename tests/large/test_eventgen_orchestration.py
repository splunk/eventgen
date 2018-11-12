#!/usr/bin/env python
# encoding: utf-8

import os
import time
import json
import pytest
import requests
from docker import APIClient
from random import choice
from string import ascii_lowercase
# Code to suppress insecure https warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")
IMAGE_NAME = "eventgen:test"
NETWORK_NAME = "eg_network_test"

def generate_random_string():
    return ''.join(choice(ascii_lowercase) for b in range(20))

def wait_for_response(url, timeout=60):
    start, end = time.time(), time.time()
    while end-start < timeout:
        try:
            r = requests.get(url)
            r.raise_for_status()
            break
        except:
            time.sleep(2)
            end = time.time()


@pytest.mark.large
class TestEventgenOrchestration(object):
	'''
	This test class is used to test the Docker image published as part of this repo.
	Specifically, this is testing:
		* Eventgen "controller" API and responses
		* Eventgen "server" API and responses
		* Eventgen controller/server orchestration
	'''

	@classmethod
	def setup_class(cls):
		# Build the image from scratch
		cls.client = APIClient(base_url="unix://var/run/docker.sock")
		response = cls.client.build(path=REPO_DIR, dockerfile=os.path.join("dockerfiles", "Dockerfile"), tag=IMAGE_NAME, rm=True, nocache=True, pull=True, stream=False)
		for line in response:
			print line,
		# Create a network for both the controller + server to run in
		cls.client.create_network(NETWORK_NAME, driver="bridge", attachable=True)
		networking_config = cls.client.create_networking_config({NETWORK_NAME: cls.client.create_endpoint_config()})
		# Start the controller
		print 'creating controller'
		host_config = cls.client.create_host_config(auto_remove=True, publish_all_ports=True)
		container = cls.client.create_container(image=IMAGE_NAME, 
												command="controller",
												host_config=host_config,
												networking_config=networking_config)
		cls.client.start(container["Id"])
		TestEventgenOrchestration.controller_id = container["Id"]
		print container["Id"]
		cls.controller_container = cls.client.inspect_container(container["Id"])
		cls.controller_eventgen_webport = cls.controller_container["NetworkSettings"]["Ports"]["9500/tcp"][0]["HostPort"]
		cls.controller_rabbitmq_webport = cls.controller_container["NetworkSettings"]["Ports"]["15672/tcp"][0]["HostPort"]
		# Start the server
		print 'creating server'
		container = cls.client.create_container(image=IMAGE_NAME, 
												command="server",
												environment=["EVENTGEN_AMQP_HOST={}".format(cls.controller_container["Id"][:12])],
												host_config=host_config,
												networking_config=networking_config)
		cls.client.start(container["Id"])
		TestEventgenOrchestration.server_id = container["Id"]
		print container["Id"]
		cls.server_container = cls.client.inspect_container(container["Id"])
		cls.server_eventgen_webport = cls.server_container["NetworkSettings"]["Ports"]["9500/tcp"][0]["HostPort"]
		cls.server_rabbitmq_webport = cls.server_container["NetworkSettings"]["Ports"]["15672/tcp"][0]["HostPort"]
		# Wait for the controller to be available
		wait_for_response("http://127.0.0.1:{}".format(cls.controller_eventgen_webport))
		# Wait for the server to be available
		wait_for_response("http://127.0.0.1:{}".format(cls.server_eventgen_webport))

	@classmethod
	def teardown_class(cls):
		cls.client.remove_container(cls.server_container, v=True, force=True)
		cls.client.remove_container(cls.controller_container, v=True, force=True)
		cls.client.remove_image(IMAGE_NAME, force=True, noprune=False)
		cls.client.remove_network(NETWORK_NAME)

	### Controller tests ###

	def test_controller_rabbitmq(self):
		r = requests.get("http://127.0.0.1:{}".format(self.controller_rabbitmq_webport))
		assert r.status_code == 200
		assert "RabbitMQ" in r.content
	
	def test_controller_root(self):
		r = requests.get("http://127.0.0.1:{}".format(self.controller_eventgen_webport))
		assert r.status_code == 200
		assert "Eventgen Controller" in r.content
		assert "Host: " in r.content
		assert "You are running Eventgen Controller" in r.content
	
	def test_controller_index(self):
		r = requests.get("http://127.0.0.1:{}/index".format(self.controller_eventgen_webport))
		assert r.status_code == 200
		assert "Eventgen Controller" in r.content
		assert "Host: " in r.content
		assert "You are running Eventgen Controller" in r.content
	
	def test_controller_status(self):
		r = requests.get("http://127.0.0.1:{}/status".format(self.controller_eventgen_webport))
		assert r.status_code == 200
		output = json.loads(r.content)
		assert output
	
	def test_controller_start(self):
		r = requests.post("http://127.0.0.1:{}/start".format(self.controller_eventgen_webport))
		assert r.status_code == 200
		assert "Start event dispatched to all" in r.content
	
	def test_controller_start_with_target(self):
		r = requests.post("http://127.0.0.1:{}/start/{}".format(self.controller_eventgen_webport, TestEventgenOrchestration.server_id[:12]))
		assert r.status_code == 200
		assert "Start event dispatched to {}".format(TestEventgenOrchestration.server_id[:12]) in r.content
	
	def test_controller_stop(self):
		r = requests.post("http://127.0.0.1:{}/stop".format(self.controller_eventgen_webport))
		assert r.status_code == 200
		assert "Stop event dispatched to all" in r.content
	
	def test_controller_stop_with_target(self):
		r = requests.post("http://127.0.0.1:{}/stop/{}".format(self.controller_eventgen_webport, TestEventgenOrchestration.server_id[:12]))
		assert r.status_code == 200
		assert "Stop event dispatched to {}".format(TestEventgenOrchestration.server_id[:12]) in r.content
	
	def test_controller_restart(self):
		r = requests.post("http://127.0.0.1:{}/stop".format(self.controller_eventgen_webport))
		assert r.status_code == 200
		assert "Stop event dispatched to all" in r.content
		
	def test_controller_restart_with_target(self):
		r = requests.post("http://127.0.0.1:{}/stop/{}".format(self.controller_eventgen_webport, TestEventgenOrchestration.server_id[:12]))
		assert r.status_code == 200
		assert "Stop event dispatched to {}".format(TestEventgenOrchestration.server_id[:12]) in r.content
	
	def test_controller_bundle_invalid_request(self):
		r = requests.post("http://127.0.0.1:{}/bundle".format(self.controller_eventgen_webport))
		assert r.status_code == 400
		assert "Please pass in a valid object with bundle URL" in r.content
	
	def test_controller_bundle_with_url(self):
		r = requests.post("http://127.0.0.1:{}/bundle".format(self.controller_eventgen_webport), json={"url": "http://server.com/bundle.tgz"})
		assert r.status_code == 200
		assert "Bundle event dispatched to all with url http://server.com/bundle.tgz" in r.content

	def test_controller_bundle_with_url_and_target(self):
		r = requests.post("http://127.0.0.1:{}/bundle/{}".format(self.controller_eventgen_webport, TestEventgenOrchestration.server_id[:12]), json={"url": "http://server.com/bundle.tgz"})
		assert r.status_code == 200
		assert "Bundle event dispatched to {} with url http://server.com/bundle.tgz".format(TestEventgenOrchestration.server_id[:12]) in r.content

	def test_controller_get_volume(self):
		r = requests.get("http://127.0.0.1:{}/volume".format(self.controller_eventgen_webport))
		assert r.status_code == 200
		output = json.loads(r.content)
		assert output[TestEventgenOrchestration.server_id[:12]] == {}

	def test_controller_set_volume_invalid_request(self):
		r = requests.post("http://127.0.0.1:{}/volume".format(self.controller_eventgen_webport))
		assert r.status_code == 400
		assert "Please pass in a valid object with volume" in r.content

	def test_controller_set_volume_with_volume(self):
		r = requests.post("http://127.0.0.1:{}/volume".format(self.controller_eventgen_webport), json={"perDayVolume": 10})
		assert r.status_code == 200
		assert "set_volume event dispatched to all" in r.content

	def test_controller_set_volume_with_volume_and_target(self):
		r = requests.post("http://127.0.0.1:{}/volume/{}".format(self.controller_eventgen_webport, TestEventgenOrchestration.server_id[:12]), json={"perDayVolume": 10})
		assert r.status_code == 200
		assert "set_volume event dispatched to {}".format(TestEventgenOrchestration.server_id[:12]) in r.content

	### Server tests ###

	def test_server_root(self):
		r = requests.get("http://127.0.0.1:{}".format(self.server_eventgen_webport))
		assert r.status_code == 200
		assert "Host: " in r.content
		assert "Eventgen Status" in r.content
		assert "Eventgen Config file path" in r.content
		assert "Total volume:" in r.content
		assert "Worker Queue Status" in r.content
		assert "Sample Queue Status" in r.content
		assert "Output Queue Status" in r.content
	
	def test_server_index(self):
		r = requests.get("http://127.0.0.1:{}/index".format(self.server_eventgen_webport))
		assert r.status_code == 200
		assert "Host: " in r.content
		assert "Eventgen Status" in r.content
		assert "Eventgen Config file path" in r.content
		assert "Total volume:" in r.content
		assert "Worker Queue Status" in r.content
		assert "Sample Queue Status" in r.content
		assert "Output Queue Status" in r.content
	
	def test_server_status(self):
		r = requests.get("http://127.0.0.1:{}/status".format(self.server_eventgen_webport))
		assert r.status_code == 200
		output = json.loads(r.content)
		assert output
		assert output['EVENTGEN_STATUS'] == 0

	def test_server_get_and_set_conf(self):
		r = requests.get("http://127.0.0.1:{}/conf".format(self.server_eventgen_webport))
		assert r.status_code == 200
		assert json.loads(r.content) == {}
		config_json = {"windbag": {"outputMode": "stdout"}}
		r = requests.post("http://127.0.0.1:{}/conf".format(self.server_eventgen_webport), json=config_json)
		assert r.status_code == 200
		assert json.loads(r.content) == config_json

	def test_server_start(self):
		r = requests.post("http://127.0.0.1:{}/start".format(self.server_eventgen_webport))
		assert r.status_code == 200
		assert json.loads(r.content) == "Eventgen has successfully started."

	def test_server_restart(self):
		r = requests.post("http://127.0.0.1:{}/restart".format(self.server_eventgen_webport))
		assert r.status_code == 200
		assert json.loads(r.content) == "Eventgen restarted."

	def test_server_stop(self):
		r = requests.post("http://127.0.0.1:{}/stop".format(self.server_eventgen_webport))
		assert r.status_code == 200
		assert json.loads(r.content) == "Eventgen is stopped."

	def test_server_bundle(self):
		r = requests.post("http://127.0.0.1:{}/bundle".format(self.server_eventgen_webport))
		assert r.status_code == 400
		assert "Please pass in a valid object with bundle URL" in r.content

	def test_server_get_and_set_volume(self):
		# Must initialize a stanza with the perDayVolume setting before hitting the /volume endpoint
		r = requests.put("http://127.0.0.1:{}/conf".format(self.server_eventgen_webport), json={"windbag": {}})
		assert r.status_code == 200
		assert json.loads(r.content)
		r = requests.post("http://127.0.0.1:{}/volume".format(self.server_eventgen_webport), json={"perDayVolume": 10})
		assert r.status_code == 200
		assert json.loads(r.content)
		r = requests.get("http://127.0.0.1:{}/volume".format(self.server_eventgen_webport))
		assert r.status_code == 200
		output = json.loads(r.content)
		assert output == 10.0
		r = requests.post("http://127.0.0.1:{}/volume".format(self.server_eventgen_webport), json={"perDayVolume": 150})
		assert r.status_code == 200
		assert json.loads(r.content)
		r = requests.get("http://127.0.0.1:{}/volume".format(self.server_eventgen_webport))
		assert r.status_code == 200
		output = json.loads(r.content)
		assert output == 150.0
