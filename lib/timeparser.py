import datetime
import re
import math
import logging

# Hack to allow distributing python modules since Splunk doesn't have setuptools
# We create the egg outside of Splunk (with a copy of python2.7 and using Python only modules
# To avoid being platform specific) and then append the egg path and import the module
# If we get a lot of these we'll move the eggs from bin to lib
#
# python-dateutil acquired from http://labix.org/python-dateutil.  BSD Licensed
import sys, os
path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend + '/python_dateutil-1.4.1-py2.7.egg')
import dateutil.parser as dateutil_parser

# If we're inside eventgen, we'll have a global logger, if not set one up
try:
    if logger == None:
        logger = logging.getLogger('timeparser')
except NameError:
    logger = logging.getLogger('timeparser')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
# 5-5-2012 CS  Replacing TimeParser with our own code to remove Splunk dependency
# Based off spec for relative time identifiers at http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/SearchTimeModifiers#How_to_specify_relative_time_modifiers
# If we're not relative, we'll try to parse it as an ISO compliant time
def timeParser(ts='now', timezone=datetime.timedelta(days=1), now=None, utcnow=None):
    if ts == 'now':
        if timezone.days > 0:
            if now == None:
                return datetime.datetime.now()
            else:
                return now()
        else:
            if utcnow  == None:
                return datetime.datetime.now()
            else:
                return utcnow() + timezone
    else:
        if ts[:1] == '+' or ts[:1] == '-':
            if timezone.days > 0:
                if now == None:
                    ret = datetime.datetime.now()
                else:
                    ret = now()
            else:
                if utcnow == None:
                    ret = datetime.datetime.utcnow() + timezone
                else:
                    ret = utcnow() + timezone
            
            unitsre = "(seconds|second|secs|sec|minutes|minute|min|hours|hour|hrs|hr|days|day|weeks|week|w[0-6]|months|month|mon|quarters|quarter|qtrs|qtr|years|year|yrs|yr|s|h|m|d|w|y|w|q)"
            reltimere = "(?i)(?P<plusminus>[+-]*)(?P<num>\d{1,})(?P<unit>"+unitsre+"{1})(([\@](?P<snapunit>"+unitsre+"{1})((?P<snapplusminus>[+-])(?P<snaprelnum>\d+)(?P<snaprelunit>"+unitsre+"{1}))*)*)"
            
            results = re.match(reltimere, ts)
            resultsdict = results.groupdict()
            
            # Handle first part of the time string
            if resultsdict['plusminus'] != None and resultsdict['num'] != None \
                    and resultsdict['unit'] != None:
                ret = timeParserTimeMath(resultsdict['plusminus'], resultsdict['num'], resultsdict['unit'], ret)
                    
                # Now handle snap-to
                if resultsdict['snapunit'] != None:
                    if resultsdict['snapunit'] in ('s', 'sec', 'secs', 'second', 'seconds'):
                        ret = datetime.datetime(ret.year, ret.month, ret.day, ret.hour, \
                                                ret.minute, ret.second, 0)
                    elif resultsdict['snapunit'] in ('m', 'min', 'minute', 'minutes'):
                        ret = datetime.datetime(ret.year, ret.month, ret.day, ret.hour, \
                                                ret.minute, 0, 0)
                    elif resultsdict['snapunit'] in ('h', 'hr', 'hrs', 'hour', 'hours'):
                        ret = datetime.datetime(ret.year, ret.month, ret.day, ret.hour, 0, 0, 0)
                    elif resultsdict['snapunit'] in ('d', 'day', 'days'):
                        ret = datetime.datetime(ret.year, ret.month, ret.day, 0, 0, 0, 0)
                    elif re.match('w[0-6]', resultsdict['snapunit']) != None or \
                            resultsdict['snapunit'] in ('w', 'week', 'weeks'):
                        if resultsdict['snapunit'] in ('w', 'week', 'weeks'):
                            resultsdict['snapunit'] = 'w0'
                        weekdaynum = int(resultsdict['snapunit'][1:2])
                        
                        # Convert python's weekdays to Splunk's
                        retweekday = datetime.date.weekday(ret)
                        if retweekday == 6:
                            retweekday = 0
                        else:
                            retweekday += 1
                            
                        if weekdaynum <= retweekday:
                            ret = ret + datetime.timedelta(days=(weekdaynum - retweekday))
                            ret = datetime.datetime(ret.year, ret.month, ret.day, 0, 0, 0, 0)
                        else:
                            ret = ret - datetime.timedelta(days=7)
                            ret = ret - datetime.timedelta(days=retweekday)
                            ret = ret + datetime.timedelta(days=int(weekdaynum))
                            ret = datetime.datetime(ret.year, ret.month, ret.day, 0, 0, 0, 0)
                    # Normalize out all year/quarter/months to months and do the math on that
                    elif resultsdict['snapunit'] in ('mon', 'month', 'months'):
                        ret = datetime.datetime(ret.year, ret.month, 1, 0, 0, 0, 0)
                    elif resultsdict['snapunit'] in ('q', 'qtr', 'qtrs', 'quarter', 'quarters'):
                        ret = datetime.datetime(ret.year, (math.floor(ret.month / 3) * 3), 1, 0, 0, 0, 0)
                    elif resultsdict['snapunit'] in ('y', 'yr', 'yrs', 'year', 'years'):
                        ret = datetime.datetime(ret.year, 1, 1, 0, 0, 0, 0)
                        
                    if resultsdict['snapplusminus'] != None and resultsdict['snaprelnum'] != None \
                            and resultsdict['snaprelunit'] != None:
                        ret = timeParserTimeMath(resultsdict['snapplusminus'], resultsdict['snaprelnum'], 
                                                resultsdict['snaprelunit'], ret)
                return ret
            
            else:
                raise ValueError('Cannot parse relative time string for %s' %(ts))
        else:
            # The spec says we must be a ISO8601 time.  This parser should be able to handle 
            # more date formats though, so we can be liberal in what we accept

            return dateutil_parser.parse(ts)
            #except ValueError:
            #    raise ValueError("Cannot parse date/time for %s" % (ts))

def timeParserTimeMath(plusminus, num, unit, ret):
    try:
        num = int(num)
        td = None
        if unit in ('s', 'sec', 'secs', 'second', 'seconds'):
            td = datetime.timedelta(seconds=int(num))
        elif unit in ('m', 'min', 'minute', 'minutes'):
            td = datetime.timedelta(minutes=int(num))
        elif unit in ('h', 'hr', 'hrs', 'hour', 'hours'):
            td = datetime.timedelta(hours=int(num))
        elif unit in ('d', 'day', 'days'):
            td = datetime.timedelta(days=int(num))
        elif unit in ('w', 'week', 'weeks'):
            td = datetime.timedelta(days=(int(num)*7))
        elif re.match('w[0-6]', unit) != None:
            logger.error('Day of week is only available in snap-to.  Time string: %s' % (ts))
            return False
        # Normalize out all year/quarter/months to months and do the math on that
        elif unit in ('mon', 'month', 'months') or \
                    unit in ('q', 'qtr', 'qtrs', 'quarter', 'quarters') or \
                    unit in ('y', 'yr', 'yrs', 'year', 'years'):
            if unit in ('q', 'qtr', 'qtrs', 'quarter', 'quarters'):
                num *= 3
            elif unit in ('y', 'yr', 'yrs', 'year', 'years'):
                num *= 12
        
            monthnum = int(num) * -1 if plusminus == '-' else int(num)
            if abs(monthnum) / 12 > 0:
                yearnum = int(math.floor(abs(monthnum)/12) * -1 if plusminus == '-' else int(math.floor(abs(monthnum)/12)))
                monthnum = int((abs(monthnum) % 12) * -1 if plusminus == '-' else int((abs(monthnum)%12)))
                ret = datetime.datetime(ret.year + yearnum, ret.month + monthnum, ret.day, ret.hour,
                                        ret.minute, ret.second, ret.microsecond)
            elif monthnum > 0:
                if ret.month + monthnum > 12:
                    ret = datetime.datetime(ret.year+1, ((ret.month+monthnum)%12),
                                            ret.day, ret.hour, ret.minute, ret.second, ret.microsecond)
                else:
                    ret = datetime.datetime(ret.year, ret.month+monthnum, ret.day,
                                            ret.hour, ret.minute, ret.second, ret.microsecond)
            elif monthnum <= 0:
                if ret.month + monthnum <= 0:
                    ret = datetime.datetime(ret.year-1, (12-abs(ret.month+monthnum)),
                                            ret.day, ret.hour, ret.minute, ret.second, ret.microsecond)
                else:
                    ret = datetime.datetime(ret.year, ret.month+monthnum, ret.day,
                                            ret.hour, ret.minute, ret.second, ret.microsecond)

    except ValueError:
        logger.error('Cannot parse relative time string')
        import traceback
        stack =  traceback.format_exc()
        logger.debug('%s', stack)
        return False
        
    if td != None:
        if plusminus == '-':
            td = td * -1
        ret = ret + td
        
    # Always chop microseconds to maintain compatibility with Splunk's parser
    ret = datetime.datetime(ret.year, ret.month, ret.day, ret.hour, ret.minute, ret.second)
    
    return ret
    
## Converts Time Delta object to number of seconds in delta
def timeDelta2secs(timeDiff):
    deltaSecs = (timeDiff.microseconds + (timeDiff.seconds + timeDiff.days * 24 * 3600) * 10**6) / 10**6
    return int(deltaSecs)