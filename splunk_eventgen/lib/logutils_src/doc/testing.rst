Unit testing
============

When developing unit tests, you may find the
:class:`~logutils.testing.TestHandler` and :class:`~logutils.testing.Matcher`
classes useful.

Typical usage::

    import logging
    from logutils.testing import TestHandler, Matcher
    import unittest

    class LoggingTest(unittest.TestCase):
        def setUp(self):
            self.handler = h = TestHandler(Matcher())
            self.logger = l = logging.getLogger()
            l.addHandler(h)

        def tearDown(self):
            self.logger.removeHandler(self.handler)
            self.handler.close()

        def test_simple(self):
            "Simple test of logging test harness."
            # Just as a demo, let's log some messages.
            # Only one should show up in the log.
            self.logger.debug("This won't show up.")
            self.logger.info("Neither will this.")
            self.logger.warning("But this will.")
            h = self.handler
            self.assertTrue(h.matches(levelno=logging.WARNING))
            self.assertFalse(h.matches(levelno=logging.DEBUG))
            self.assertFalse(h.matches(levelno=logging.INFO))

        def test_partial(self):
            "Test of partial matching in logging test harness."
            # Just as a demo, let's log some messages.
            # Only one should show up in the log.
            self.logger.debug("This won't show up.")
            self.logger.info("Neither will this.")
            self.logger.warning("But this will.")
            h = self.handler
            self.assertTrue(h.matches(msg="ut th")) # from "But this will"
            self.assertTrue(h.matches(message="ut th")) # from "But this will"
            self.assertFalse(h.matches(message="either"))
            self.assertFalse(h.matches(message="won't"))

        def test_multiple(self):
            "Test of matching multiple values in logging test harness."
            # Just as a demo, let's log some messages.
            # Only one should show up in the log.
            self.logger.debug("This won't show up.")
            self.logger.info("Neither will this.")
            self.logger.warning("But this will.")
            self.logger.error("And so will this.")
            h = self.handler
            self.assertTrue(h.matches(levelno=logging.WARNING,
                                      message='ut thi'))
            self.assertTrue(h.matches(levelno=logging.ERROR,
                                      message='nd so wi'))
            self.assertFalse(h.matches(levelno=logging.INFO))

.. automodule:: logutils.testing
   :members:
