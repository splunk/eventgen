#!/usr/bin/env python
# encoding: utf-8

from setuptools import setup
from setuptools import find_packages
import splunk_eventgen


VERSION = splunk_eventgen.__version__

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()

def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='splunk_eventgen',
    version=VERSION,
    description='Splunk Event Generator to produce real-time, representative data',
    long_description=long_description,
    url='https://repo.splunk.com/artifactory/api/pypi/pypi-local',
    author='Splunk, Inc.',
    author_email='tonyl@splunk.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7'],
    keywords='splunk eventgen container containers docker automation',
    entry_points={'console_scripts': ["splunk_eventgen = splunk_eventgen.__main__:main"]},
    include_package_data=True,
    packages=find_packages(),
    package_data={"splunk_eventgen": ['*.sh', '*.txt', '*.yml'], '': ['*.sh', '*.txt', '*.yml']},
    install_requires=[
        'pytest>=3.0.0', # Required to test functional tests in eventgen.
        'boto3',
        'requests==2.19.1',
        'requests[security]',
        'logutils>=0.3.4.1',
        'futures>=3.0.5',
        'ujson>=1.35', # way faster implementation of JSON processing
        'pyyaml',
        'httplib2',
        'jinja2',
        'pyrabbit==1.1.0'
    ]
    )
