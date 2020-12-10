from pytest import mark


def calculate_perdayvolume(events, runtime, interval=60):
    # Calculate expected data volume output (GB) if run for 24 hours
    # Get the integer # of intervals, data is only generated on completion of an interval
    num_intervals = runtime // interval
    event_volume = sum([len(event) for event in events])
    total_volume = event_volume / 1024 / 1024 / 1024 * 60 * 24
    perdayvolume = total_volume / num_intervals
    return perdayvolume


@mark.parametrize(
    ("conf_filename", "execution_timeout", "perdayvolume"),
    [
        ("eventgen_perdayvolume.conf", 300, 1),
        ("eventgen_perdayvolume_small_token.conf", 300, 1),
        ("eventgen_perdayvolume_large_token.conf", 300, 1),
    ],
)
def test_perdayvolume(
    eventgen_test_helper, conf_filename, execution_timeout, perdayvolume
):
    # Test accuracy of small volume target with no token replacements
    # TODO: using outputMode=file for now, test helper unable to collect all generated events w/ outputMode=stdout
    events = eventgen_test_helper(conf_filename, execution_timeout).get_events()
    assert (
        0.98 < (calculate_perdayvolume(events, execution_timeout) / perdayvolume) < 1.02
    )
