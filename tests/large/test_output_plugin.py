import os
import subprocess
import time
from utils.splunk_search_util import get_session_key, preprocess_search, run_search, get_search_response


def test_plugin_devnull(eventgen_test_helper):
    """Test output plugin devnull"""
    events = eventgen_test_helper("eventgen_plugin_devnull.conf").get_events()
    # assert the events size is 0
    assert len(events) == 0


def test_plugin_file(eventgen_test_helper):
    """Test output plugin file"""
    events = eventgen_test_helper("eventgen_plugin_file.conf").get_events()
    # assert the events size is 12 when end = 1
    assert len(events) == 12


def test_plugin_httpevent(eventgen_test_helper):
    """Test output plugin httpevent"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    docker_compose_file = os.path.join(base_dir, "provision/docker-compose.yml")
    up_cmd = ["docker-compose", "-f", docker_compose_file, "up"]
    subprocess.Popen(up_cmd, shell=True, stdout=subprocess.PIPE)

    time.sleep(30)
    # https://github.com/docker/compose/issues/5696
    provision_cmd = ["docker-compose -f " + docker_compose_file +
                     " exec -T splunk sh -c 'cd /opt/splunk;./provision.sh;/opt/splunk/bin/splunk restart'"]

    try:
        subprocess.check_output(provision_cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))

    time.sleep(30)
    eventgen_test_helper("eventgen_plugin_httpevent.conf").get_events()

    session_key = get_session_key()
    search_job_id = run_search(session_key, preprocess_search('index=main'))
    events = get_search_response(session_key, search_job_id)
    assert len(events) == 12
    down_cmd = ["docker-compose", "-f", docker_compose_file, "down"]
    subprocess.Popen(down_cmd, shell=True, stdout=subprocess.PIPE)
