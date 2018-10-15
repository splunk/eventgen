#!/usr/bin/env python2
# encoding: utf-8
"""
Continuous Delivery script that automates code deployment from the cut of release branches
"""
import argparse
import os
import sys
import re
import subprocess
import json
import shutil

file_location = os.path.dirname(os.path.realpath(__file__))
splunk_eventgen_location = os.path.normpath(os.path.join(file_location, ".."))
eventgen_external_location = os.path.normpath(os.path.join(splunk_eventgen_location, "..", "eventgen_external"))
eventgen_internal_location = os.path.normpath(os.path.join(splunk_eventgen_location, "..", "eventgen_internal"))
internal_core_file = os.path.normpath(os.path.join(eventgen_internal_location, "splunk_eventgen", "eventgen_core.py"))
internal_remove_paths = ["Makefile", "Jenkinsfile", "scripts", "documentation/deploy.py", "documentation/node_modules",
                         "documentation/_book", "documentation/CHANGELOG.md"]
# TODO: get correct links below and resolve what documentation needs to be refactored (for its internal links)
splunkbase_url = "https://splunkbase.splunk.com/app/1924/edit/#/hosting"
artifactory_url = ""

sys.path.insert(0, splunk_eventgen_location)
from splunk_eventgen.__init__ import _set_dev_version, _set_release_version
from splunk_eventgen.__main__ import build_splunk_app


def create_branch(branch_name, working_dir):
    """
    Create a new github branch from the latest develop branch
    """
    # Make sure our branch is clean and we can checkout
    response = os.popen("git status")
    if "nothing to commit, working tree clean" in response.read():
        cwd = os.getcwd()
        os.chdir(working_dir)
        response = os.popen("git checkout -b {}; make clean".format(branch_name))
        os.chdir(cwd)
    else:
        raise Exception("Current branch is not clean, cannot checkout new branch")


def update_versions(new_version, root_path):
    """
    Update all version references to the new release version
    """
    # update version file
    version_file = os.path.normpath(os.path.join(root_path, "splunk_eventgen/version.json"))
    conf_file = os.path.normpath(os.path.join(root_path, "splunk_eventgen/splunk_app/default/app.conf"))
    with open(version_file, "r") as infile:
        version_json = json.load(infile)
        version_json["version"] = new_version
    with open(version_file, "w") as outfile:
        json.dump(version_json, outfile)
    # update version and reset build # in app.conf
    with open(conf_file, "r") as infile:
        lines = infile.read()
        lines = re.sub("build = [0-9]*", "build = 1", lines)
        lines = re.sub("version = [0-9.dev]*", "version = {}".format(new_version), lines)
    with open(conf_file, "w") as outfile:
        outfile.write(lines)


def prepare_internal_release(new_version, artifactory, pip, container, bitbucket):
    """
    Prepare documentation for release and publish to specified internal sources
    """
    output = create_branch("release/{}".format(new_version), eventgen_internal_location)
    update_versions(new_version, eventgen_internal_location)
    # handle publishing methods
    if artifactory:
        print("Pushing .spl file to artifactory")
        build_splunk_app(eventgen_internal_location, source=eventgen_internal_location, remove=True)
    if pip:
        print("Pushing eventgen package to internal PyPI index")
        push_pypi(eventgen_internal_location)
    if container:
        print("Pushing new eventgen image")
        push_image(eventgen_internal_location)
    # TODO: write a release notes and distribute to productsall + eng (commit messages? manual?)
    # Develop branches are updated manually for now, don't update with dev version yet
    # update_versions(new_version+'.dev0', eventgen_internal_location)

def prepare_external_release(new_version, splunkbase, bitbucket):
    """
    Remove all sensitive Splunk information from codebase and publish to specified external sources
    """
    output = create_branch("release/{}_open_source".format(new_version), eventgen_external_location)
    update_versions(new_version, eventgen_external_location)
    remove_internal_references(new_version)
    # handle publishing methods
    if splunkbase:
        print("Pushing eventgen app to splunkbase")


def remove_internal_references(new_version):
    """
    Remove all files and/or in-line references to Splunk credentials and other sensitive information
    """
    # TODO: remove splunk link inside setup.py
        # edit: remove all splunk links (repo.splunk.com...)
    for relative_path in internal_remove_paths:
        path = os.path.normpath(os.path.join(eventgen_external_location, relative_path))
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
    # Remove logger try/except block from eventgen_core.py
    with open(internal_core_file, 'r') as infile:
        found = False
        lines = infile.read().split('\n')
        new_lines = ""
        for line in lines:
            if "# This code block must be removed before external release" in line:
                found = not found
            elif not found:
                new_lines += (line+"\n")
    with open(internal_core_file, 'w') as outfile:
        outfile.writelines(new_lines)


def push_image(eventgen_location):
    print("Pushing docker image")
    cwd = os.getcwd()
    os.chdir(eventgen_location)
    response = os.popen("make push_image_production")
    os.chdir(cwd)


def push_pypi(eventgen_location):
    print "Pushing PyPI..."
    push = subprocess.Popen(["python", "setup.py", "sdist", "upload", "-r", "production"], cwd=eventgen_location)
    push.wait()


def parse():
    parser = argparse.ArgumentParser(prog="Eventgen Continuous Deployment",
                                     description="Build and upload pip or Docker images")
    subparsers = parser.add_subparsers(title="package_type",
                                       help="please specify which package type to build or deploy", dest="subcommand")
    parser.add_argument("--push", default=False, action="store_true",
                        help="Pypi pushes to production, Container pushes to branch path unless --production flag"
                             "passed, then versioned Eventgen created")
    parser.add_argument("--dev", default=False, action="store_true", help="specify the package if its dev")
    parser.add_argument("--release", default=False, action="store_true", help="specify the package if its release")
    parser.add_argument("--pdf", default=False, action="store_true", help="Generate a pdf from the documentation")
    # internal: .spl (app), pip module, container
    parser.add_argument("--artifactory", "--af", default=False, action="store_true",
                        help="Publish eventgen app to Splunk internal Artifactory as .spl file")
    parser.add_argument("--pip", default=False, action="store_true",
                        help="Publish version update to internal eventgen pip module")
    parser.add_argument("--container", "--ct", default=False, action="store_true",
                        help="Publish new container to internal")
    parser.add_argument("--internal-bitbucket", "--ibb", default=False, action="store_true",
                        help="Publish release version to public, internal Bitbucket repository")
    # external: splunkbase, github
    parser.add_argument("--splunkbase", "--sb", default=False, action="store_true",
                        help="Publish eventgen as an app to external/public splunkbase")
    parser.add_argument("--external-bitbucket", "--ebb", default=False, action="store_true",
                        help="Publish release version to public, external Bitbucket repository")
    parser.add_argument("--version", "--v", type=str, default=None, required=True,
                        help="specify version of new release")
    ## Adding Pypi Module subparser
    pypi_subparser = subparsers.add_parser("pypi", help="Build/deploy pypi module to production")
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
        push_pypi()
    # Copy files to new directories for editing
    if os.path.exists(eventgen_external_location):
        shutil.rmtree(eventgen_external_location)
    shutil.copytree(splunk_eventgen_location, eventgen_external_location)
    if os.path.exists(eventgen_internal_location):
        shutil.rmtree(eventgen_internal_location)
    shutil.copytree(splunk_eventgen_location, eventgen_internal_location)
    # Prepare for releases based on command-line arguments
    prepare_internal_release(args.version, args.artifactory, args.pip, args.container, args.internal_bitbucket)
    prepare_external_release(args.version, args.splunkbase, args.external_bitbucket)


if __name__ == "__main__":
    main()
