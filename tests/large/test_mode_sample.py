from datetime import datetime
import re


def test_mode_sample(eventgen_test_helper):
    """Test normal sample mode with sampletype = raw"""
    current_datetime = datetime.now()
    events = eventgen_test_helper("eventgen_sample.conf").get_events()
    # assert the event length is the same as sample file size when end = 1
    assert len(events) == 12
    pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    for event in events:
        # assert that integer token is replaced
        assert "@@integer" not in event
        result = pattern.match(event)
        assert result is not None
        event_datetime = datetime.strptime(result.group(), "%Y-%m-%d %H:%M:%S")
        delter_seconds = (event_datetime - current_datetime).total_seconds()
        # assert the event time is after (now - earliest) time
        assert delter_seconds > -20


def test_mode_sample_csv(eventgen_test_helper):
    """Test normal sample mode with sampletype = csv"""
    events = eventgen_test_helper("eventgen_sample_csv.conf").get_events()
    # assert the event length is the same as sample file size when end = 1
    assert len(events) == 10


def test_mode_sample_interval(eventgen_test_helper):
    """Test normal sample mode with interval = 10s"""
    events = eventgen_test_helper("eventgen_sample_interval.conf", timeout=30).get_events()
    # assert the total events count is 12 * 3
    assert len(events) == 36


def test_mode_sample_end(eventgen_test_helper):
    """Test normal sample mode with end = 1 and outputMode = file which will generate from the sample once"""
    helper = eventgen_test_helper("eventgen_sample_end.conf")
    events = helper.get_events()
    # assert the event length is the same as sample file size when end = 1
    assert len(events) == 12


def test_mode_sample_backfill(eventgen_test_helper):
    """Test normal sample mode with end = 1 and backfill = -15s which will generate from the sample once"""
    current_datetime = datetime.now()
    helper = eventgen_test_helper("eventgen_sample_backfill.conf")
    events = helper.get_events()
    pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    for event in events:
        result = pattern.match(event)
        assert result is not None
        event_datetime = datetime.strptime(result.group(), "%Y-%m-%d %H:%M:%S")
        delter_seconds = (event_datetime - current_datetime).total_seconds()
        # assert the event time is after (now - backfill) time
        assert delter_seconds > -15


def test_mode_sample_breaker(eventgen_test_helper):
    r"""Test sample mode with end = 1, count = 3 and breaker = ^\d{14}\.\d{6}"""
    helper = eventgen_test_helper("eventgen_sample_breaker.conf")
    events = helper.get_events()
    assert len(events) == 3


def test_mode_sample_earliest(eventgen_test_helper):
    """Test sample mode with earliest = -15s"""
    current_datetime = datetime.now()
    helper = eventgen_test_helper("eventgen_sample_earliest.conf")
    events = helper.get_events()
    pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    for event in events:
        result = pattern.match(event)
        assert result is not None
        event_datetime = datetime.strptime(result.group(), "%Y-%m-%d %H:%M:%S")
        delter_seconds = (event_datetime - current_datetime).total_seconds()
        # assert the event time is after (now - earliest) + 1 time, plus 1 to make it less flaky
        assert delter_seconds > -16


def test_mode_sample_latest(eventgen_test_helper):
    """Test sample mode with latest = +15s"""
    current_datetime = datetime.now()
    helper = eventgen_test_helper("eventgen_sample_latest.conf")
    events = helper.get_events()
    pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    for event in events:
        result = pattern.match(event)
        assert result is not None
        event_datetime = datetime.strptime(result.group(), "%Y-%m-%d %H:%M:%S")
        delter_seconds = (event_datetime - current_datetime).total_seconds()
        # assert the event time is after (now - earliest) time
        assert delter_seconds < 16


def test_mode_sample_count(eventgen_test_helper):
    """Test sample mode with count = 5 which will output 5 events"""
    helper = eventgen_test_helper("eventgen_sample_count.conf")
    events = helper.get_events()
    assert len(events) == 5
