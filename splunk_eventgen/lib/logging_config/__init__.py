import os
import logging.config

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
DEFAULT_LOGGING_LEVEL = "DEBUG"

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'default': {
            'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },

    'filters': {
    },

    'handlers': {
        'console': {
            'level': DEFAULT_LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'eventgen_main': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': DEFAULT_LOGGING_LEVEL,
            'formatter': 'default',
            'filters': [],
            'maxBytes': 1024 * 1024,
            'filename': os.path.join(LOG_DIR, 'eventgen-main.log')
        },
        'eventgen_controller': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': DEFAULT_LOGGING_LEVEL,
            'formatter': 'default',
            'filters': [],
            'maxBytes': 1024 * 1024,
            'filename': os.path.join(LOG_DIR, 'eventgen-controller.log')
        },
        'eventgen_httpevent': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': DEFAULT_LOGGING_LEVEL,
            'formatter': 'default',
            'filters': [],
            'maxBytes': 1024 * 1024,
            'filename': os.path.join(LOG_DIR, 'eventgen-httpevent.log')
        },
        'eventgen_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'default',
            'filters': [],
            'maxBytes': 1024 * 1024,
            'filename': os.path.join(LOG_DIR, 'eventgen-error.log')
        },
        'eventgen_metrics': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': DEFAULT_LOGGING_LEVEL,
            'formatter': 'default',
            'filters': [],
            'maxBytes': 1024 * 1024,
            'filename': os.path.join(LOG_DIR, 'eventgen-metrics.log')
        },
        'eventgen_server': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': DEFAULT_LOGGING_LEVEL,
            'formatter': 'default',
            'filters': [],
            'maxBytes': 1024 * 1024,
            'filename': os.path.join(LOG_DIR, 'eventgen-server.log')
        },
    },

    'loggers': {
        'eventgen': {
            'handlers': ['console', 'eventgen_main'],
            'level': DEFAULT_LOGGING_LEVEL,
            'propagate': False
        },
        'eventgen_metrics': {
            'handlers': ['eventgen_metrics'],
            'level': DEFAULT_LOGGING_LEVEL,
            'propagate': False
        },
        'eventgen_server': {
            'handlers': ['eventgen_server', 'console'],
            'level': DEFAULT_LOGGING_LEVEL,
            'propagate': False
        },
        'eventgen_controller': {
            'handlers': ['eventgen_controller', 'console'],
            'level': DEFAULT_LOGGING_LEVEL,
            'propagate': False
        },
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('eventgen')
controller_logger = logging.getLogger('eventgen_controller')
server_logger = logging.getLogger('eventgen_server')
metrics_logger = logging.getLogger('eventgen_metrics')
