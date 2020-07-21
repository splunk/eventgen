from os import path as op

import pytest

from splunk_eventgen.lib.eventgenconfig import Config


@pytest.fixture
def eventgen_config():
    """Returns a function to create config instance based on config file"""

    def _make_eventgen_config_instance(configfile=None):
        if configfile is not None:
            configfile = op.join(
                op.dirname(op.dirname(__file__)),
                "sample_eventgen_conf",
                "unit",
                configfile,
            )
        return Config(configfile=configfile)

    return _make_eventgen_config_instance
