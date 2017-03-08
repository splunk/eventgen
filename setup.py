#!/usr/bin/env python
# encoding: utf-8

from setuptools import setup
from setuptools import find_packages
import splunk_orca


VERSION = splunk_orca.__version__

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()

def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='splunk_orca',
    version=VERSION,
    description='Containerized Splunk deployment as a Service command line tool and api',
    long_description=long_description,
    url='https://repo.splunk.com/artifactory/api/pypi/pypi-local',
    author='Splunk, Inc.',
    author_email='jvega@splunk.com',
    classifiers=[
        'Development Status :: 1 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7'],
    keywords='splunk orca container containers docker automation',
    entry_points={'console_scripts': ["splunk_orca = splunk_orca.__main__:main"]},
    include_package_data=True,
    packages=find_packages(),
    package_data={"splunk_orca": ['*.sh', '*.txt', '*.yml'], '': ['*.sh', '*.txt', '*.yml']},
    install_requires=[
        'ansible>=2.2.0',
        'docker>=2.0.0',
        'pyasn1>=0.1.9', # required by requests[security]
        'pyOpenSSL==0.15.0', # required by requests[security]
        'pytest>=3.0.0', # Required to test functional tests in orca.
        'ndg-httpsclient>=0.4.1', # required by requests[security]
        'requests==2.10.0',
        'requests[security]',
        'futures>=3.0.5']
    )
