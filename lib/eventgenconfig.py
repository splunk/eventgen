from ConfigParser import ConfigParser
import os
import re
import __main__

## Validations
validSettings = ['spoolDir', 'spoolFile', 'breaker', 'interval', 'count', 'earliest', 'latest', 
                'eai:acl', 'hourOfDayRate', 'dayOfWeekRate', 'randomizeCount', 'randomizeEvents',
                'outputMode', 'file', 'fileMaxBytes', 'fileBackupFiles', 'splunkHost', 'splunkPort',
                'splunkMethod', 'splunkUser', 'splunkPass', 'index', 'source', 'sourcetype']
validTokenTypes = {'token': 0, 'replacementType': 1, 'replacement': 2}

def configParser():
    # Setup defaults.  Copied from SA-Eventgen stock eventgen.conf
    conf = ConfigParser()
    parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__main__.__file__)))
    grandparentdir = os.path.dirname(parentdir)
    currentdir = os.getcwd()
    
    # If we're running standalone (and thusly using configParser)
    # only pick up eventgen-standalone.conf.
    conffiles = [os.path.join(parentdir, 'lib', 'eventgen_defaults'),
                os.path.join(parentdir, 'default', 'eventgen-standalone.conf'),
                os.path.join(parentdir, 'local', 'eventgen-standalone.conf')]
    # If we don't see SA-Eventgen, then pick up eventgen.conf as well
    if not os.path.exists(os.path.join(grandparentdir, 'SA-Eventgen')) \
            and not os.path.exists(os.path.join(grandparentdir, 'eventgen')):
        conffiles.append(os.path.join(parentdir, 'default', 'eventgen.conf'))
        conffiles.append(os.path.join(parentdir, 'local', 'eventgen.conf'))
    conf.read(conffiles)
                
    sections = conf.sections()
    ret = { }
    orig = { }
    for section in sections:
        orig[section] = dict(conf.items(section))
        ret[section] = { }
        # For compatibility with Splunk's configs, need to add the app name to an eai:acl key
        ret[section]['eai:acl'] = { 'app': parentdir.split(os.sep)[-1] }
        for item in orig[section]:
            results = re.match('(token\.\d+)\.(\w+)', item)
            if results != None:
                groups = results.groups()
                try:
                    if type(ret[section][groups[0]]) != list:
                        ret[section][groups[0]] = [ None, None, None ]
                except KeyError:
                     ret[section][groups[0]] = [ None, None, None ]
                try:
                    ret[section][groups[0]][dict((k.lower(), v) for (k,v) in validTokenTypes.items())[groups[1].lower()]] = orig[section][item]
                except:
                    pass
            else:
                if item.lower() in [x.lower() for x in validSettings]:
                    newitem = validSettings[[x.lower() for x in validSettings].index(item.lower())]
                ret[section][newitem] = orig[section][item]
                    
    # Second pass to do validations and clean up if we don't match
    for section in sections:
        badKeys = [ ]
        for item in ret[section]:
            # If we're not a valid setting and not a token, remove us
            if item.find('token') < 0 and not matchSetting(item):
                badKeys.append(item)
                    
        for item in badKeys:
            del ret[section][item]
                
    return ret
    
def matchSetting(match):
    matched = False
    for setting in validSettings:
        if setting.lower() == match.lower():
            matched = True
    return matched
                