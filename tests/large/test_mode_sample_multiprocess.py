import re
from datetime import datetime


def test_mode_sample(eventgen_test_helper):
    """Test sample mode with end=1 in multiprocess mode"""
    current_datetime = datetime.now()
    helper = eventgen_test_helper(
        "eventgen_sample_multiprocess.conf", timeout=None, mode="process"
    )
    events = helper.get_events()
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
