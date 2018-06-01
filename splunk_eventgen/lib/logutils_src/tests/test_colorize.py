#
# Copyright (C) 2012-2017 Vinay Sajip. See LICENSE.txt for details.
#
import logging
import logutils.colorize
import os
import sys
import unittest

if sys.version_info[0] < 3:
    u = lambda o: unicode(o, 'unicode_escape')
else:
    u = lambda o: o

class ColorizeTest(unittest.TestCase):

    def test_colorize(self):
        logger = logging.getLogger()
        handler = logutils.colorize.ColorizingStreamHandler()
        logger.addHandler(handler)
        try:
            logger.warning(u('Some unicode string with some \u015b\u0107\u017a\xf3\u0142 chars'))
        finally:
            logger.removeHandler(handler)
