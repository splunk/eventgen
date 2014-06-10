'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import os, sys
import logging

#Setup logging for this test run
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-5s  %(message)s',
                    filename='SA-Eventgen-test.log',
                    filemode='w')

logger = logging.getLogger('SA-Eventgen-python-fw')
logger.info('Logging setup completed.')






