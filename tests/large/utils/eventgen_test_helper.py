import os
import subprocess
import re
from threading import Timer

import configparser

# $EVENTGEN_HOME/tests/large
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# change working directory so that 'splunk_eventgen' call in the project root directory
os.chdir(os.path.dirname(os.path.dirname(base_dir)))


class EventgenTestHelper(object):
    def __init__(self, conf, timeout=None):
        self.conf = os.path.join(base_dir, 'conf', conf)
        self.config, self.section = self._read_conf(self.conf)
        self.output_mode = self._get_output_mode()
        self.file_name = self._get_file_name()
        self.breaker = self._get_breaker()
        self.process = subprocess.Popen(['splunk_eventgen', 'generate', self.conf], stdout=subprocess.PIPE)
        if timeout:
            timer = Timer(timeout, self.kill)
            timer.start()

    def kill(self):
        self.process.kill()

    def is_alive(self):
        if self.process.poll() is None:
            return True
        else:
            return False

    def get_events(self):
        """Get events either from stdout or from file"""
        self.process.wait()
        if self.output_mode == 'stdout':
            output = self.process.communicate()[0]
        elif self.output_mode == 'file':
            with open(os.path.join(base_dir, 'results', self.file_name), 'r') as f:
                output = f.read()

        if self.breaker[0] == '^':
            self.breaker = self.breaker[1:]
        if self.breaker[-1] == '$':
            self.breaker = self.breaker[:-1]
        results = re.split(self.breaker, output)
        return [x for x in results if x != ""]

    def tear_down(self):
        """Kill sub-processes and remove results file"""
        if self.is_alive():
            self.process.kill()
        if self.file_name:
            os.remove(os.path.join(base_dir, 'results', self.file_name))

    def _get_output_mode(self):
        return self.config.get(self.section, 'outputMode', fallback=None)

    def _get_file_name(self):
        file_name = None
        file_name_value = self.config.get(self.section, 'fileName', fallback=None)
        if file_name_value is not None:
            file_name = file_name_value.split(os.sep)[-1]
        return file_name

    def _get_breaker(self):
        return self.config.get(self.section, 'breaker', fallback='\n')

    @staticmethod
    def _read_conf(conf):
        config = configparser.ConfigParser()
        config.read(conf)
        if len(config.sections()) != 1 or config.sections()[0] == 'default' or config.sections()[0] == 'global':
            raise Exception("Invalid test eventgen conf")
        return config, config.sections()[0]
