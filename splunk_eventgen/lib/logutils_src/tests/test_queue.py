#
# Copyright (C) 2010-2017 Vinay Sajip. See LICENSE.txt for details.
#
import logging
from logutils.testing import TestHandler, Matcher
from logutils.queue import QueueHandler, QueueListener, queue
import unittest

class QueueTest(unittest.TestCase):
    def setUp(self):
        self.handler = h = TestHandler(Matcher())
        self.logger = l = logging.getLogger()
        self.queue = q = queue.Queue(-1)
        self.qh = qh = QueueHandler(q)
        self.ql = ql = QueueListener(q, h)
        ql.start()
        l.addHandler(qh)

    def tearDown(self):
        self.logger.removeHandler(self.qh)
        self.qh.close()
        self.handler.close()

    def test_simple(self):
        "Simple test of queue handling and listening."
        # Just as a demo, let's log some messages.
        # Only one should show up in the log.
        self.logger.debug("This won't show up.")
        self.logger.info("Neither will this.")
        self.logger.warning("But this will.")
        self.ql.stop() #ensure all records have come through.
        h = self.handler
        #import pdb; pdb.set_trace()
        self.assertTrue(h.matches(levelno=logging.WARNING))
        self.assertFalse(h.matches(levelno=logging.DEBUG))
        self.assertFalse(h.matches(levelno=logging.INFO))

    def test_partial(self):
        "Test of partial matching through queues."
        # Just as a demo, let's log some messages.
        # Only one should show up in the log.
        self.logger.debug("This won't show up.")
        self.logger.info("Neither will this.")
        self.logger.warning("But this will.")
        self.ql.stop() #ensure all records have come through.
        h = self.handler
        self.assertTrue(h.matches(msg="ut th")) # from "But this will"
        self.assertTrue(h.matches(message="ut th")) # from "But this will"
        self.assertFalse(h.matches(message="either"))
        self.assertFalse(h.matches(message="won't"))

    def test_multiple(self):
        "Test of matching multiple values through queues."
        # Just as a demo, let's log some messages.
        # Only one should show up in the log.
        self.logger.debug("This won't show up.")
        self.logger.info("Neither will this.")
        self.logger.warning("But this will.")
        self.logger.error("And so will this.")
        self.ql.stop() #ensure all records have come through.
        h = self.handler
        self.assertTrue(h.matches(levelno=logging.WARNING,
                                  message='ut thi'))
        self.assertTrue(h.matches(levelno=logging.ERROR,
                                  message='nd so wi'))
        self.assertFalse(h.matches(levelno=logging.INFO))

if __name__ == '__main__':
    unittest.main()
