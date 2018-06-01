#!/usr/bin/env python2

import pytest
import os
import sys
from mock import MagicMock, call, patch, mock_open

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(FILE_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(FILE_DIR, "..", "..", "..", "splunk_eventgen"))
from splunk_eventgen.__main__ import parse_cli_vars, parse_env_vars


@pytest.mark.parametrize(('config'),
        [   
            # Empty config
            ({}),
            # Some elements already defined - function should override
            ({"AMQP_HOST": "guest", "AMQP_PASS": "guest"})
        ])
def test_parse_cli_vars(config):
    args = MagicMock()
    args.amqp_uri = "pyamqp://user:pass@host:port"
    args.amqp_host = "hostname"
    args.amqp_port = 8001
    args.amqp_webport = 8000
    args.amqp_user = "hello"
    args.amqp_pass = "world"
    args.web_server_address = "0.0.0.:1111"
    obj = parse_cli_vars(config, args)
    assert obj == { "AMQP_URI": "pyamqp://user:pass@host:port",
                    "AMQP_HOST": "hostname",
                    "AMQP_PORT": 8001,
                    "AMQP_WEBPORT": 8000 ,
                    "AMQP_USER": "hello",
                    "AMQP_PASS": "world",
                    "WEB_SERVER_ADDRESS": "0.0.0.:1111" }

@pytest.mark.parametrize(('env_vars'),
        [   
            # No environment vars defined
            ({}),
            # All environemnt vars defined
            ({"EVENTGEN_AMQP_URI": "test", "EVENTGEN_AMQP_HOST": "host", "EVENTGEN_AMQP_PORT": 8000, "EVENTGEN_AMQP_WEBPORT": 8001, "EVENTGEN_AMQP_USER": "hello", "EVENTGEN_AMQP_PASS": "world", "EVENTGEN_WEB_SERVER_ADDR": "0.0.0.0:1111"})
        ])
def test_parse_env_vars(env_vars):
    with patch("splunk_eventgen.__main__.os") as mock_os:
        mock_os.environ = env_vars
        obj = parse_env_vars()
        assert obj.keys() == ['AMQP_WEBPORT', 'AMQP_USER', 'AMQP_PASS', 'AMQP_PORT', 'AMQP_URI', 'WEB_SERVER_ADDRESS', 'AMQP_HOST']
        if env_vars:
            # If enviroment vars are defined, let's make sure they are set instead of default values
            assert obj["WEB_SERVER_ADDRESS"] == "0.0.0.0:1111"
            assert obj["AMQP_HOST"] == "host"
            assert obj["AMQP_PORT"] == 8000

def test_parse_env_vars_and_parse_cli_vars():
    '''
    This test checks the layering effect of both parsing CLI and env vars.
    Arguments passed via CLI should take precedence over those defined in environment.
    '''
    with patch("splunk_eventgen.__main__.os") as mock_os:
        mock_os.environ = {}
        obj = parse_env_vars()
        assert obj["AMQP_WEBPORT"] == 15672
        assert obj["AMQP_USER"] == "guest"
        assert obj["AMQP_PORT"] == 5672
        assert obj["AMQP_PASS"] == "guest"
        assert obj["AMQP_USER"] == "guest"
        assert obj["AMQP_URI"] == None
        assert obj["WEB_SERVER_ADDRESS"] == "0.0.0.0:9500"
        args = MagicMock()
        args.amqp_uri = "pyamqp://user:pass@host:port"
        args.amqp_host = "hostname"
        args.amqp_port = 8001
        args.amqp_webport = 8000
        args.web_server_address = "0.0.0.:1111"
        # Purposely defining None vars here for these CLI args - in this case, environment vars will be used
        args.amqp_user = None
        args.amqp_pass = None
        newobj = parse_cli_vars(obj, args)
        assert obj == { "AMQP_URI": "pyamqp://user:pass@host:port",
                        "AMQP_HOST": "hostname",
                        "AMQP_PORT": 8001,
                        "AMQP_WEBPORT": 8000 ,
                        "AMQP_USER": "guest",
                        "AMQP_PASS": "guest",
                        "WEB_SERVER_ADDRESS": "0.0.0.:1111" }
