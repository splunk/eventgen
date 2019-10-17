import os
import sys

import pytest

SMALL = 'tests/small'
MEDIUM = 'tests/medium'
LARGE = 'tests/large'
XLARGE = 'tests/xlarge'
newargs = []
args = sys.argv[:]
ENV = os.environ
PATH = sys.path

# Normally, it is 8, which should match the cores/hyperthreads of most of our systems.
NUM_TEST_WORKERS_LARGE = '8'
"""
How to run the tests:
1. python run_tests.py
2. python run_tests.py {SMALL_TEST_PATH} {MEDIUM_TEST_PATH} {LARGE_TEST_PATH} {XLARGE_TEST_PATH} {optional RUN_DESTROY}
    - You can pass 'None' as a value to either to ignore those tests
    - To run a specific folder, file, pass it in as a value. ex
        * python run_tests.py None None tests/large/test_destroy.py None
"""
# Parse the inputs, figure out what tests to run
if len(args) > 1:
    args.pop(0)
    SMALL = args.pop(0)
    MEDIUM = args.pop(0)
    LARGE = args.pop(0)
    XLARGE = args.pop(0)

    if SMALL.lower() == 'none':
        SMALL = False
    if MEDIUM.lower() == 'none':
        MEDIUM = False
    if LARGE.lower() == 'none':
        LARGE = False
    if XLARGE.lower() == 'none':
        XLARGE = False

cov_args = [
    "--cov=splunk_eventgen",
    "--cov-config=tests/.coveragerc",
    "--cov-report=term",
    "--cov-report=html",
    "--cov-append"
]

# Run small tests
if SMALL:
    sys.path = PATH
    os.environ = ENV
    args = [SMALL, "--junitxml=tests/test-reports/tests_small_results.xml"] + cov_args
    rt = pytest.main(args)
    if rt != 0:
        print("There are failures in small test cases!")
        sys.exit(rt)


# Run medium tests
if MEDIUM:
    sys.path = PATH
    os.environ = ENV
    args = ["-sv", MEDIUM, "--junitxml=tests/test-reports/tests_medium_results.xml"] + cov_args
    rt = pytest.main(args)
    if rt != 0:
        print("There are failures in medium test cases!")
        sys.exit(rt)

# Commenting out other tests that aren't added yet.
# Run large tests
if LARGE:
    sys.path = PATH
    os.environ = ENV
    args = ["-sv", LARGE, "--junitxml=tests/test-reports/tests_large_results.xml"] + cov_args
    rt = pytest.main(args)
    if rt != 0:
        print("There are failures in large test cases!")
        sys.exit(rt)
