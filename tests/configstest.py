## True division
from __future__ import division
from ConfigParser import ConfigParser

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
    path_prepend = os.environ['SPLUNK_HOME']+'/etc/apps/SA-Eventgen/lib'
else:
    path_prepend = '../lib'

sys.path.append(path_prepend + '/python_dateutil-1.4.1-py2.7.egg')
sys.path.append(path_prepend)
sys.path.insert(1, '/Applications/splunk/lib/python2.7/site-packages')

import splunk.auth as auth
import splunk.bundle as bundle
import splunk.entity as entity
import splunk.rest as rest
import splunk.util as util

from pprint import pprint

if __name__ == '__main__':
    
    # Login to Splunk
    sessionKey = auth.getSessionKey('admin', 'rUstY3')
    confDict = entity.getEntities('configs/eventgen', count=-1, sessionKey=sessionKey)
    
    print 'Legacy'
    pprint(dict(confDict))
    pprint(dict(confDict['sample.businessevent']))
    
    # print 'ConfigParser'
    # conf = ConfigParser()
    # conf.read([os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'oidemo', 'default', 'eventgen.conf')])
    # pprint(dict(conf.items('sample.businessevent')))
    
    print 'New'
    from eventgenconfig import configParser
    conf = configParser()
    # pprint(conf)
    pprint(conf['sample.businessevent'])