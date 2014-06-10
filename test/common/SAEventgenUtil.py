import os
import logging
from helmut_lib.InstallUtil import InstallUtil

class SAEventgenUtil:

    def __init__(self, splunk_home, logger):
        """
        Constructor of the SAEventgen object.
        """
        self.logger = logger
        self.splunk_home = splunk_home

    def get_and_install_sa_eventgen(self):

        self.soln_root = os.environ["SOLN_ROOT"]
        self.logger.info("SOLN_ROOT:" + self.soln_root)

        install_util = InstallUtil("SA-Eventgen2", self.splunk_home)
        package = install_util.get_solution()
        install_util.install_solution(package)
        return package
