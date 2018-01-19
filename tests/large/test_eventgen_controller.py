#!/usr/bin/env python
# encoding: utf-8

import os
import re
import time
import json
import pytest
import requests
import ConfigParser
from docker import APIClient
from random import choice
from string import ascii_lowercase
# Code to suppress insecure https warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")
RETRY_NUM = 3

def generate_random_string():
    return ''.join(choice(ascii_lowercase) for b in range(20))

@pytest.mark.large
class TestEventgenServer(object):

	@classmethod
	def setup_class(cls):
		cls.client = APIClient(base_url="unix://var/run/docker.sock")
		cls.image_tag = "eg:{}".format(generate_random_string())
		response = cls.client.build(path=REPO_DIR, dockerfile=os.path.join("dockerfiles", "Dockerfile"), tag=cls.image_tag, rm=True, nocache=True, pull=True, stream=False)
		for line in response:
			print line,
		host_config = cls.client.create_host_config(auto_remove=True, publish_all_ports=True)
		container = cls.client.create_container(image=cls.image_tag, 
												command="controller",
												host_config=host_config)
		cls.client.start(container["Id"])
		cls.container = cls.client.inspect_container(container["Id"])
		cls.eventgen_webport = cls.container["NetworkSettings"]["Ports"]["9500/tcp"][0]["HostPort"]
		cls.rabbitmq_webport = cls.container["NetworkSettings"]["Ports"]["15672/tcp"][0]["HostPort"]
		# Wait for the server to be available
		i = 0
		while i < 30:
			try:
				r = requests.get("http://127.0.0.1:{}".format(cls.eventgen_webport))
				r.raise_for_status()
				break
			except:
				pass
			finally:
				time.sleep(3)
				i += 1

	@classmethod
	def teardown_class(cls):
		cls.client.remove_container(cls.container, v=True, force=True)
		cls.client.remove_image(cls.image_tag, force=True, noprune=False)

	def test_rabbitmq(self):
		r = requests.get("http://127.0.0.1:{}".format(self.rabbitmq_webport))
		assert r.status_code == 200
		assert "RabbitMQ" in r.content

	def test_root(self):
		r = requests.get("http://127.0.0.1:{}".format(self.eventgen_webport))
		assert r.status_code == 200
		assert "Eventgen Controller" in r.content
		assert "Host: " in r.content
		assert "You are running Eventgen Controller" in r.content
	
	def test_index(self):
		r = requests.get("http://127.0.0.1:{}/index".format(self.eventgen_webport))
		assert r.status_code == 200
		assert "Eventgen Controller" in r.content
		assert "Host: " in r.content
		assert "You are running Eventgen Controller" in r.content
	
	def test_status(self):
		r = requests.get("http://127.0.0.1:{}/status".format(self.eventgen_webport))
		assert r.status_code == 200
		output = json.loads(r.content)
		assert output == {}
	
	def test_start(self):
		r = requests.post("http://127.0.0.1:{}/start".format(self.eventgen_webport))
		assert r.status_code == 200
		assert "Start event dispatched to all" in r.content
	
	def test_start_with_target(self):
		r = requests.post("http://127.0.0.1:{}/start".format(self.eventgen_webport), json={"target": "abcd"})
		assert r.status_code == 200
		assert "Start event dispatched to abcd" in r.content
	
	def test_stop(self):
		r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport))
		assert r.status_code == 200
		assert "Stop event dispatched to all" in r.content
	
	def test_stop_with_target(self):
		r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport), json={"target": "abcd"})
		assert r.status_code == 200
		assert "Stop event dispatched to abcd" in r.content
	
	def test_restart(self):
		r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport))
		assert r.status_code == 200
		assert "Stop event dispatched to all" in r.content
	
	def test_restart_with_target(self):
		r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport), json={"target": "abcd"})
		assert r.status_code == 200
		assert "Stop event dispatched to abcd" in r.content
	
	def test_bundle(self):
		r = requests.post("http://127.0.0.1:{}/bundle".format(self.eventgen_webport))
		assert r.status_code == 400
		assert "Please pass in a valid object with bundle URL" in r.content
	
	def test_bundle_with_url(self):
		r = requests.post("http://127.0.0.1:{}/bundle".format(self.eventgen_webport), json={"target": "abcd", "url": "http://server.com/bundle.tgz"})
		assert r.status_code == 200
		assert "Bundle event dispatched to abcd with url http://server.com/bundle.tgz" in r.content
