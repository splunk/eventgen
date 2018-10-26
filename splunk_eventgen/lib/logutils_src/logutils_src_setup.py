# -*- coding: utf-8 -*-

import distutils.core
import logutils
from os.path import join, dirname, abspath
import re


def description():
    f = open(join(dirname(__file__), 'README.rst'))
    readme = f.read()
    f.close()
    regexp = r'logutils\s*[\d.]*\s*\n=======+\s*\n(.*)Requirements '
    reqts, = re.findall(regexp, readme, re.DOTALL)
    regexp = r'Availability & Documentation\s*\n-----+\s*\n(.*)'
    avail, = re.findall(regexp, readme, re.DOTALL)
    return reqts + avail

class TestCommand(distutils.core.Command):
    user_options = []

    def run(self):
        import sys
        import unittest

        sys.path.append(join(dirname(__file__), 'tests'))
        import logutil_tests
        loader = unittest.TestLoader()
        runner = unittest.TextTestRunner()
        test_results = runner.run(loader.loadTestsFromModule(logutil_tests))
        if not test_results.wasSuccessful():
            sys.exit(1)

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

distutils.core.setup(
    name='logutils',
    version=logutils.__version__,
    author='Vinay Sajip',
    author_email='vinay_sajip@red-dove.com',
    url='http://code.google.com/p/logutils/',
    description='Logging utilities',
    long_description = description(),
    license='Copyright (C) 2010-2017 by Vinay Sajip. All Rights Reserved. See LICENSE.txt for license.',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        'Topic :: Software Development',
    ],
    packages=['logutils'],
    cmdclass={
        'test': TestCommand,
    },

)
