#!/usr/bin/env python
# encoding: utf-8

import os
import sys
from mock import MagicMock, patch
from splunk_eventgen.__main__ import parse_args
from splunk_eventgen.eventgen_core import EventGenerator

FILE_DIR = os.path.dirname(os.path.abspath(__file__))

class TestFileOutputPlugin(object):

    def test_output_data_to_file(self):
        configfile = "tests/sample_eventgen_conf/medium_test/eventgen.conf.fileoutput"
        testargs = ["eventgen", "generate", configfile]
        with patch.object(sys, 'argv', testargs):
            pargs = parse_args()
            assert pargs.subcommand == 'generate'
            assert pargs.configfile == configfile
            eventgen = EventGenerator(args=pargs)
            eventgen.start()

        file_output_path = os.path.abspath(os.path.join(FILE_DIR, '..', '..', '..', 'test_file_output.result'))
        assert os.path.isfile(file_output_path)
        with open(file_output_path, 'r') as outfile:
            line_count = 1
            assert len(outfile) > 0
            for output_line in outfile:
                if not output_line or line_count == 6:
                    break
                assert "WINDBAG Event {} of 5".format(line_count) in output_line
                line_count += 1
