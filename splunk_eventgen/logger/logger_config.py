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
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'main']
    },
}

