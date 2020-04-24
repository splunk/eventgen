import os
import subprocess
import re
from threading import Timer

import configparser

# $EVENTGEN_HOME/tests/large
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_dir = os.path.dirname(os.path.dirname(base_dir))
result_dir = os.path.join(base_dir, "results")
# change working directory so that 'splunk_eventgen' call in the project root directory
os.chdir(os.path.dirname(os.path.dirname(base_dir)))


class EventgenTestHelper(object):
    @classmethod
    def make_result_dir(cls):
        if not os.path.isdir(result_dir):
            os.makedirs(result_dir)

    def __init__(self, conf, timeout=None, mode=None, env=None):
        self.conf = os.path.join(base_dir, "conf", conf)
        self.config, self.section = self._read_conf(self.conf)
        self.output_mode = self._get_output_mode()
        self.file_name = self._get_file_name()
        self.breaker = self._get_breaker()
        cmd = ["splunk_eventgen", "generate", self.conf]
        if mode == "process":
            cmd.append("--multiprocess")
        env_var = os.environ.copy()
        if env is not None:
            for k, v in env.items():
                env_var[k] = v
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env_var)
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
        if self.output_mode == "stdout":
            output, stderr = self.process.communicate()
            if stderr:
                assert False
        elif self.output_mode == "file":
            with open(os.path.join(result_dir, self.file_name), "r") as f:
                output = f.read()
        elif self.output_mode == "spool":
            spool_dir_config = self.config.get(self.section, "spoolDir", fallback=None)
            spool_file_config = self.config.get(
                self.section, "spoolFile", fallback=None
            )
            if os.path.isabs(spool_dir_config):
                self.file_name = os.path.join(spool_dir_config, spool_file_config)
            else:
                self.file_name = os.path.join(
                    project_dir, spool_dir_config, spool_file_config
                )
            with open(self.file_name, "r") as f:
                output = f.read()
        else:
            output = ""

        if self.breaker[0] == "^":
            self.breaker = self.breaker[1:]
        if self.breaker[-1] == "$":
            self.breaker = self.breaker[:-1]

        if isinstance(output, bytes):
            output = output.decode("UTF-8")

        results = re.split(self.breaker, output)
        return [x for x in results if x != ""]

    def tear_down(self):
        """Kill sub-processes and remove results file"""
        if self.is_alive():
            self.process.kill()
        if self.file_name:
            result_file = os.path.join(result_dir, self.file_name)
            if os.path.isfile(result_file):
                os.remove(result_file)

    def _get_output_mode(self):
        return self.config.get(self.section, "outputMode", fallback=None)

    def _get_file_name(self):
        file_name = None
        file_name_value = self.config.get(self.section, "fileName", fallback=None)
        if file_name_value is not None:
            file_name = file_name_value.split(os.sep)[-1]
        return file_name

    def _get_breaker(self):
        return self.config.get(self.section, "breaker", fallback="\n")

    @staticmethod
    def _read_conf(conf):
        config = configparser.ConfigParser()
        config.read(conf)
        section = None
        for s in config.sections():
            if s == "default" or s == "global":
                continue
            else:
                section = s
                break
        return config, section
