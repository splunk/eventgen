#!/usr/bin/env python3
# encoding: utf-8

import os
import sys

from mock import MagicMock, patch

from splunk_eventgen.__main__ import parse_args
from splunk_eventgen.eventgen_core import EventGenerator
from splunk_eventgen.lib.plugins.output.udpout import UdpOutputPlugin

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


class TestUdpOutputPlugin(object):
    def test_output_data_to_udp_port(self):
        configfile = "tests/sample_eventgen_conf/medium_test/eventgen.conf.udpoutput"
        testargs = ["eventgen", "generate", configfile]
        with patch.object(sys, 'argv', testargs):
            pargs = parse_args()
            assert pargs.subcommand == 'generate'
            assert pargs.configfile == configfile
            eventgen = EventGenerator(args=pargs)

        with patch('socket.socket') as mock_requests:
            sample = MagicMock()
            udpoutput = UdpOutputPlugin(sample)
            mock_requests.sendto = MagicMock()
            mock_requests.connect = MagicMock()
            post_resp = MagicMock()
            post_resp.raise_for_status = MagicMock()
            mock_requests.post.return_value = MagicMock()

            eventgen.start()
            assert not udpoutput.s.connect.called
            assert udpoutput.s.sendto.call_count == 5
