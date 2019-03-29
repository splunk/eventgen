# Copyright 2009 Brian Quinlan. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.
"""Execute computations asynchronously using threads or processes."""

__author__ = 'Brian Quinlan (brian@sweetapp.com)'

from concurrent.futures._base import (ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION, CancelledError, Executor, Future,
                                      TimeoutError, as_completed, wait)
from concurrent.futures.thread import ThreadPoolExecutor

try:
    from concurrent.futures.process import ProcessPoolExecutor
except ImportError:
    # some platforms don't have multiprocessing
    pass
