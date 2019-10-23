import json
import os
import csv
import re

base_dir = os.path.dirname(os.path.abspath(__file__))


def test_token_replacement(eventgen_test_helper):
    """Test token replcement with replacementType= static | random | file | timestamp"""
    events = eventgen_test_helper("eventgen_token_replacement.conf").get_events()
    # assert the events size is 10 since end = 1
    assert len(events) == 10

    with open(os.path.join(base_dir, 'sample', 'id.csv'), 'rt') as f:
        id_content = f.read()
    with open(os.path.join(base_dir, 'sample', 'ip.csv'), 'rt') as f:
        ip_content = f.read()
    with open(os.path.join(base_dir, 'sample', 'cp.csv'), 'rt') as f:
        cp_content = f.read()
    with open(os.path.join(base_dir, 'sample', 'city.csv'), 'rt') as f:
        reader = csv.reader(f)
        country = []
        city = []
        latitude = []
        longitude = []
        for row in reader:
            country.append(row[0])
            city.append(row[1])
            latitude.append(row[3])
            longitude.append(row[4])

    integer_id_seed = 1
    for event in events:
        try:
            event_obj = json.loads(event)
        except ValueError:
            raise Exception("Token replacement error")

        # assert replacementType = integerid
        assert int(event_obj["ppcustomdata"]["receiver_id"]) == integer_id_seed
        integer_id_seed += 1

        # assert replacementType = file
        assert event_obj["id"] in id_content
        assert event_obj["cp"] in cp_content
        assert event_obj["message"]["cliIP"] in ip_content

        # assert replacementType = static
        assert event_obj["netPerf"]["lastByte"] == "0"

        # assert replacementType = random and replacement = integer[<start>:<end>]
        assert 5000 >= int(event_obj["message"]["bytes"]) > 40

        # assert replacementType = random and replacement = float[<start>:<end>]
        assert 3.0 >= float(event_obj["netPerf"]["lastMileRTT"]) >= -3.0

        # assert replacementType = random and replacement = ipv4 | ipv6 | mac
        ipv4_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
        ipv6_pattern = re.compile(r"^([A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}$")
        mac_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

        assert ipv4_pattern.match(event_obj["akadebug"]["Ak_IP"]) is not None
        assert ipv6_pattern.match(event_obj["akadebug"]["forward-origin-ip"]) is not None
        assert mac_pattern.match(event_obj["akadebug"]["end-user-ip"]) is not None

        # assert replacementType = file | mvfile and replacement = <replacement file name>:<column number>
        assert event_obj["geo"]["city"] in city
        assert event_obj["geo"]["country"] in country
        assert event_obj["geo"]["lat"] in latitude
        assert event_obj["geo"]["long"] in longitude
