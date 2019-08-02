#!/usr/bin/env python
# encoding: utf-8

import json
import os
import time
from random import choice
from string import ascii_lowercase

import pytest
import requests
from docker import APIClient
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
    while end - start < timeout:
        try:
            r = requests.get(url)
            r.raise_for_status()
            break
        except:
            time.sleep(10)
            end = time.time()


@pytest.mark.large
class TestEventgenOrchestration(object):
    """
    This test class is used to test the Docker image published as part of this repo.
    Specifically, this is testing:
        * Eventgen "controller" API and responses
        * Eventgen "server" API and responses
        * Eventgen controller/server orchestration
    """

    @classmethod
    def setup_class(cls):
        # Build the image from scratch
        cls.client = APIClient(base_url="unix://var/run/docker.sock")
        response = cls.client.build(path=REPO_DIR, dockerfile=os.path.join("dockerfiles", "Dockerfile"), tag=IMAGE_NAME, rm=True, nocache=True, pull=True, stream=False)
        for line in response:
            print(line, end=' ')
        # Create a network for both the controller and server to run in
        cls.client.create_network(NETWORK_NAME, driver="bridge", attachable=True)
        networking_config = cls.client.create_networking_config({NETWORK_NAME: cls.client.create_endpoint_config()})
        # Start the controller
        print('creating controller')
        host_config = cls.client.create_host_config(auto_remove=True, publish_all_ports=True)
        container = cls.client.create_container(image=IMAGE_NAME, command="controller", host_config=host_config,
                                                networking_config=networking_config)
        cls.client.start(container["Id"])
        TestEventgenOrchestration.controller_id = container["Id"]
        print(container["Id"])
        cls.controller_container = cls.client.inspect_container(container["Id"])
        cls.controller_eventgen_webport = cls.controller_container["NetworkSettings"]["Ports"]["9500/tcp"][0][
            "HostPort"]
        # Start the server
        print('creating server')
        redis_host = container["Id"][:12]
        container = cls.client.create_container(
            image=IMAGE_NAME, command="server", environment=["REDIS_HOST={}".format(redis_host)], 
            host_config=host_config,
            networking_config=networking_config)
        cls.client.start(container["Id"])
        TestEventgenOrchestration.server_id = container["Id"]
        print(container["Id"])
        cls.server_container = cls.client.inspect_container(container["Id"])
        cls.server_eventgen_webport = cls.server_container["NetworkSettings"]["Ports"]["9500/tcp"][0]["HostPort"]

        # Wait for the controller to be available
        print("Waiting for Eventgen Controller to become available.")
        wait_for_response("http://127.0.0.1:{}".format(cls.controller_eventgen_webport))
        print("Eventgen Controller has become available.")

        # Wait for the server to be available
        print("Waiting for Eventgen Server to become available.")
        wait_for_response("http://127.0.0.1:{}".format(cls.server_eventgen_webport))
        print("Eventgen Server has become available.")
        time.sleep(30)

        cls.test_json = {
            "windbag": {
                "generator": "windbag",
                "earliest": "-3s",
                "latest": "now",
                "interval": "5",
                "count": "5",
                "outputMode": "stdout",
                "end": "15",
                "threading": "process"
            }
        }

    @classmethod
    def teardown_class(cls):
        cls.client.remove_container(cls.server_container, v=True, force=True)
        cls.client.remove_container(cls.controller_container, v=True, force=True)
        cls.client.remove_image(IMAGE_NAME, force=True, noprune=False)
        cls.client.remove_network(NETWORK_NAME)

    # Controller tests #
    def test_controller_root(self):
        r = requests.get("http://127.0.0.1:{}/".format(self.controller_eventgen_webport))
        assert r.status_code == 200
        assert "running_eventgen_controller" in r.content

    def test_controller_index(self):
        r = requests.get("http://127.0.0.1:{}/index".format(self.controller_eventgen_webport))
        assert r.status_code == 200
        assert "Eventgen Controller" in r.content
        assert "Host: " in r.content
        assert "You are running Eventgen Controller" in r.content

    def test_controller_status(self):
        max_retry = 5
        current_retry = 1
        output = {}
        while not output and current_retry <= max_retry:
            response = requests.get("http://127.0.0.1:{}/status".format(self.controller_eventgen_webport), timeout=10)
            if response.status_code == 200:
                output = json.loads(response.content)
            current_retry += 1
            time.sleep(10)
        assert output
    
    def test_controller_conf(self):
        r = requests.post("http://127.0.0.1:{}/conf".format(self.controller_eventgen_webport), json=self.test_json)
        assert r.status_code == 200
        assert "windbag" in r.content

    def test_controller_start(self):
        r = requests.post("http://127.0.0.1:{}/start".format(self.controller_eventgen_webport))
        assert r.status_code == 200
        assert "Eventgen has successfully started" in r.content

    def test_controller_start_with_target(self):
        r = requests.post("http://127.0.0.1:{}/start/{}".format(self.controller_eventgen_webport,
                                                                TestEventgenOrchestration.server_id[:12]))
        assert r.status_code == 200
        assert "Eventgen already started" in r.content

    def test_controller_restart(self):
        r = requests.post("http://127.0.0.1:{}/restart".format(self.controller_eventgen_webport))
        assert r.status_code == 200
        assert "Eventgen is restarting" in r.content

    def test_controller_restart_with_target(self):
        r = requests.post("http://127.0.0.1:{}/restart/{}".format(self.controller_eventgen_webport,
                                                               TestEventgenOrchestration.server_id[:12]))
        assert r.status_code == 200
        assert "Eventgen is restarting" in r.content

    def test_controller_bundle_invalid_request(self):
        r = requests.post("http://127.0.0.1:{}/bundle".format(self.controller_eventgen_webport))
        assert r.status_code == 500
        assert "Internal Error Occurred" in r.content

    def test_controller_bundle_with_url(self):
        r = requests.post("http://127.0.0.1:{}/bundle".format(self.controller_eventgen_webport), json={
            "url": "http://server.com/bundle.tgz"})
        assert r.status_code == 200

    def test_controller_bundle_with_url_and_target(self):
        r = requests.post(
            "http://127.0.0.1:{}/bundle/{}".format(self.controller_eventgen_webport,
                                                   TestEventgenOrchestration.server_id[:12]), json={
                                                       "url": "http://server.com/bundle.tgz"})
        assert r.status_code == 200

    def test_controller_get_volume(self):
        max_retry = 5
        current_retry = 1
        output = {}
        while not output and current_retry <= max_retry:
            response = requests.get("http://127.0.0.1:{}/volume".format(self.controller_eventgen_webport), timeout=10)
            if response.status_code == 200:
                output = json.loads(response.content)
            current_retry += 1
            time.sleep(10)
        assert output[TestEventgenOrchestration.server_id[:12]]["perDayVolume"] == 0.0

    def test_controller_set_volume_invalid_request(self):
        r = requests.post("http://127.0.0.1:{}/volume".format(self.controller_eventgen_webport))
        assert r.status_code == 500
        assert "Internal Error Occurred" in r.content

    def test_controller_set_volume_with_volume(self):
        r = requests.post("http://127.0.0.1:{}/volume".format(self.controller_eventgen_webport), json={
            "perDayVolume": 10})
        assert r.status_code == 200
        output = json.loads(r.content)
        assert output[TestEventgenOrchestration.server_id[:12]]["perDayVolume"] == 10

    def test_controller_set_volume_with_volume_and_target(self):
        r = requests.post(
            "http://127.0.0.1:{}/volume/{}".format(self.controller_eventgen_webport,
                                                   TestEventgenOrchestration.server_id[:12]), json={"perDayVolume": 20})
        assert r.status_code == 200
        output = json.loads(r.content)
        assert output[TestEventgenOrchestration.server_id[:12]]["perDayVolume"] == 20
    
    def test_controller_stop(self):
        r = requests.post("http://127.0.0.1:{}/stop".format(self.controller_eventgen_webport))
        assert r.status_code == 200
        assert r.status_code == 200
        assert "Eventgen is stopping" in r.content

    def test_controller_stop_with_target(self):
        r = requests.post("http://127.0.0.1:{}/stop/{}".format(self.controller_eventgen_webport,
                                                               TestEventgenOrchestration.server_id[:12]))
        assert r.status_code == 200
        assert "Eventgen is stopping" in r.content

    # Server tests #

    def test_server_reset(self):
        r = requests.post("http://127.0.0.1:{}/reset".format(self.server_eventgen_webport))
        assert r.status_code == 200

    def test_server_root(self):
        r = requests.get("http://127.0.0.1:{}".format(self.server_eventgen_webport))
        assert r.status_code == 200
        assert "running_eventgen_server" in r.content

    def test_server_index(self):
        r = requests.get("http://127.0.0.1:{}/index".format(self.server_eventgen_webport))
        assert r.status_code == 200
        assert "Host: " in r.content
        assert "Eventgen Status" in r.content
        assert "Eventgen Config file exists" in r.content
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
        assert output['TOTAL_VOLUME'] == 20

    def test_server_get_and_set_conf(self):
        r = requests.get("http://127.0.0.1:{}/conf".format(self.server_eventgen_webport))
        assert r.status_code == 200
        assert json.loads(r.content)
        config_json = {
            "windbag": {
                "end": "10"
            }
        }
        r = requests.post("http://127.0.0.1:{}/conf".format(self.server_eventgen_webport), json=config_json)
        assert r.status_code == 200
        assert json.loads(r.content) == config_json

    def test_server_start(self):
        r = requests.post("http://127.0.0.1:{}/start".format(self.server_eventgen_webport), timeout=5)
        assert r.status_code == 200
        assert "Eventgen has successfully started" in r.content

    def test_server_restart(self):
        r = requests.post("http://127.0.0.1:{}/restart".format(self.server_eventgen_webport))
        assert r.status_code == 200
        assert "Eventgen has successfully restarted" in r.content

    def test_server_stop(self):
        r = requests.post("http://127.0.0.1:{}/stop".format(self.server_eventgen_webport))
        assert r.status_code == 200
        assert "Eventgen is stopped" in r.content

    def test_server_bundle(self):
        r = requests.post("http://127.0.0.1:{}/bundle".format(self.server_eventgen_webport))
        assert r.status_code == 500
        assert "Internal Error Occurred" in r.content

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
        assert output["perDayVolume"] == 10.0
        r = requests.post("http://127.0.0.1:{}/volume".format(self.server_eventgen_webport), json={"perDayVolume": 150})
        assert r.status_code == 200
        assert json.loads(r.content)
        r = requests.get("http://127.0.0.1:{}/volume".format(self.server_eventgen_webport))
        assert r.status_code == 200
        output = json.loads(r.content)
        assert output["perDayVolume"] == 150.0
