"""
Meta
====
    $Id: //splunk/solutions/SA-ThreatIntelligence/mainline/test/build/build_SA-ThreatIntelligence.py#12 $
    $DateTime: 2011/03/20 23:04:29 $
    $Author: dzakharov $
    $Change: 96913 $
"""

import logging
import os
from BuildUtil import BuildUtil


class TestBuildSAEventgen:

    # in this method we just build SA-Eventgen
    def test_build(self):
        self.logger = logging.getLogger('BuildSA-Eventgen')
        """codeline = os.environ["CODELINE"]"""
        buildutil = BuildUtil('SA-Eventgen', 'mainline2', 'spl', self.logger)
        buildutil.build_solution()

