import os
import sys

from mock import patch
from splunk_eventgen.__main__ import parse_args
from splunk_eventgen.eventgen_core import EventGenerator

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = 'test_jinja_generator_file_output.result'


class TestJinjaGenerator(object):
    def test_jinja_generator_to_file(self):
        configfile = "tests/sample_eventgen_conf/jinja/eventgen.conf.jinja_basic"
        testargs = ["eventgen", "generate", configfile]
        file_output_path = os.path.abspath(os.path.join(FILE_DIR, '..', '..', '..', OUTPUT_FILE))
        # remove the result file if it exists
        if os.path.exists(file_output_path):
            os.remove(file_output_path)

        with patch.object(sys, 'argv', testargs):
            pargs = parse_args()
            assert pargs.subcommand == 'generate'
            assert pargs.configfile == configfile
            eventgen = EventGenerator(args=pargs)
            eventgen.start()

        assert os.path.isfile(file_output_path)

        with open(file_output_path, 'r') as outfile:
            line_count = 1
            for output_line in outfile:
                if not output_line or line_count == 11:
                    break
                assert "I like little windbags" in output_line
                assert "Im at: {0} out of: 10".format(line_count) in output_line
                line_count += 1
