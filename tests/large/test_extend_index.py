from utils.splunk_search_util import (
    get_session_key,
    preprocess_search,
    run_search,
    get_search_response,
)


def test_extend_index(eventgen_test_helper):
    """Test extendIndexes config"""
    eventgen_test_helper("eventgen_extend_index.conf").get_events()

    session_key = get_session_key()
    search_job_id = run_search(
        session_key, preprocess_search("index=main sourcetype=cisco")
    )
    test_index_search_job_id = run_search(
        session_key, preprocess_search("index=test_*")
    )
    main_events = get_search_response(session_key, search_job_id)
    test_index_events = get_search_response(session_key, test_index_search_job_id)
    assert len(main_events) == 12
    assert len(test_index_events) == 12
