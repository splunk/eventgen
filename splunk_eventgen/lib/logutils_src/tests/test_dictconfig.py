#
# Copyright 2009-2017 by Vinay Sajip. See LICENSE.txt for details.
#
import logging
from logutils.adapter import LoggerAdapter
from logutils.dictconfig import dictConfig, named_handlers_supported
from logutils.testing import TestHandler, Matcher
import sys
import unittest

try:
    StandardError
except NameError:
    StandardError = Exception

class ExceptionFormatter(logging.Formatter):
    """A special exception formatter."""
    def formatException(self, ei):
        return "Got a [%s]" % ei[0].__name__

def formatFunc(format, datefmt=None):
    return logging.Formatter(format, datefmt)

def testHandler():
    return TestHandler(Matcher())

def handlerFunc():
    return logging.StreamHandler()

class CustomHandler(logging.StreamHandler):
    pass

class ConfigDictTest(unittest.TestCase):

    """Reading logging config from a dictionary."""

    def setUp(self):
        self.logger = l = logging.getLogger()
        self.adapter = LoggerAdapter(l, {})

        logger_dict = logging.getLogger().manager.loggerDict
        logging._acquireLock()
        try:
            self.saved_handlers = logging._handlers.copy()
            self.saved_handler_list = logging._handlerList[:]
            self.saved_loggers = logger_dict.copy()
            if hasattr(logging, '_levelNames'):
                self.saved_level_names = logging._levelNames.copy()
            else:
                self.saved_level_to_name = logging._levelToName.copy()
                self.saved_name_to_level = logging._nameToLevel.copy()
        finally:
            logging._releaseLock()

        self.root_logger = logging.getLogger("")
        self.original_logging_level = self.root_logger.getEffectiveLevel()


    def tearDown(self):
        self.root_logger.setLevel(self.original_logging_level)
        logging._acquireLock()
        try:
            if hasattr(logging, '_levelNames'):
                logging._levelNames.clear()
                logging._levelNames.update(self.saved_level_names)
            else:
                logging._levelToName.clear()
                logging._levelToName.update(self.saved_level_to_name)
                logging._nameToLevel.clear()
                logging._nameToLevel.update(self.saved_name_to_level)
            logging._handlers.clear()
            logging._handlers.update(self.saved_handlers)
            logging._handlerList[:] = self.saved_handler_list
            loggerDict = logging.getLogger().manager.loggerDict
            loggerDict.clear()
            loggerDict.update(self.saved_loggers)
        finally:
            logging._releaseLock()

    message_num = 0

    def next_message(self):
        """Generate a message consisting solely of an auto-incrementing
        integer."""
        self.message_num += 1
        return "%d" % self.message_num

    # config0 is a standard configuration.
    config0 = {
        'version': 1,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            }
        },
        'root' : {
            'level' : 'WARNING',
            'handlers' : ['hand1'],
        },
    }

    # config1 adds a little to the standard configuration.
    config1 = {
        'version': 1,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            }
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }

    # config2 has a subtle configuration error that should be reported
    config2 = {
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                'class' : 'logging.StreamHandler',
                'formatter' : 'form1',
                'level' : 'NOTSET',
                'stream'  : 'ext://sys.stdbout',
            },
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }

    #As config1 but with a misspelt level on a handler
    config2a = {
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                'class' : 'logging.StreamHandler',
                'formatter' : 'form1',
                'level' : 'NTOSET',
                'stream'  : 'ext://sys.stdout',
            },
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }


    #As config1 but with a misspelt level on a logger
    config2b = {
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                'class' : 'logging.StreamHandler',
                'formatter' : 'form1',
                'level' : 'NOTSET',
                'stream'  : 'ext://sys.stdout',
            },
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WRANING',
        },
    }

    # config3 has a less subtle configuration error
    config3 = {
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                'class' : 'logging.StreamHandler',
                'formatter' : 'misspelled_name',
                'level' : 'NOTSET',
                'stream'  : 'ext://sys.stdout',
            },
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }

    # config4 specifies a custom formatter class to be loaded
    config4 = {
        'version': 1,
        'formatters': {
            'form1' : {
                '()' : __name__ + '.ExceptionFormatter',
                'format' : '%(levelname)s:%(name)s:%(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            }
        },
        'root' : {
            'level' : 'NOTSET',
                'handlers' : ['hand1'],
        },
    }

    # As config4 but using an actual callable rather than a string
    config4a = {
        'version': 1,
        'formatters': {
            'form1' : {
                '()' : ExceptionFormatter,
                'format' : '%(levelname)s:%(name)s:%(message)s',
            },
            'form2' : {
                '()' : __name__ + '.formatFunc',
                'format' : '%(levelname)s:%(name)s:%(message)s',
            },
            'form3' : {
                '()' : formatFunc,
                'format' : '%(levelname)s:%(name)s:%(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            },
            'hand2' : {
                '()' : handlerFunc,
            },
        },
        'root' : {
            'level' : 'NOTSET',
                'handlers' : ['hand1'],
        },
    }

    # config5 specifies a custom handler class to be loaded
    config5 = {
        'version': 1,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            }
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }

    # config6 specifies a custom handler class to be loaded
    # but has bad arguments
    config6 = {
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                'class' : __name__ + '.CustomHandler',
                'formatter' : 'form1',
                'level' : 'NOTSET',
                'stream'  : 'ext://sys.stdout',
                '9' : 'invalid parameter name',
            },
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }

    #config 7 does not define compiler.parser but defines compiler.lexer
    #so compiler.parser should be disabled after applying it
    config7 = {
        'version': 1,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            }
        },
        'loggers' : {
            'compiler.lexer' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }

    config8 = {
        'version': 1,
        'disable_existing_loggers' : False,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            }
        },
        'loggers' : {
            'compiler' : {
                'level' : 'DEBUG',
                'handlers' : ['hand1'],
            },
            'compiler.lexer' : {
            },
        },
        'root' : {
            'level' : 'WARNING',
        },
    }

    config9 = {
        'version': 1,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
            }
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'WARNING',
                'handlers' : ['hand1'],
            },
        },
        'root' : {
            'level' : 'NOTSET',
        },
    }

    config9a = {
        'version': 1,
        'incremental' : True,
        'handlers' : {
            'hand1' : {
                'level' : 'WARNING',
            },
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'INFO',
            },
        },
    }

    config9b = {
        'version': 1,
        'incremental' : True,
        'handlers' : {
            'hand1' : {
                'level' : 'INFO',
            },
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'INFO',
            },
        },
    }

    #As config1 but with a filter added
    config10 = {
        'version': 1,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'filters' : {
            'filt1' : {
                'name' : 'compiler.parser',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': testHandler,
                'formatter': 'form1',
                'filters' : ['filt1'],
            }
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'filters' : ['filt1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
            'handlers' : ['hand1'],
        },
    }

    # As config10, but declaring a handler in a module using
    # absolute imports
    config11 = {
        'version': 1,
        'formatters': {
            'form1' : {
                'format' : '%(levelname)s ++ %(message)s',
            },
        },
        'filters' : {
            'filt1' : {
                'name' : 'compiler.parser',
            },
        },
        'handlers' : {
            'hand1' : {
                '()': 'mytest.MyTestHandler',
                'formatter': 'form1',
                'filters' : ['filt1'],
            }
        },
        'loggers' : {
            'compiler.parser' : {
                'level' : 'DEBUG',
                'filters' : ['filt1'],
            },
        },
        'root' : {
            'level' : 'WARNING',
            'handlers' : ['hand1'],
        },
    }

    def apply_config(self, conf):
        dictConfig(conf)

    def test_config0_ok(self):
        # A simple config which overrides the default settings.
        self.apply_config(self.config0)
        logger = logging.getLogger()
        # Won't output anything
        logger.info(self.next_message())
        # Outputs a message
        logger.error(self.next_message())
        h = logger.handlers[0]
        self.assertEqual(1, h.count)
        self.assertTrue(h.matchall([
                            dict(levelname='ERROR', message='2')
                        ]))

    def test_config1_ok(self, config=config1):
        # A config defining a sub-parser as well.
        self.apply_config(config)
        logger = logging.getLogger("compiler.parser")
        # Both will output a message
        logger.info(self.next_message())
        logger.error(self.next_message())
        h = logger.handlers[0]
        self.assertTrue(h.matchall([
                            dict(levelname='INFO', message='1'),
                            dict(levelname='ERROR', message='2'),
                        ]))

    def test_config2_failure(self):
        # A simple config which overrides the default settings.
        self.assertRaises(StandardError, self.apply_config, self.config2)

    def test_config2a_failure(self):
        # A simple config which overrides the default settings.
        self.assertRaises(StandardError, self.apply_config, self.config2a)

    def test_config2b_failure(self):
        # A simple config which overrides the default settings.
        self.assertRaises(StandardError, self.apply_config, self.config2b)

    def test_config3_failure(self):
        # A simple config which overrides the default settings.
        self.assertRaises(StandardError, self.apply_config, self.config3)

    def test_config4_ok(self):
        # A config specifying a custom formatter class.
        self.apply_config(self.config4)
        logger = logging.getLogger()
        h = logger.handlers[0]
        try:
            raise RuntimeError()
        except RuntimeError:
            logging.exception("just testing")
        self.assertEquals(h.formatted[0],
            "ERROR:root:just testing\nGot a [RuntimeError]")

    def test_config4a_ok(self):
        # A config specifying a custom formatter class.
        self.apply_config(self.config4a)
        logger = logging.getLogger()
        h = logger.handlers[0]
        try:
            raise RuntimeError()
        except RuntimeError:
            logging.exception("just testing")
        self.assertEquals(h.formatted[0],
            "ERROR:root:just testing\nGot a [RuntimeError]")

    def test_config5_ok(self):
        self.test_config1_ok(config=self.config5)

    def test_config6_failure(self):
        self.assertRaises(StandardError, self.apply_config, self.config6)

    def test_config7_ok(self):
        self.apply_config(self.config1)
        logger = logging.getLogger("compiler.parser")
        # Both will output a message
        logger.info(self.next_message())
        logger.error(self.next_message())
        h = logger.handlers[0]
        self.assertTrue(h.matchall([
                            dict(levelname='INFO', message='1'),
                            dict(levelname='ERROR', message='2'),
                        ]))
        self.apply_config(self.config7)
        logger = logging.getLogger("compiler.parser")
        self.assertTrue(logger.disabled)
        logger = logging.getLogger("compiler.lexer")
        # Both will output a message
        h = logger.handlers[0]
        logger.info(self.next_message())
        logger.error(self.next_message())
        self.assertTrue(h.matchall([
                            dict(levelname='INFO', message='3'),
                            dict(levelname='ERROR', message='4'),
                        ]))

    #Same as test_config_7_ok but don't disable old loggers.
    def test_config_8_ok(self):
        self.apply_config(self.config1)
        logger = logging.getLogger("compiler.parser")
        # Both will output a message
        logger.info(self.next_message())
        logger.error(self.next_message())
        h = logger.handlers[0]
        self.assertTrue(h.matchall([
                            dict(levelname='INFO', message='1'),
                            dict(levelname='ERROR', message='2'),
                        ]))
        self.apply_config(self.config8)
        logger = logging.getLogger("compiler.parser")
        self.assertFalse(logger.disabled)
        toplogger = logging.getLogger("compiler")
        # Both will output a message
        logger.info(self.next_message())
        logger.error(self.next_message())
        logger = logging.getLogger("compiler.lexer")
        # Both will output a message
        logger.info(self.next_message())
        logger.error(self.next_message())
        h = toplogger.handlers[0]
        self.assertTrue(h.matchall([
                            dict(levelname='INFO', message='3'),
                            dict(levelname='ERROR', message='4'),
                            dict(levelname='INFO', message='5'),
                            dict(levelname='ERROR', message='6'),
                        ]))

    def test_config_9_ok(self):
        self.apply_config(self.config9)
        logger = logging.getLogger("compiler.parser")
        #Nothing will be output since both handler and logger are set to WARNING
        logger.info(self.next_message())
        h = logger.handlers[0]
        self.assertEqual(0, h.count)
        self.apply_config(self.config9a)
        #Nothing will be output since both handler is still set to WARNING
        logger.info(self.next_message())
        h = logger.handlers[0]
        nhs = named_handlers_supported()
        if nhs:
            self.assertEqual(0, h.count)
        else:
            self.assertEqual(1, h.count)
        self.apply_config(self.config9b)
        #Message should now be output
        logger.info(self.next_message())
        if nhs:
            h = logger.handlers[0]
            self.assertTrue(h.matchall([
                                dict(levelname='INFO', message='3'),
                            ]))
        else:
            self.assertEqual(2, h.count)

    def test_config_10_ok(self):
        self.apply_config(self.config10)
        logger = logging.getLogger("compiler.parser")
        logger.warning(self.next_message())
        logger = logging.getLogger('compiler')
        #Not output, because filtered
        logger.warning(self.next_message())
        logger = logging.getLogger('compiler.lexer')
        #Not output, because filtered
        logger.warning(self.next_message())
        logger = logging.getLogger("compiler.parser.codegen")
        #Output, as not filtered
        logger.error(self.next_message())
        h = logging.getLogger().handlers[0]
        self.assertTrue(h.matchall([
                            dict(levelname='WARNING', message='1'),
                            dict(levelname='ERROR', message='4'),
                        ]))

    def test_config_11_ok(self):
        self.apply_config(self.config11)
        h = logging.getLogger().handlers[0]
        self.assertEqual(h.__module__, 'mytest')
        self.assertEqual(h.__class__.__name__, 'MyTestHandler')
