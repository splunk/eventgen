import os

import structlog
import logging.config

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
DEFAULT_LOGGING_LEVEL = "DEBUG"

structlog.configure(
    processors=[
        structlog.processors.UnicodeEncoder(encoding='utf-8', errors='backslashreplace'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

pre_chain = [
    # Add the log level and a timestamp to the event_dict if the log entry
    # is not from structlog.
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt='iso'),
]

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'default': {
            'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json_struct': {
            "()": structlog.stdlib.ProcessorFormatter,
            "foreign_pre_chain": pre_chain,
            "processor": structlog.processors.JSONRenderer(sort_keys=True),
        }
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
            'formatter': 'json_struct',
            'filters': [],
            'maxBytes': 1024 * 1024,
            'filename': os.path.join(LOG_DIR, 'eventgen-metrics.log')
        },
        'eventgen_server': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': DEFAULT_LOGGING_LEVEL,
            'formatter': 'json_struct',
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

logger = structlog.get_logger('eventgen')
controller_logger = structlog.get_logger('eventgen_controller')
server_logger = structlog.get_logger('eventgen_server')
metrics_logger = structlog.get_logger('eventgen_metrics')
