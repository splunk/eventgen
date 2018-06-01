#
# Copyright (C) 2008-2017 Vinay Sajip. See LICENSE.txt for details.
#
import logging
from logutils.adapter import LoggerAdapter
from logutils.testing import TestHandler, Matcher
import unittest

class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.handler = h = TestHandler(Matcher())
        self.logger = l = logging.getLogger()
        l.addHandler(h)
        self.adapter = LoggerAdapter(l, {})

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_simple(self):
        "Simple test of logging test harness."
        # Just as a demo, let's log some messages.
        # Only one should show up in the log.
        self.adapter.debug("This won't show up.")
        self.adapter.info("Neither will this.")
        self.adapter.warning("But this will.")
        h = self.handler
        self.assertTrue(h.matches(levelno=logging.WARNING))
        self.assertFalse(h.matches(levelno=logging.DEBUG))
        self.assertFalse(h.matches(levelno=logging.INFO))

    def test_partial(self):
        "Test of partial matching in logging test harness."
        # Just as a demo, let's log some messages.
        # Only one should show up in the log.
        self.adapter.debug("This won't show up.")
        self.adapter.info("Neither will this.")
        self.adapter.warning("But this will.")
        h = self.handler
        self.assertTrue(h.matches(msg="ut th")) # from "But this will"
        self.assertTrue(h.matches(message="ut th")) # from "But this will"
        self.assertFalse(h.matches(message="either"))
        self.assertFalse(h.matches(message="won't"))

    def test_multiple(self):
        "Test of matching multiple values in logging test harness."
        # Just as a demo, let's log some messages.
        # Only one should show up in the log.
        self.adapter.debug("This won't show up.")
        self.adapter.info("Neither will this.")
        self.adapter.warning("But this will.")
        self.adapter.error("And so will this.")
        h = self.handler
        self.assertTrue(h.matches(levelno=logging.WARNING,
                                  message='ut th'))
        self.assertTrue(h.matches(levelno=logging.ERROR,
                                  message='nd so w'))
        self.assertFalse(h.matches(levelno=logging.INFO))

    def test_hashandlers(self):
        "Test of hasHandlers() functionality."
        self.assertTrue(self.adapter.hasHandlers())
        self.logger.removeHandler(self.handler)
        self.assertFalse(self.adapter.hasHandlers())
        self.logger.addHandler(self.handler)
        self.assertTrue(self.adapter.hasHandlers())

if __name__ == '__main__':
    unittest.main()
