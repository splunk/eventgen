#!/usr/bin/env python3
# encoding: utf-8

import json
import os

file_location = os.path.normpath(os.path.realpath(__file__))
VERSION_FILE = "version.json"
VERSION_LOCATION = os.path.normpath(os.path.join(file_location, '..', VERSION_FILE))


def _get_version():
    """
    @return: Version Number
    """
    with open(VERSION_LOCATION, 'rb') as fp:
        json_data = json.load(fp)
        version = json_data['version']
    return version


def _set_dev_version():
    """
    Write .dev at the end of version
    :return: None
    """
    with open(VERSION_LOCATION, 'rb+') as fp:
        json_data = json.load(fp)
        new_version = json_data['version'].split('.dev0')[0]
        new_version_write = new_version + ".dev0"
        json_data['version'] = new_version_write
        fp.seek(0)
        fp.write(json.dumps(json_data))


def _set_release_version():
    """
    Remove .dev at end of version if it exists
    :return: None
    """
    with open(VERSION_LOCATION, 'rb+') as fp:
        json_data = json.load(fp)
        new_version = json_data['version'].split('.dev0')[0]
        json_data['version'] = new_version
        fp.seek(0)
        fp.truncate()
        fp.write(json.dumps(json_data))


__version__ = _get_version()

if __name__ == "__main__":
    print(__version__)
