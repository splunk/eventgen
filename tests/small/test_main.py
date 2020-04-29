#!/usr/bin/env python3

import os
import sys

from mock import MagicMock

from splunk_eventgen.__main__ import gather_env_vars

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(FILE_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(FILE_DIR, "..", "..", "..", "splunk_eventgen"))


def test_gather_env_vars():
    args = MagicMock()
    args.redis_host = "127.0.0.1"
    args.redis_port = "6379"
    args.web_server_port = "9500"
    obj = gather_env_vars(args)
    assert obj == {
        "REDIS_HOST": "127.0.0.1",
        "REDIS_PORT": "6379",
        "WEB_SERVER_PORT": "9500",
    }
