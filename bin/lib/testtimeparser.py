## True division
from __future__ import division

# Hack to allow distributing python modules since Splunk doesn't have setuptools
# We create the egg outside of Splunk (with a copy of python2.7 and using Python only modules
# To avoid being platform specific) and then append the egg path and import the module
# If we get a lot of these we'll move the eggs from bin to lib

# python-dateutil acquired from http://labix.org/python-dateutil.  BSD Licensed

import sys, os
if 'SPLUNK_HOME' not in os.environ and 'SPLUNK_DB' not in os.environ:
    os.environ['SPLUNK_HOME'] = '/Applications/splunk'
    os.environ['SPLUNK_DB'] = '/Applications/splunk/var/lib/db'
if 'SPLUNK_HOME' in os.environ:
    path_prepend = os.environ['SPLUNK_HOME']+'/etc/apps/SA-Eventgen/bin/lib'
else:
    path_prepend = './lib'

sys.path.append(path_prepend + '/python_dateutil-1.4.1-py2.7.egg')
sys.path.append(path_prepend)
sys.path.insert(1, '/Applications/splunk/lib/python2.7/site-packages')

import datetime
import httplib2
import logging
import random
import re
import shutil
import splunk.auth as auth
import splunk.bundle as bundle
import splunk.entity as entity
import splunk.rest as rest
import splunk.util as util
import threading
import time
import lxml.etree as et
import urllib

# Imports added by CSharp
import dateutil
import math
from timeparser import timeParser as timeParserNew

TEST_STRINGS = [
    '-12h@h',
    '+1m@day',
    '+1h@m',
    '-1day@month',
    '+1h',
    '-1sec',
    '-30seconds',
    '-1d@w0',
    '-1m@w1',
    '-1d@w5',
    '-1m@w0',
    '-1m@w6',
    '+3d@w0',
    '+12d@w6',
    '-1qtr@w0+12h',
    '+12h@h-1h',
    '+3qtrs@yr+3days',
    '-12years@year-1min',
    '-3quarters@month-5days',
    '+4quarters@day-12seconds',
    '+1yr@day',
    '+13months@second-17secs',
    '2009-01-23T17:42:16.009'
]

## Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('eventgen')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)

    # file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/eventgen.log', maxBytes=25000000, backupCount=5)
    file_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

# ## Parses time strings using /search/timeparser endpoint
def timeParserOld(ts='now', sessionKey=None):
    getargs = {}
    getargs['time'] = ts
    
    tsStatus, tsResp = rest.simpleRequest('/search/timeparser', sessionKey=sessionKey, getargs=getargs)
                
    root = et.fromstring(tsResp)    
        
    ts = root.find('dict/key')
    if ts != None:
        return util.parseISO(ts.text, strict=True)
    
    else:
        logger.error("Could not retrieve timestamp for specifier '%s' from /search/timeparser" % (ts) )
        return False
        
    
if __name__ == '__main__':
    
    # Login to Splunk
    sessionKey = auth.getSessionKey('admin', 'rUstY3')
    for teststr in TEST_STRINGS:
        tpold = timeParserOld(teststr, sessionKey)
        tpnew = timeParserNew(teststr)
        tpold = datetime.datetime(tpold.year, tpold.month, tpold.day, tpold.hour, 
                                    tpold.minute, tpold.second, tpold.microsecond)
        if tpold != tpnew:
            print "%s\t%s\t%s" % (teststr, tpold, tpnew)
        #print "%s.%s" % (datetime.datetime.strftime("%Y-%m-%dT%H:%M:%S", testtime), str(testtime.microsecond)[:3])