#!/usr/bin/env python2

import pytest
import os
import sys
from mock import MagicMock, call, patch, mock_open

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(FILE_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(FILE_DIR, "..", "..", "..", "splunk_eventgen"))
from splunk_eventgen.eventgenapi_client import EventgenApiClient


def test_init():
	client = EventgenApiClient("http://www.google.com")
	assert client.url == "http://www.google.com"
	assert client.session

@pytest.mark.parametrize(('status_code', 'text'),
        [
            (200, '{"key": "value"}'),
            (404, 'error')
        ])
def test_start(status_code, text):
	client = EventgenApiClient("http://www.google.com")
	mock_resp = MagicMock()
	mock_resp.status_code = status_code
	mock_resp.text = text
	mock_session = MagicMock()
	mock_session.put = MagicMock()
	mock_session.put.return_value = mock_resp
	client.session = mock_session
	try:
		result = client.start()
		mock_session.put.assert_called_with("http://www.google.com/ctrl", params={"command": "start"})
		assert result == {"key": "value"}
	except Exception as err:
		assert err.args == ("HTTP error", 404)
