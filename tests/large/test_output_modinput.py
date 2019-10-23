import subprocess
import os
import time
import datetime
import re
from lxml import etree

file_dir = os.path.abspath(os.path.dirname(__file__))


def now_seconds():
    return round(time.time(), 0)


def test_output_plugin_modinput():
    """
    Test modinput output plugin
    """
    conf_file = os.path.join(file_dir, 'conf', 'eventgen_output_modinput.conf')
    child = subprocess.Popen(['splunk_eventgen', 'generate', conf_file], stdout=subprocess.PIPE)
    all_events = child.communicate()[0].decode('UTF-8')

    parts = all_events.split('<event>')
    events = ['<event>' + p for p in parts if p.strip() != '']
    for e in events:
        root = etree.fromstring(e)
        assert root.tag == 'event'
        ts = root[0]
        assert ts.tag == 'time'
        ts_int = int(ts.text)
        assert now_seconds() - ts_int < 30
        idx = root[1]
        assert idx.tag == 'index'
        assert idx.text == 'main'
        src = root[2]
        assert src.tag == 'source'
        assert src.text == 'eventgen'
        st = root[3]
        assert st.tag == 'sourcetype'
        assert st.text == 'eventgen'
        h = root[4]
        assert h.tag == 'host'
        assert h.text == '127.0.0.1'
        d = root[5]
        assert d.tag == 'data'
        ts_str = datetime.datetime.fromtimestamp(ts_int).strftime('%Y-%m-%d %H:%M:%S')
        raw = d.text.strip()
        assert raw.startswith(ts_str)
        p = re.compile(r'WINDBAG Event (\d+) of 12 randint (\d+)')
        m = p.search(raw)
        assert m is not None
        assert len(m.groups()) == 2
