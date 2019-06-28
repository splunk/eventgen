import urllib
import httplib2
from xml.dom import minidom
import time
import json

BASEURL = 'https://127.0.0.1:8089'
USERNAME = 'admin'
PASSWORD = 'changeme'


def get_session_key():
    server_content = httplib2.Http(disable_ssl_certificate_validation=True).request(
        BASEURL + '/services/auth/login',
        'POST',
        headers={},
        body=urllib.urlencode({'username': USERNAME, 'password': PASSWORD})
    )[1]
    try:
        session_key = minidom.parseString(server_content).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue
        return session_key
    except Exception as e:
        raise Exception('Failed to get session key: %s' % str(e))


def preprocess_search(search_query):
    # Remove leading and trailing whitespace from the search
    search_query = search_query.strip()
    # If the query doesn't already start with the 'search' operator or another
    # generating command (e.g. "| inputcsv"), then prepend "search " to it.
    if not (search_query.startswith('search') or search_query.startswith('|')):
        search_query = 'search ' + search_query
    return search_query


def run_search(session_key, search_query):
    response = httplib2.Http(disable_ssl_certificate_validation=True).request(
        BASEURL + '/services/search/jobs',
        'POST',
        headers={'Authorization': 'Splunk %s' % session_key},
        body=urllib.urlencode({'search': search_query})
    )[1]
    # return search job id
    try:
        return minidom.parseString(response).getElementsByTagName('sid')[0].childNodes[0].nodeValue
    except Exception as e:
        raise Exception('Failed to start search: %s' % str(e))


def get_search_response(session_key, search_job_id):
    # wait one second for the search to complete
    time.sleep(1)
    results = httplib2.Http(disable_ssl_certificate_validation=True).request(
        BASEURL + '/services/search/jobs/%s/results' % search_job_id,
        'GET',
        headers={'Authorization': 'Splunk %s' % session_key},
        body=urllib.urlencode({'output_mode': 'json'})
    )
    try:
        return json.loads(results[1])['results']
    except Exception as e:
        raise Exception('Failed to get search results: %s' % str(e))
