from __future__ import absolute_import

from logutils.testing import Matcher, TestHandler


class MyTestHandler(TestHandler):
    def __init__(self):
        TestHandler.__init__(self, Matcher())
