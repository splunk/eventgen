#
# Copyright (C) 2011-2017 Vinay Sajip. See LICENSE.txt for details.
#
import logging
from logutils.testing import TestHandler, Matcher
from logutils.redis import RedisQueueHandler, RedisQueueListener
from redis import Redis
import socket
import subprocess
import time
import unittest

class QueueListener(RedisQueueListener):
    def dequeue(self, block):
        record = RedisQueueListener.dequeue(self, block)
        if record:
            record = logging.makeLogRecord(record)
        return record

class RedisQueueTest(unittest.TestCase):
    def setUp(self):
        self.handler = h = TestHandler(Matcher())
        self.logger = l = logging.getLogger()
        self.server = subprocess.Popen(['redis-server'],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        self.wait_for_server()
        self.queue = q = Redis()
        self.qh = qh = RedisQueueHandler(redis=q)
        self.ql = ql = QueueListener(h, redis=q)
        ql.start()
        l.addHandler(qh)

    def tearDown(self):
        self.logger.removeHandler(self.qh)
        self.qh.close()
        self.handler.close()
        self.server.terminate()

    def wait_for_server(self):
        maxtime = time.time() + 2 # 2 seconds to wait for server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while time.time() < maxtime:
            try:
                sock.connect(('localhost', 6379))
                break
            except socket.error:
                pass
        if time.time() >= maxtime:
            raise Exception('unable to connect to Redis server')
        sock.close()

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
