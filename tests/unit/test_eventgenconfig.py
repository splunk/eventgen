import os
from ConfigParser import ConfigParser


def test_makeSplunkEmbedded(eventgen_config):
    session_key = 'ea_IO86v01Xipz8BuB_Ako9rMoc5_HNn6UQrBhVQY5zj68LN2J2xVrLzYD^XEgVTWyKrXva6r8yZ2gtEuv9nnZ'
    eventgen_config.makeSplunkEmbedded(session_key)
    assert eventgen_config.splunkEmbedded
    # reset splunkEmbedded since all instances share the attribute
    eventgen_config.splunkEmbedded = False


def test_buildConfDict(eventgen_config):
    eventgen_config._buildConfDict()
    configparser = ConfigParser()
    splunk_eventgen_folder = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'splunk_eventgen')
    configparser.read(os.path.join(splunk_eventgen_folder, 'default', 'eventgen.conf'))
    configparser.set('global', 'eai:acl', {'app': 'splunk_eventgen'})

    for key, value in eventgen_config._confDict['global'].items():
        assert value == configparser.get('global', key)


def test_validateSetting(eventgen_config):
    # 1. tokens./hosts.
    # 2. _validSettings: int/float/bool/json
    # 3. _complexSettings
    valid_token_types = ['token', 'replacementType', 'replacement']
    valid_host_token = ['token', 'replacement']
    valid_replacement_type = ['static', 'timestamp', 'replaytimestamp', 'random', 'rated', 'file', 'mvfile', 'seqfile',
                              'integerid']
    pass


def test_validateTimezone():
    pass


def test_validateSeed():
    pass


def test_parse():
    pass

