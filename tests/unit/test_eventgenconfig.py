import json
import os
from configparser import ConfigParser

import pytest

from splunk_eventgen.lib.eventgensamples import Sample


def test_makeSplunkEmbedded(eventgen_config):
    """Test makeSplunkEmbedded works"""
    config_instance = eventgen_config()
    session_key = 'ea_IO86v01Xipz8BuB_Ako9rMoc5_HNn6UQrBhVQY5zj68LN2J2xVrLzYD^XEgVTWyKrXva6r8yZ2gtEuv9nnZ'
    config_instance.makeSplunkEmbedded(session_key)
    assert config_instance.splunkEmbedded
    # reset splunkEmbedded since all instances share the attribute
    config_instance.splunkEmbedded = False


def test_buildConfDict(eventgen_config):
    """Test buildConfDict returns the same as reading directly from file"""
    config_instance = eventgen_config()
    config_instance._buildConfDict()
    configparser = ConfigParser()
    splunk_eventgen_folder = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'splunk_eventgen')
    configparser.read(os.path.join(splunk_eventgen_folder, 'default', 'eventgen.conf'))
    configparser.set('global', 'eai:acl', {'app': 'splunk_eventgen'})

    for key, value in config_instance._confDict['global'].items():
        assert value == configparser.get('global', key)


def test_validate_setting_count(eventgen_config):
    """Test count config is int with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'count', '0')) == int
    assert config_instance._validateSetting('sample', 'count', '0') == 0


def test_validate_setting_delay(eventgen_config):
    """Test delay config is int with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'delay', '10')) == int
    assert config_instance._validateSetting('sample', 'delay', '10') == 10


def test_validate_setting_interval(eventgen_config):
    """Test interval config is int with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'interval', '3')) == int
    assert config_instance._validateSetting('sample', 'interval', '3') == 3


def test_validate_setting_perdayvolume(eventgen_config):
    """Test perdayvolume config is float with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'perDayVolume', '1')) == float
    assert config_instance._validateSetting('sample', 'perDayVolume', '1') == 1.0


def test_validate_setting_randomizeCount(eventgen_config):
    """Test randomizeCount config is float with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'randomizeCount', '0.2')) == float
    assert config_instance._validateSetting('sample', 'randomizeCount', '0.2') == 0.2


def test_validate_setting_timeMultiple(eventgen_config):
    """Test timeMultiple config is float with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'timeMultiple', '2')) == float
    assert config_instance._validateSetting('sample', 'timeMultiple', '2') == 2.0


def test_validate_setting_disabled(eventgen_config):
    """Test disabled config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'disabled', 'false')) == bool
    assert config_instance._validateSetting('sample', 'disabled', 'false') is False


def test_validate_setting_profiler(eventgen_config):
    """Test profiler config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'profiler', 'false')) == bool
    assert config_instance._validateSetting('sample', 'profiler', 'false') is False


def test_validate_setting_useOutputQueue(eventgen_config):
    """Test useOutputQueue config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'useOutputQueue', 'false')) == bool
    assert config_instance._validateSetting('sample', 'useOutputQueue', 'false') is False


def test_validate_setting_bundlelines(eventgen_config):
    """Test bundlelines config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'bundlelines', 'false')) == bool
    assert config_instance._validateSetting('sample', 'bundlelines', 'false') is False


def test_validate_setting_httpeventWaitResponse(eventgen_config):
    """Test httpeventWaitResponse config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'httpeventWaitResponse', 'false')) == bool
    assert config_instance._validateSetting('sample', 'httpeventWaitResponse', 'false') is False


def test_validate_setting_sequentialTimestamp(eventgen_config):
    """Test sequentialTimestamp config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'sequentialTimestamp', 'false')) == bool
    assert config_instance._validateSetting('sample', 'sequentialTimestamp', 'false') is False


def test_validate_setting_autotimestamp(eventgen_config):
    """Test autotimestamp config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'autotimestamp', 'false')) == bool
    assert config_instance._validateSetting('sample', 'autotimestamp', 'false') is False


def test_validate_setting_randomizeEvents(eventgen_config):
    """Test randomizeEvents config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'randomizeEvents', 'false')) == bool
    assert config_instance._validateSetting('sample', 'randomizeEvents', 'false') is False


def test_validate_setting_outputCounter(eventgen_config):
    """Test outputCounter config is bool with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert type(config_instance._validateSetting('sample', 'outputCounter', 'false')) == bool
    assert config_instance._validateSetting('sample', 'outputCounter', 'false') is False


def test_validate_setting_minuteOfHourRate(eventgen_config):
    """Test minuteOfHourRate config is dict with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    minuteOfHourRate = '{ "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1,' \
                       ' "10": 1, "11": 1, "12": 1, "13": 1, "14": 1, "15": 1, "16": 1, "17": 1, "18": 1,' \
                       ' "19": 1, "20": 1, "21": 1, "22": 1, "23": 1, "24": 1, "25": 1, "26": 1, "27": 1,' \
                       ' "28": 1, "29": 1, "30": 1, "31": 1, "32": 1, "33": 1, "34": 1, "35": 4, "36": 0.1,' \
                       ' "37": 0.1, "38": 1, "39": 1, "40": 1, "41": 1, "42": 1, "43": 1, "44": 1, "45": 1,' \
                       ' "46": 1, "47": 1, "48": 1, "49": 1, "50": 1, "51": 1, "52": 1, "53": 1, "54": 1,' \
                       ' "55": 1, "56": 1, "57": 1, "58": 1, "59": 1 }'
    assert type(config_instance._validateSetting('sample', 'minuteOfHourRate', minuteOfHourRate)) == dict
    result = json.loads(minuteOfHourRate)
    assert config_instance._validateSetting('sample', 'minuteOfHourRate', minuteOfHourRate) == result


def test_validate_setting_hourOfDayRate(eventgen_config):
    """Test hourOfDayRate config is dict with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    hourOfDayRate = '{ "0": 0.30, "1": 0.20, "2": 0.20, "3": 0.20, "4": 0.20, "5": 0.25, "6": 0.35, "7": 0.50,' \
                    ' "8": 0.60, "9": 0.65, "10": 0.70, "11": 0.75, "12": 0.77, "13": 0.80, "14": 0.82,' \
                    ' "15": 0.85, "16": 0.87, "17": 0.90, "18": 0.95, "19": 1.0, "20": 0.85, "21": 0.70,' \
                    ' "22": 0.60, "23": 0.45 }'
    assert type(config_instance._validateSetting('sample', 'hourOfDayRate', hourOfDayRate)) == dict
    result = json.loads(hourOfDayRate)
    assert config_instance._validateSetting('sample', 'hourOfDayRate', hourOfDayRate) == result


def test_validate_setting_dayOfWeekRate(eventgen_config):
    """Test dayOfWeekRate config is dict with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    dayOfWeekRate = '{ "0": 0.97, "1": 0.95, "2": 0.90, "3": 0.97, "4": 1.0, "5": 0.99, "6": 0.55 }'
    assert type(config_instance._validateSetting('sample', 'dayOfWeekRate', dayOfWeekRate)) == dict
    result = json.loads(dayOfWeekRate)
    assert config_instance._validateSetting('sample', 'dayOfWeekRate', dayOfWeekRate) == result


def test_validate_setting_dayOfMonthRate(eventgen_config):
    """Test dayOfMonthRate config is dict with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    dayOfMonthRate = '{ "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, "10": 1,' \
                     ' "11": 1, "12": 1, "13": 1, "14": 1, "15": 1, "16": 1, "17": 1, "18": 1, "19": 1, "20": 1,' \
                     ' "21": 1, "22": 1, "23": 1, "24": 1, "25": 1, "26": 1, "27": 1, "28": 1, "29": 1, "30": 1,' \
                     ' "31": 1 }'
    assert type(config_instance._validateSetting('sample', 'dayOfMonthRate', dayOfMonthRate)) == dict
    result = json.loads(dayOfMonthRate)
    assert config_instance._validateSetting('sample', 'dayOfMonthRate', dayOfMonthRate) == result


def test_validate_setting_monthOfYearRate(eventgen_config):
    """Test monthOfYearRate config is dict with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    monthOfYearRate = '{ "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1,' \
                      ' "8": 1, "9": 1, "10": 1, "11": 1, "12": 1 }'
    assert type(config_instance._validateSetting('sample', 'monthOfYearRate', monthOfYearRate)) == dict
    result = json.loads(monthOfYearRate)
    assert config_instance._validateSetting('sample', 'monthOfYearRate', monthOfYearRate) == result


def test_validate_setting_httpeventServers(eventgen_config):
    """Test httpeventServers config is dict with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    httpeventServers = '{"servers":[{ "protocol":"https", "address":"127.0.0.1",' \
                       ' "port":"8088", "key":"8d5ab52c-3759-49e3-b66a-5213ce525692"}]}'
    assert type(config_instance._validateSetting('sample', 'httpeventServers', httpeventServers)) == dict
    result = json.loads(httpeventServers)
    assert config_instance._validateSetting('sample', 'httpeventServers', httpeventServers) == result


def test_validate_setting_autotimestamps(eventgen_config):
    """Test autotimestamps config is dict with right value"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    autotimestamps = r'[["\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}", "%Y-%m-%d %H:%M:%S"], ' \
                     r'["\\d{1,2}\\/\\w{3}\\/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}:\\d{1,3}", "%d/%b/%Y %H:%M:%S:%f"], ' \
                     r'["\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}", "%Y-%m-%dT%H:%M:%S.%f"], ' \
                     r'["\\d{1,2}/\\w{3}/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}:\\d{1,3}", "%d/%b/%Y %H:%M:%S:%f"], ' \
                     r'["\\d{1,2}/\\d{2}/\\d{2}\\s\\d{1,2}:\\d{2}:\\d{2}", "%m/%d/%y %H:%M:%S"], ' \
                     r'["\\d{2}-\\d{2}-\\d{4} \\d{2}:\\d{2}:\\d{2}", "%m-%d-%Y %H:%M:%S"], ' \
                     r'["\\w{3} \\w{3} +\\d{1,2} \\d{2}:\\d{2}:\\d{2}", "%a %b %d %H:%M:%S"], ' \
                     r'["\\w{3} \\w{3} \\d{2} \\d{4} \\d{2}:\\d{2}:\\d{2}", "%a %b %d %Y %H:%M:%S"], ' \
                     r'["^(\\w{3}\\s+\\d{1,2}\\s\\d{2}:\\d{2}:\\d{2})", "%b %d %H:%M:%S"], ' \
                     r'["(\\w{3}\\s+\\d{1,2}\\s\\d{1,2}:\\d{1,2}:\\d{1,2})", "%b %d %H:%M:%S"], ' \
                     r'["(\\w{3}\\s\\d{1,2}\\s\\d{1,4}\\s\\d{1,2}:\\d{1,2}:\\d{1,2})", "%b %d %Y %H:%M:%S"], ' \
                     r'["\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}\\.\\d{3}", "%Y-%m-%d %H:%M:%S.%f"], ' \
                     r'["\\,\\d{2}\\/\\d{2}\\/\\d{2,4}\\s+\\d{2}:\\d{2}:\\d{2}\\s+[AaPp][Mm]\\,", ' \
                     r'",%m/%d/%Y %I:%M:%S %p,"], ' \
                     r'["^\\w{3}\\s+\\d{2}\\s+\\d{2}:\\d{2}:\\d{2}", "%b %d %H:%M:%S"], ' \
                     r'["\\d{2}/\\d{2}/\\d{4} \\d{2}:\\d{2}:\\d{2}", "%m/%d/%Y %H:%M:%S"], ' \
                     r'["^\\d{2}\\/\\d{2}\\/\\d{2,4}\\s+\\d{2}:\\d{2}:\\d{2}\\s+[AaPp][Mm]", "%m/%d/%Y %I:%M:%S %p"],' \
                     r'["\\d{2}\\/\\d{2}\\/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}", "%m-%d-%Y %H:%M:%S"], ' \
                     r'["\\\"timestamp\\\":\\s\\\"(\\d+)", "%s"], ' \
                     r'["\\d{2}\\/\\w+\\/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}:\\d{3}", "%d-%b-%Y %H:%M:%S:%f"], ' \
                     r'["\\\"created\\\":\\s(\\d+)", "%s"], ["\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}", ' \
                     r'"%Y-%m-%dT%H:%M:%S"], ' \
                     r'["\\d{1,2}/\\w{3}/\\d{4}:\\d{2}:\\d{2}:\\d{2}:\\d{1,3}", "%d/%b/%Y:%H:%M:%S:%f"], ' \
                     r'["\\d{1,2}/\\w{3}/\\d{4}:\\d{2}:\\d{2}:\\d{2}", "%d/%b/%Y:%H:%M:%S"]]'
    assert type(config_instance._validateSetting('sample', 'autotimestamps', autotimestamps)) == list
    result = json.loads(autotimestamps)
    assert config_instance._validateSetting('sample', 'autotimestamps', autotimestamps) == result


def test_getPlugin(eventgen_config):
    """Test getPlugin method without loading any plugins"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    with pytest.raises(KeyError):
        config_instance.getPlugin('output.awss3')


def test_getSplunkUrl(eventgen_config):
    """Test getSplunkUrl with provided sample object"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    sample = Sample('test')
    sample.splunkHost = 'localhost'
    sample.splunkMethod = 'https'
    sample.splunkPort = '8088'

    assert ('https://localhost:8088', 'https', 'localhost', '8088') == config_instance.getSplunkUrl(sample)


def test_validateTimeZone(eventgen_config):
    """Test _validateTimeZone method"""
    pass


def test_validateSeed(eventgen_config):
    """Test _validateSeed method"""
    pass


def test_punct(eventgen_config):
    """Test _punct method with given string"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    assert '--:\n$^' == config_instance._punct('this-is-a: test \ntest $^')


def test_parse(eventgen_config):
    """Test parse method with given evengen config"""
    config_instance = eventgen_config(configfile='eventgen.conf.config')
    config_instance.parse()
    assert len(config_instance.samples) == 1
