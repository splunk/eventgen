import json
import os
import csv

base_dir = os.path.dirname(os.path.abspath(__file__))


def test_token_replacement(eventgen_test_helper):
    """Test token replcement with replacementType= static | random | file | timestamp"""
    events = eventgen_test_helper("eventgen_token_replacement.conf").get_events()
    # assert the events size is 10 since end = 1
    assert len(events) == 10

    with open(os.path.join(base_dir, 'sample', 'id.csv'), 'rb') as f:
        id_content = f.read()
    with open(os.path.join(base_dir, 'sample', 'ip.csv'), 'rb') as f:
        ip_content = f.read()
    with open(os.path.join(base_dir, 'sample', 'cp.csv'), 'rb') as f:
        cp_content = f.read()
    with open(os.path.join(base_dir, 'sample', 'city.csv'), 'rb') as f:
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

    for event in events:
        try:
            event_obj = json.loads(event)
        except ValueError:
            raise Exception("Token replacement error")

        # assert replacementType = file
        assert event_obj["id"] in id_content
        assert event_obj["cp"] in cp_content
        assert event_obj["message"]["cliIP"] in ip_content

        # assert replacementType = static
        assert event_obj["netPerf"]["lastByte"] == "0"

        # assert replacementType = random
        assert 5000 > int(event_obj["message"]["bytes"]) > 40

        # assert replacementType = file and replacement = <replacement file name>:<column number>
        assert event_obj["geo"]["city"] in city
        assert event_obj["geo"]["country"] in country
        assert event_obj["geo"]["lat"] in latitude
        assert event_obj["geo"]["long"] in longitude
