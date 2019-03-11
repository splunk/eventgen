#!/usr/bin/env python
# encoding: utf-8

import os
import sys
from mock import MagicMock, patch
from splunk_eventgen.__main__ import parse_args
from splunk_eventgen.eventgen_core import EventGenerator
from splunk_eventgen.lib.plugins.output.tcpout import TcpOutputPlugin

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


class TestTcpOutputPlugin(object):

    def test_output_data_to_tcp_port(self):
        configfile = "tests/sample_eventgen_conf/medium_test/eventgen.conf.tcpoutput"
        testargs = ["eventgen", "generate", configfile]
        with patch.object(sys, 'argv', testargs):
            pargs = parse_args()
            assert pargs.subcommand == 'generate'
            assert pargs.configfile == configfile
            eventgen = EventGenerator(args=pargs)

        with patch('socket.socket') as mock_requests:
            sample = MagicMock()
            tcpoutput = TcpOutputPlugin(sample)
            mock_requests.send = MagicMock()
            mock_requests.connect = MagicMock()
            post_resp = MagicMock()
            post_resp.raise_for_status = MagicMock()
            mock_requests.post.return_value = MagicMock()
            mock_requests.connect.return_value = True

            eventgen.start()
            tcpoutput.s.connect.assert_called_with(('127.0.0.1', 9999))
            assert tcpoutput.s.send.call_count == 5

