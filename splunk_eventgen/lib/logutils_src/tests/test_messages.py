import logutils
import sys
import unittest

class MessageTest(unittest.TestCase):
    if sys.version_info[:2] >= (2, 6):
        def test_braces(self):
            "Test whether brace-formatting works."
            __ = logutils.BraceMessage
            m = __('Message with {0} {1}', 2, 'placeholders')
            self.assertEqual(str(m), 'Message with 2 placeholders')
            m = __('Message with {0:d} {1}', 2, 'placeholders')
            self.assertEqual(str(m), 'Message with 2 placeholders')
            m = __('Message without {0:x} {1}', 16, 'placeholders')
            self.assertEqual(str(m), 'Message without 10 placeholders')

            class Dummy:
                pass

            dummy = Dummy()
            dummy.x, dummy.y = 0.0, 1.0
            m = __('Message with coordinates: ({point.x:.2f}, {point.y:.2f})',
                    point=dummy)
            self.assertEqual(str(m), 'Message with coordinates: (0.00, 1.00)')

    def test_dollars(self):
        "Test whether dollar-formatting works."
        __ = logutils.DollarMessage
        m = __('Message with $num ${what}', num=2, what='placeholders')
        self.assertEqual(str(m), 'Message with 2 placeholders')
        ignored = object()
        self.assertRaises(TypeError, __, 'Message with $num ${what}',
                          ignored, num=2, what='placeholders')
