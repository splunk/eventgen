#!/usr/bin/env python2
# encoding: utf-8

import argparse
import os
import sys
import re
import subprocess

file_location = os.path.dirname(os.path.realpath(__file__))
splunk_eventgen_location = os.path.normpath(os.path.join(file_location, '..'))
push_location = os.path.normpath(os.path.join(file_location, 'push'))
build_location = os.path.normpath(os.path.join(file_location, 'build'))

sys.path.insert(0, splunk_eventgen_location)
from splunk_eventgen.__init__ import _set_dev_version, _set_release_version


def push_pypi(args):
    print "Pushing PyPI..."
    push = subprocess.Popen(["python", "setup.py", "sdist", "upload", "-r", "production"], cwd=splunk_eventgen_location)
    push.wait()

def parse():
    parser = argparse.ArgumentParser(prog='Eventgen Continuous Deployment',
                                     description='Build and upload pip or Docker images')
    subparsers = parser.add_subparsers(title='package_type',
                                       help="please specify which package type to build or deploy", dest='subcommand')
    parser.add_argument("--push", default=False, action='store_true',
                        help="Pypi pushes to production, Container pushes to branch path unless --production flag passed, then versioned Eventgen created")
    parser.add_argument('--dev', default=True, action='store_true', help='specify the package if its dev')
    parser.add_argument('--release', default=False, action='store_true', help='specify the package if its release')
    ## Adding Pypi Module subparser
    pypi_subparser = subparsers.add_parser('pypi', help="Build/deploy pypi module to production")
    return parser.parse_args()


def main():
    # Parse out the options, and execute for "help"
    args = parse()
    # Inject correct ansible version into args
    if args.dev:
        _set_dev_version()
    if args.release:
        _set_release_version()
    if args.push:
        push_pypi(args)

if __name__ == "__main__":
    main()
