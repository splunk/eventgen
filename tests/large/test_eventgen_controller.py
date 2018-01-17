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
		#cls.image_tag = "eg:{}".format(generate_random_string())
		#response = cls.client.build(path=os.path.join(REPO_DIR, "dockerfiles"), tag=cls.image_tag, rm=True, nocache=True, pull=True, stream=False)
		#for line in response:
		#	print line,
		host_config = cls.client.create_host_config(auto_remove=True, publish_all_ports=True)
		container = cls.client.create_container(image="eventgen:latest", 
												command="controller",
												host_config=host_config)
		cls.client.start(container["Id"])
		cls.container = cls.client.inspect_container(container["Id"])
		import pprint
		#pprint.pprint(cls.container)
		cls.eventgen_webport = cls.container["NetworkSettings"]["Ports"]["9500/tcp"][0]["HostPort"]
		cls.rabbitmq_webport = cls.container["NetworkSettings"]["Ports"]["15672/tcp"][0]["HostPort"]
		time.sleep(30)

	@classmethod
	def teardown_class(cls):
		cls.client.remove_container(cls.container, v=True, force=True)

	def test_rabbitmq(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.get("http://127.0.0.1:{}".format(self.rabbitmq_webport))
				assert r.status_code == 200
				assert "RabbitMQ" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	def test_root(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.get("http://127.0.0.1:{}".format(self.eventgen_webport))
				assert r.status_code == 200
				assert "Eventgen Controller" in r.content
				assert "Host: " in r.content
				assert "You are running Eventgen Controller" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_index(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.get("http://127.0.0.1:{}/index".format(self.eventgen_webport))
				assert r.status_code == 200
				assert "Eventgen Controller" in r.content
				assert "Host: " in r.content
				assert "You are running Eventgen Controller" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_status(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.get("http://127.0.0.1:{}/status".format(self.eventgen_webport))
				assert r.status_code == 200
				output = json.loads(r.content)
				assert output == {}
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_start(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/start".format(self.eventgen_webport))
				assert r.status_code == 200
				assert "Start event dispatched to all" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_start_with_target(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/start".format(self.eventgen_webport), json={"target": "abcd"})
				assert r.status_code == 200
				assert "Start event dispatched to abcd" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_stop(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport))
				assert r.status_code == 200
				assert "Stop event dispatched to all" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_stop_with_target(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport), json={"target": "abcd"})
				assert r.status_code == 200
				assert "Stop event dispatched to abcd" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_restart(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport))
				assert r.status_code == 200
				assert "Stop event dispatched to all" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_restart_with_target(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/stop".format(self.eventgen_webport), json={"target": "abcd"})
				assert r.status_code == 200
				assert "Stop event dispatched to abcd" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_bundle(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/bundle".format(self.eventgen_webport))
				assert r.status_code == 400
				assert "Please pass in a valid object with bundle URL" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
	
	def test_bundle(self):
		for i in range(RETRY_NUM):
			try:
				r = requests.post("http://127.0.0.1:{}/bundle".format(self.eventgen_webport), json={"target": "abcd", "url": "http://server.com/bundle.tgz"})
				assert r.status_code == 200
				assert "Bundle event dispatched to abcd with url http://server.com/bundle.tgz" in r.content
				break
			except:
				if i < RETRY_NUM-1:
					print 'Retrying...'
					time.sleep(5)
				else:
					raise
