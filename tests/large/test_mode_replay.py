import re
import time
from datetime import datetime, timedelta


def test_mode_replay(eventgen_test_helper):
    """Test normal replay mode settings"""
    events = eventgen_test_helper("eventgen_replay.conf").get_events()
    # assert the event length is the same as sample file size
    assert len(events) == 12
    pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    for event in events:
        # assert that integer token is replaced
        assert "@@integer" not in event
        result = pattern.match(event)
        assert result is not None


def test_mode_replay_end_1(eventgen_test_helper):
    """Test normal replay mode with end = 2 which will replay the sample twice and exit"""
    events = eventgen_test_helper("eventgen_replay_end_1.conf").get_events()
    # assert the event length is twice of the events in the sample file
    assert len(events) == 24


def test_mode_replay_end_2(eventgen_test_helper):
    """Test normal replay mode with end = -1 which will replay the sample forever"""
    helper = eventgen_test_helper("eventgen_replay_end_2.conf")
    time.sleep(60)
    assert helper.is_alive()


def test_mode_replay_backfill(eventgen_test_helper):
    """Test normal replay mode with backfill = -5s which should be ignore since backfill < interval"""
    events = eventgen_test_helper("eventgen_replay_backfill.conf").get_events()
    # assert the events length is twice of the events in the sample file
    assert len(events) == 24


def test_mode_replay_backfill_greater_interval(eventgen_test_helper):
    """Test normal replay mode with backfill = -120s"""
    current_datetime = datetime.now()
    events = eventgen_test_helper(
        "eventgen_replay_backfill_greater_interval.conf"
    ).get_events()
    # assert the events length is twice of the events in the sample file
    assert len(events) == 24
    pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    for event in events:
        result = pattern.match(event)
        assert result is not None
        event_datetime = datetime.strptime(result.group(), "%Y-%m-%d %H:%M:%S")
        assert event_datetime < current_datetime


def test_mode_replay_tutorial1(eventgen_test_helper):
    """Test the replay mode with csv for sample file sample.tutorial1.csv"""
    events = eventgen_test_helper("eventgen_tutorial1.conf").get_events()
    assert len(events) == 2019


def test_mode_replay_timemultiple(eventgen_test_helper):
    """Test normal replay mode with timeMultiple = 0.5 which will replay the sample with half time interval"""
    current_datetime = datetime.now()
    events = eventgen_test_helper("eventgen_replay_timeMultiple.conf").get_events()

    pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    for event in events:
        result = pattern.match(event)
        assert result is not None
        event_datetime = datetime.strptime(result.group(), "%Y-%m-%d %H:%M:%S")
        delter_seconds = (event_datetime - current_datetime).total_seconds()
        # assert the event time is after (now - earliest) time
        assert delter_seconds < 14


def test_mode_replay_csv(eventgen_test_helper):
    """Test normal replay mode with sampletype = csv which will get _raw row from the sample"""
    events = eventgen_test_helper("eventgen_replay_csv.conf").get_events()
    # assert the events equals to the sample csv file
    assert len(events) == 10


def test_mode_replay_with_timezone(eventgen_test_helper):
    """Test normal replay mode with sampletype = csv which will get _raw row from the sample"""
    events = eventgen_test_helper("eventgen_replay_csv_with_tz.conf").get_events()
    # assert the events equals to the sample csv file
    assert len(events) == 4
    now_ts = datetime.utcnow() + timedelta(hours=-1)
    for event in events:
        event_ts = datetime.strptime(event.split(" ")[0], "%Y-%m-%dT%H:%M:%S,%f")
        d = now_ts - event_ts
        assert d.seconds < 60, "timestamp with timezone check fails."
