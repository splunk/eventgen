#!/usr/bin/env python3
# encoding: utf-8

import os
import sys
import requests

from mock import MagicMock, patch

from splunk_eventgen.__main__ import parse_args
from splunk_eventgen.eventgen_core import EventGenerator
from splunk_eventgen.lib.plugins.output.scsout import SCSOutputPlugin

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


class TestSCSOutputPlugin(object):
    def test_output_data_to_scs(self):
        configfile = "tests/sample_eventgen_conf/medium_test/eventgen.conf.scsoutput"
        testargs = ["eventgen", "generate", configfile]
        with patch.object(sys, 'argv', testargs):
            pargs = parse_args()
            assert pargs.subcommand == 'generate'
            assert pargs.configfile == configfile
            eventgen = EventGenerator(args=pargs)
        with patch('requests_futures.sessions.FuturesSession.post') as mock_requests:
            sample = MagicMock()
            scsoutput = SCSOutputPlugin(sample)

            eventgen.start()
            scsoutput.session.post.assert_called()
            assert scsoutput.session.post.call_count == 1
