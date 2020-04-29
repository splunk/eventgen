#!/usr/bin/env python3
# encoding: utf-8

from setuptools import setup
import json

try:
    import pypandoc

    long_description = pypandoc.convert("README.md", "rst")
except (IOError, ImportError):
    long_description = open("README.md").read()


def get_version():
    """
    @return: Version Number
    """
    with open("splunk_eventgen/version.json", "rb") as fp:
        json_data = json.load(fp)
        version = json_data["version"]
    return version


def readme():
    with open("README.md") as f:
        return f.read()


def get_requirements():
    with open("requirements.txt") as f:
        requirements = f.read().splitlines()
    return requirements


VERSION = get_version()


setup(
    name="splunk_eventgen",
    version=VERSION,
    description="Splunk Event Generator to produce real-time, representative data",
    long_description=long_description,
    author="Splunk, Inc.",
    python_requires=">3.7.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
    ],
    keywords="splunk eventgen container containers docker automation",
    entry_points={
        "console_scripts": ["splunk_eventgen = splunk_eventgen.__main__:main"]
    },
    include_package_data=True,
    packages=["splunk_eventgen"],
    package_data={
        "splunk_eventgen": ["*.sh", "*.txt", "*.yml"],
        "": ["*.sh", "*.txt", "*.yml"],
    },
    install_requires=get_requirements(),
)
