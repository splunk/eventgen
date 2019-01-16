import pytest
import sys
import time
import os
SMALL = 'tests/small'
MEDIUM = 'tests/medium'
LARGE = 'tests/large'
XLARGE = 'tests/xlarge'
newargs = []
args = sys.argv[:]
ENV = os.environ
PATH = sys.path

# Set to 1 is debugging is a problem.  Normally, it is 8, which should match the cores/hyperthreads of most of our systems.
NUM_TEST_WORKERS_LARGE = '8'

"""
How to run the tests:
1. python run_tests.py
2. python run_tests.py {SMALL_TESTS_TO_RUN} {MEDIUM_TESTS_TO_RUN} {LARGE_TESTS_TO_RUN} {XLARGE_TESTS_TO_RUN} {optional RUN_DESTROY}
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

# Array that will hold return codes
return_codes = []

# Run small tests
if SMALL:
    sys.path = PATH
    os.environ = ENV
    args = [ "--cov=splunk_eventgen", "--cov-config=tests/.coveragerc", "--cov-report=term", "--cov-report=html", SMALL, "--junitxml=tests/test-reports/tests_small_results.xml"]
    return_codes.append(pytest.main(args))

# Run medium tests
if MEDIUM:
    sys.path = PATH
    os.environ = ENV
    args = ["-sv", MEDIUM, "--junitxml=tests/test-reports/tests_medium_results.xml"]
    return_codes.append(pytest.main(args))

# Commenting out other tests that aren't added yet.
# Run large tests
if LARGE:
    sys.path = PATH
    os.environ = ENV
    args = ["-sv", LARGE, "--junitxml=tests/test-reports/tests_large_results.xml"]
    return_codes.append(pytest.main(args))

print("What do you call a Boomerang that doesn't come back....")
# We need to ensure we return a bad exit code if the tests do not completely pass
for code in return_codes:
    if int(code) != 0:
        sys.exit(int(code))
