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
                         "documentation/_book", "documentation/CHANGELOG.md", "setup.py"]
# Going to manually remove these...
internal_link_paths = ["tests/large/test_eventgen_orchestration.py", "tests/requirements.txt"]
internal_link_comment = "# This code block must be removed/changed before external release"
test_categories = ["tests/small", "tests/medium", "tests/large"]
replace_host = {"splunktelbe-01\.splunk\.com": "host4.foobar.com", "esxi4104\.splunk\.com": "host2.foobar.com",
                "wimpy\.splunk\.com": "host3.foobar.com", "be-01\.splunk\.com": "host1.foobar.com",
                "apps-demo04\.sv\.splunk\.com": "host5.foobar.com", "esxi4103\.splunk\.com": "host6.foobar.com",
                "ESXi4103\.splunk\.com": "host7.foobar.com", "ross-datagen\.sv\.splunk\.com": "host8.foobar.com",
                "io-qa\.sv\.splunk.com": "host9.foobar.com", "esxi4102\.splunk\.com": "host10.foobar.com",
                "io-qa-splunk\.sv\.splunk\.com": "host11.foobar.com"}

sys.path.insert(0, splunk_eventgen_location)
from splunk_eventgen.__init__ import _set_dev_version, _set_release_version
from splunk_eventgen.__main__ import build_splunk_app


def replace_internal_hosts():
    """
    Replace Splunk host names with imaginary host names (defined above). This should not affect code funtionality as
    all expected replacements are a part of a tutorial or piece of sample code.
    """
    for dirname, dirs, files in os.walk(eventgen_external_location):
        for filename in files:
            filepath = os.path.join(dirname, filename)
            if ".git" not in filepath:
                with open(filepath, 'r') as infile:
                    lines = infile.read()
                for key in replace_host.keys():
                    lines = re.sub(key, replace_host[key], lines)
                with open(filepath, 'w') as outfile:
                    outfile.write(lines)


def remove_internal_links():
    """
    Replace Splunk internal links with empty strings. If the links are used by a test file, mark the test as skipped.
    """
    for relative_path in internal_link_paths:
        path = os.path.normpath(os.path.join(eventgen_external_location, relative_path))
        is_test = False
        for category in test_categories:
            if category in path:
                is_test = True
        with open(path, 'r') as infile:
            lines = infile.read()
            lines = re.sub(".*splunk\.com.*", "", lines)
            if is_test:
                lines = re.sub(internal_link_comment, '@pytest.mark.skip(reason="This test uses an internal link")',
                               lines)
        with open(path, 'w') as outfile:
            outfile.write(lines)

def create_branch(branch_name, eventgen_location):
    """
    Create a new github branch from the latest develop branch.
    """
    # Make sure our branch is clean and we can checkout
    response = os.popen("git status")
    if "nothing to commit, working tree clean" in response.read():
        cwd = os.getcwd()
        os.chdir(eventgen_location)
        response = os.popen("git checkout -b {}; make clean".format(branch_name))
        os.chdir(cwd)
    else:
        raise Exception("Current branch is not clean, cannot checkout new branch")


def update_versions(new_version, eventgen_location):
    """
    Update all version references for the new release and reset the build counter.
    """
    version_file = os.path.normpath(os.path.join(eventgen_location, "splunk_eventgen/version.json"))
    conf_file = os.path.normpath(os.path.join(eventgen_location, "splunk_eventgen/splunk_app/default/app.conf"))
    with open(version_file, "r") as infile:
        version_json = json.load(infile)
        version_json["version"] = new_version
    with open(version_file, "w") as outfile:
        json.dump(version_json, outfile)
    with open(conf_file, "r") as infile:
        lines = infile.read()
        lines = re.sub("build = [0-9]*", "build = 1", lines)
        lines = re.sub("version = [0-9.dev]*", "version = {}".format(new_version), lines)
    with open(conf_file, "w") as outfile:
        outfile.write(lines)


def prepare_internal_release(new_version, artifactory, pip, container):
    """
    Prepare documentation for release and publish to specified internal sources.
    """
    # Github commands not needed for now
    # output = create_branch("release/{}".format(new_version), eventgen_internal_location)
    if new_version:
        update_versions(new_version, eventgen_internal_location)
    if artifactory:
        print("Building .spl file for internal artifactory directory")
        build_splunk_app(eventgen_internal_location, source=eventgen_internal_location, remove=True)
    if pip:
        push_pypi(eventgen_internal_location)
    if container:
        push_image(eventgen_internal_location)
    # TODO: write a release notes and distribute to productsall + eng (may need to refactor docs/samples first)
    # Develop branches are updated manually for now, don't update with dev version yet
    # update_versions(new_version+'.dev0', eventgen_internal_location)


def prepare_external_release(new_version, splunkbase):
    """
    Remove all sensitive Splunk information from codebase and publish to specified external sources.
    """
    # Github commands not needed for now
    # output = create_branch("release/{}_open_source".format(new_version), eventgen_external_location)
    if new_version:
        update_versions(new_version, eventgen_external_location)
    remove_internal_references()
    if splunkbase:
        print("Building .spl file for external splunkbase directory")
        build_splunk_app(eventgen_external_location, source=eventgen_external_location, remove=True)


def remove_internal_references():
    """
    Remove all files and/or in-line references to Splunk credentials and other sensitive information.
    """
    # Doing this single step manually for now
    # remove_internal_links()
    # Remove unnecessary/sensitive files
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
            if internal_link_comment in line:
                found = not found
            elif not found:
                new_lines += (line+"\n")
    with open(internal_core_file, 'w') as outfile:
        outfile.writelines(new_lines)
    # Remove remaining internal links across entire project
    replace_internal_hosts()


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
    # internal/external publish args
    parser.add_argument("--artifactory", "--af", default=False, action="store_true",
                        help="Publish eventgen app to Splunk internal Artifactory as .spl file")
    parser.add_argument("--pip", default=False, action="store_true",
                        help="Publish version update to internal eventgen pip module")
    parser.add_argument("--container", "--ct", default=False, action="store_true",
                        help="Publish new container to internal")
    parser.add_argument("--splunkbase", "--sb", default=False, action="store_true",
                        help="Publish eventgen as an app to external/public splunkbase")
    parser.add_argument("--version", "--v", type=str, default=None,
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
        push_pypi(splunk_eventgen_location)
    # Copy files to new directories for editing
    if os.path.exists(eventgen_external_location):
        shutil.rmtree(eventgen_external_location)
    shutil.copytree(splunk_eventgen_location, eventgen_external_location)
    if os.path.exists(eventgen_internal_location):
        shutil.rmtree(eventgen_internal_location)
    shutil.copytree(splunk_eventgen_location, eventgen_internal_location)
    # Prepare for releases based on command-line arguments
    prepare_internal_release(args.version, args.artifactory, args.pip, args.container)
    prepare_external_release(args.version, args.splunkbase)


if __name__ == "__main__":
    main()
