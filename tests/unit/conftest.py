import pytest

from splunk_eventgen.lib.eventgenconfig import Config


@pytest.fixture(scope='module', params=['configfile'])
def eventgen_config(configfile=None):
    config = Config(configfile=configfile)
    yield config
    del config
