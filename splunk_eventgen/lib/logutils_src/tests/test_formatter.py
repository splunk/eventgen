#
# Copyright (C) 2009-2017 Vinay Sajip. See LICENSE.txt for details.
#
import logging
import logutils
import os
import sys
import unittest

class FormatterTest(unittest.TestCase):
    def setUp(self):
        self.common = {
            'name': 'formatter.test',
            'level': logging.DEBUG,
            'pathname': os.path.join('path', 'to', 'dummy.ext'),
            'lineno': 42,
            'exc_info': None,
            'func': None,
            'msg': 'Message with %d %s',
            'args': (2, 'placeholders'),
        }
        self.variants = {
        }

    def get_record(self, name=None):
        result = dict(self.common)
        if name is not None:
            result.update(self.variants[name])
        return logging.makeLogRecord(result)

    def test_percent(self):
        "Test %-formatting"
        r = self.get_record()
        f = logutils.Formatter('${%(message)s}')
        self.assertEqual(f.format(r), '${Message with 2 placeholders}')
        f = logutils.Formatter('%(random)s')
        self.assertRaises(KeyError, f.format, r)
        self.assertFalse(f.usesTime())
        f = logutils.Formatter('%(asctime)s')
        self.assertTrue(f.usesTime())
        f = logutils.Formatter('asctime')
        self.assertFalse(f.usesTime())

    if sys.version_info[:2] >= (2, 6):
        def test_braces(self):
            "Test {}-formatting"
            r = self.get_record()
            f = logutils.Formatter('$%{message}%$', style='{')
            self.assertEqual(f.format(r), '$%Message with 2 placeholders%$')
            f = logutils.Formatter('{random}', style='{')
            self.assertRaises(KeyError, f.format, r)
            self.assertFalse(f.usesTime())
            f = logutils.Formatter('{asctime}', style='{')
            self.assertTrue(f.usesTime())
            f = logutils.Formatter('asctime', style='{')
            self.assertFalse(f.usesTime())

    def test_dollars(self):
        "Test $-formatting"
        r = self.get_record()
        f = logutils.Formatter('$message', style='$')
        self.assertEqual(f.format(r), 'Message with 2 placeholders')
        f = logutils.Formatter('$$%${message}%$$', style='$')
        self.assertEqual(f.format(r), '$%Message with 2 placeholders%$')
        f = logutils.Formatter('${random}', style='$')
        self.assertRaises(KeyError, f.format, r)
        self.assertFalse(f.usesTime())
        f = logutils.Formatter('${asctime}', style='$')
        self.assertTrue(f.usesTime())
        f = logutils.Formatter('$asctime', style='$')
        self.assertTrue(f.usesTime())
        f = logutils.Formatter('asctime', style='$')
        self.assertFalse(f.usesTime())
