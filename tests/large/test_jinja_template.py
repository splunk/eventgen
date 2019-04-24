import re
import datetime

ts_regex = '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}'
ts_format = '%Y-%m-%dT%H:%M:%S'


def test_jinja_template_simple(eventgen_test_helper):
    """Test simple jinja template """
    current_datetime = datetime.datetime.now()
    events = eventgen_test_helper('eventgen_jinja_simple.conf').get_events()
    # assert the event length is the same as sample file size
    assert len(events) == 10
    pattern = re.compile("^({}) test jinja template generator, seq: (\\d+)/10".format(ts_regex))
    loop = 1
    for event in events:
        # assert that integer token is replaced
        result = pattern.match(event)
        assert result is not None, 'fail to check event ```{}```'.format(event)
        event_datetime = datetime.datetime.strptime(result.group(1), ts_format)
        delta_seconds = (event_datetime - current_datetime).total_seconds()
        # assert the event time is after (now - earliest) time
        assert delta_seconds >= -3 and delta_seconds < 3, 'fail to check event ```{}```'.format(event)
        assert loop == int(result.group(2)), 'fail to check event ```{}```'.format(event)
        loop += 1


def test_jinja_template_dir_conf(eventgen_test_helper):
    """Test customized jinja template dir"""
    current_datetime = datetime.datetime.now()
    events = eventgen_test_helper('eventgen_jinja_tmpl_dir.conf').get_events()
    # assert the event length is the same as sample file size
    assert len(events) == 10
    pattern = re.compile("^({}) test jinja template directory conf, seq: (\\d+)/10".format(ts_regex))
    loop = 1
    for event in events:
        # assert that integer token is replaced
        result = pattern.match(event)
        assert result is not None
        event_datetime = datetime.datetime.strptime(result.group(1), ts_format)
        delta_seconds = (event_datetime - current_datetime).total_seconds()
        # assert the event time is after (now - earliest) time
        assert delta_seconds >= -3 and delta_seconds < 3
        assert loop == int(result.group(2))
        loop += 1


def test_jinja_template_advance(eventgen_test_helper):
    """Test advanced jinja template var feature"""
    events = eventgen_test_helper('eventgen_jinja_advance.conf').get_events()
    # print events
    # events are the stdout lines, it is not the splunk indexed events
    # splunk may index multiline event
    assert len(events) == 27
    # because we use time slice method to mock the time, it should be static values
    ts_map = {
        1: '1970-01-01T08:24:16',
        2: '1970-01-01T08:27:58',
        3: '1970-01-01T08:31:40',
    }

    firstline_pattern = re.compile(
        "^({}) \[admin\] test jinja template advance, switch=True, seq: (\\d+)/3".format(ts_regex))
    secondline_pattern = re.compile("^    this is the 2nd line, seq:(\\d+)/3")
    thirdline_pattern = re.compile("^this is the 3rd line, seq:(\\d+)/3")
    for i in range(3):
        # because end = 3
        for j in range(3):
            # because large_number=3
            for l in range(3):
                idx = i * 9 + j * 3 + l
                event = events[idx]
                assert event, 'event is empty!'
                # assert that integer token is replaced
                if l == 0:
                    result1 = firstline_pattern.match(event)
                    assert result1 is not None
                    idx1 = int(result1.group(2))
                    assert (j + 1 == idx1), 'event={}'.format(event)
                    assert (ts_map[idx1] == result1.group(1)), 'event={}'.format(event)
                elif l == 1:
                    result2 = secondline_pattern.match(event)
                    assert result2 is not None
                    idx2 = int(result2.group(1))
                    assert (j + 1 == idx2), 'event={}'.format(event)
                elif l == 2:
                    result3 = thirdline_pattern.match(event)
                    assert result3 is not None
                    idx3 = int(result3.group(1))
                    assert (j + 1 == idx3), 'event={}'.format(event)
                else:
                    assert False, 'Invalid loop when check integer token replacement. i={} j={} l={} idx={}'.format(i, j, l, idx)
