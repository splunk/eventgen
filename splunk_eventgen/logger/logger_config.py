controller_logger_config = {
    'version': 1,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
        },
        'main': {
            'class': 'logging.FileHandler',
            'filename': 'eventgen-controller-main.log',
            'mode': 'w',
            'formatter': 'detailed',
        }
    },
    'loggers': {
        'eventgen_controller': {
            'handlers': ['main']
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'main']
    },
}

listener_logger_config = {
    'version': 1,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'eventgen_main.log',
            'mode': 'w',
            'formatter': 'detailed',
        },
        'eventgenfile': {
            'class': 'logging.FileHandler',
            'filename': 'eventgen-process.log',
            'mode': 'w',
            'formatter': 'detailed',
        },
        'eventgen_listener_file': {
            'class': 'logging.FileHandler',
            'filename': 'eventgen-listener-process.log',
            'mode': 'w',
            'formatter': 'detailed',
        },
        'errors': {
            'class': 'logging.FileHandler',
            'filename': 'eventgen-errors.log',
            'mode': 'w',
            'level': 'ERROR',
            'formatter': 'detailed',
        }
    },
    'loggers': {
        'eventgen': {
            'handlers': ['eventgenfile']
        },
        'eventgen_listener': {
            'handlers': ['eventgen_listener_file']
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'errors', 'file']
    },
}