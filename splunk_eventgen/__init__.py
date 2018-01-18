#!/usr/bin/env python2
# encoding: utf-8

import json
import os
file_location = os.path.normpath(os.path.realpath(__file__))
VERSION_FILE = "version.json"
VERSION_LOCATION = os.path.normpath(os.path.join(file_location, '..', VERSION_FILE))


def _get_version(versionfile):
    """
    @param versionfile: File to get the version info from 
    @return: Version Number
    """
    with open(VERSION_LOCATION, 'r') as fp:
        json_data = json.load(fp)
        version = json_data['version']
    fp.close()
    return version

def _set_dev_version():
    """
    Write .dev at the end of version
    :return: None
    """
    with open(VERSION_LOCATION, 'r+') as fp:
        json_data = json.load(fp)
        new_version = json_data['version'].split('.dev0')[0]
        new_version_write = new_version + ".dev0"
        json_data['version'] = new_version_write
        fp.seek(0)
        fp.write(json.dumps(json_data))
    fp.close()

def _set_release_version():
    """
    Remove .dev at end of version if it exists
    :return: None
    """
    with open(VERSION_LOCATION, 'r+') as fp:
        json_data = json.load(fp)
        new_version = json_data['version'].split('.dev0')[0]
        json_data['version'] = new_version
        fp.seek(0)
        fp.truncate()
        fp.write(json.dumps(json_data))
    fp.close()


__version__ = _get_version(versionfile='version.json')

if __name__ == "__main__":
    print __version__
