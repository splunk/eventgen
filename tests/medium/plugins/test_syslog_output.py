#!/usr/bin/env python
# encoding: utf-8

import os
import sys

from mock import MagicMock, patch

from splunk_eventgen.__main__ import parse_args
from splunk_eventgen.eventgen_core import EventGenerator
from splunk_eventgen.lib.plugins.output.syslogout import SyslogOutOutputPlugin

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


class TestSyslogOutputPlugin(object):
    def test_output_data_to_syslog(self):
        configfile = "tests/sample_eventgen_conf/medium_test/eventgen.conf.syslogoutput"
        testargs = ["eventgen", "generate", configfile]
        with patch.object(sys, 'argv', testargs):
            with patch('logging.getLogger'):
                pargs = parse_args()
                assert pargs.subcommand == 'generate'
                assert pargs.configfile == configfile
                eventgen = EventGenerator(args=pargs)

                sample = MagicMock()
                sample.name = 'test'
                sample.syslogDestinationHost = '127.0.0.1'
                sample.syslogDestinationPort = 9999
                syslogoutput = SyslogOutOutputPlugin(sample)

                eventgen.start()
                for i in xrange(1, 6):
                    appearance = False
                    for logger_call in syslogoutput._l.info.call_args_list:
                        if "WINDBAG Event {} of 5".format(i) in str(logger_call):
                            appearance = True
                    if not appearance:
                        assert False
