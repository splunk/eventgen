import datetime

import pytest

from splunk_eventgen.lib import timeparser

time_delta_test_params = [(datetime.timedelta(days=1), 86400),
                          (datetime.timedelta(days=1, hours=3, minutes=15, seconds=32), 98132),
                          (datetime.timedelta(hours=1, minutes=10), 4200), (datetime.timedelta(hours=-1), -3600),
                          (None, 0)]


@pytest.mark.parametrize('delta,expect', time_delta_test_params)
def test_time_delta_2_second(delta, expect):
    ''' Test timeDelta2secs function, convert time delta object to seconds
    Normal cases:
    case 1: time delta is 1 day, expect is 86400
    case 2: time delta is 1 day 3 hour 15 minutes 32 seconds, expect is 98132
    case 3: time delta is less than 1 day, only 1 hour 10 minutes, expect is 4200
    case 4: time delta is 1 hour ago, expect is -3600

    Corner cases:
    case 1: delta object is None -- invalid input, expect is <TBD>
    '''
    assert timeparser.timeDelta2secs(delta) == expect


def check_datetime_equal(d1, d2):
    assert d1.year == d2.year
    assert d1.month == d2.month
    assert d1.day == d2.day
    assert d1.hour == d2.hour
    assert d1.minute == d2.minute
    assert d1.second == d2.second


parse_time_math_params = [('+', '100', 's', datetime.datetime(2019, 3, 8, 4, 10, 20),
                           datetime.datetime(2019, 3, 8, 4, 12, 0)),
                          ('-', '20', 'm', datetime.datetime(2019, 3, 8, 4, 10, 20),
                           datetime.datetime(2017, 7, 8, 4, 10, 20)),
                          ('', '3', 'w', datetime.datetime(2019, 3, 8, 4, 10, 20),
                           datetime.datetime(2019, 3, 29, 4, 10, 20)),
                          ('', '0', 's', datetime.datetime(2019, 3, 8, 4, 10, 20),
                           datetime.datetime(2019, 3, 8, 4, 10, 20)),
                          ('', '123', '', datetime.datetime(2019, 3, 8, 4, 10, 20),
                           datetime.datetime(2019, 3, 8, 4, 10, 20))]


@pytest.mark.parametrize('plusminus,num,unit,ret,expect', parse_time_math_params)
def test_time_parser_time_math(plusminus, num, unit, ret, expect):
    '''
    test timeParserTimeMath function, parse the time modifier
    Normal Case:
    Case 1: input "+100s" -- the parser should translate it as 100 seconds later.
    Case 2: input "-20m" -- the parser should handle the month larger than 12 and translate as 20 months ago
    Case 3: input '3w' -- the parser should translate as 21 days later.

    Corner Cases:
    Case 1: input "0s" -- the time parser should return now
    Case 2: input "123" -- unit is the empty string, behavior <TBD>
    '''
    check_datetime_equal(timeparser.timeParserTimeMath(plusminus, num, unichr, ret), expect)


def mock_now():
    return datetime.datetime(2019, 3, 10, 13, 20, 15)


def mock_utc_now():
    return datetime.datetime(2019, 3, 10, 5, 20, 15)


timeparser_params = [
    ('now', datetime.timedelta(days=1), datetime.datetime(2019, 3, 10, 13, 20, 15)),
    ('now', datetime.timedelta(days=0), datetime.datetime(2019, 3, 10, 5, 20, 15)),
    ('now', datetime.timedelta(hours=2), datetime.datetime(2019, 3, 10, 7, 20, 15)),
    ('now', datetime.timedelta(hours=-3), datetime.datetime(2019, 3, 10, 2, 20, 15)),
    ('-7d', datetime.timedelta(days=1), datetime.datetime(2019, 3, 3, 13, 20, 15)),
    ('-0mon@mon', datetime.timedelta(days=1), datetime.datetime(2019, 3, 1, 0, 0, 0)),
    ('-1mon@mon', datetime.timedelta(days=1), datetime.datetime(2019, 2, 1, 0, 0, 0)),
    ('-3d@d', datetime.timedelta(days=1), datetime.datetime(2019, 3, 7, 0, 0, 0)),
    ('+5d', datetime.timedelta(days=1), datetime.datetime(2019, 3, 15, 13, 20, 15)),
    ('', datetime.timedelta(days=1), datetime.datetime(2019, 3, 10, 13, 20, 15)), ]


@pytest.mark.parametrize('ts,tz,expect', timeparser_params)
def test_timeparser(ts, tz, expect):
    '''
    test timeParser function, parse splunk time modifier
    Normal Cases:
    Case 1: get now timestamp
    Case 2: get utc now timestamp
    Case 3: get utc+2 timezone timestamp
    Case 4: get utc-2 timezone timestamp
    Case 5: get the 7 days ago timestamp
    Case 5: get the beginning of this month. check the snap to month
    Case 6: get the beginning of last month. check the snap to last month
    Case 7: get 3 days ago, snap to day
    Case 8: get 5 days later

    Corner Cases:
    Case 1: empty string as input. behavior <TBD>
    '''
    r = timeparser.timeParser(ts, tz, mock_now, mock_utc_now)
    check_datetime_equal(r, expect)
