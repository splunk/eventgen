# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from outputplugin import OutputPlugin
from xml.dom import minidom
import re
import httplib, httplib2
import urllib
import logging
from collections import deque

class SplunkStreamOutputPlugin(OutputPlugin):
    name = 'splunkstream'
    MAXQUEUELENGTH = 100

    validSettings = [ 'splunkMethod', 'splunkUser', 'splunkPass', 'splunkHost', 'splunkPort' ]
    complexSettings = { 'splunkMethod': ['http', 'https'] }
    intSettings = [ 'splunkPort' ]


    _splunkHost = None
    _splunkPort = None
    _splunkMethod = None
    _splunkUser = None
    _splunkPass = None
    _splunkhttp = None

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'SplunkStreamOutputPlugin', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

        self._splunkUrl, self._splunkMethod, self._splunkHost, self._splunkPort = c.getSplunkUrl(self._sample)
        self._splunkUser = self._sample.splunkUser
        self._splunkPass = self._sample.splunkPass
            
        if self._sample.sessionKey == None:
            try:
                myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
                logger.debugv("Getting session key from '%s' with user '%s' and pass '%s'" % (self._splunkUrl + '/services/auth/login', self._splunkUser, self._splunkPass))
                response = myhttp.request(self._splunkUrl + '/services/auth/login', 'POST',
                                            headers = {}, body=urllib.urlencode({'username': self._splunkUser, 
                                                                                'password': self._splunkPass}))[1]
                self._sample.sessionKey = minidom.parseString(response).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue
                logger.debug("Got new session for splunkstream, sessionKey '%s'" % self._sample.sessionKey)
            except:
                logger.error("Error getting session key for non-SPLUNK_EMBEEDED for sample '%s'.  Credentials are missing or wrong" % self._sample.name)
                raise IOError("Error getting session key for non-SPLUNK_EMBEEDED for sample '%s'.  Credentials are missing or wrong" % self._sample.name)
                
        logger.debug("Retrieved session key '%s' for Splunk session for sample %s'" % (self._sample.sessionKey, self._sample.name))   

    def flush(self, q):
        if len(q) > 0:
            # For faster processing, we need to break these up by source combos
            # so they'll each get their own thread.
            # Fixes a bug where we're losing source and sourcetype with bundlelines type transactions
            queues = { }
            for row in q:
                if row['source'] is None:
                    row['source'] = ''
                if row['sourcetype'] is None:
                    row['sourcetype'] = ''
                if not row['source']+'_'+row['sourcetype'] in queues:
                    queues[row['source']+'_'+row['sourcetype']] = deque([])

            # logger.debug("Queues setup: %s" % pprint.pformat(queues))
            m = q.popleft()
            while m:
                queues[m['source']+'_'+m['sourcetype']].append(m)
                try:
                    m = q.popleft()
                except IndexError:
                    m = False

            for k, queue in queues.items():
                splunkhttp = None
                if len(queue) > 0:
                    streamout = ""
                    # SHould now be getting a different output thread for each source
                    # So therefore, look at the first message in the queue, set based on that
                    # and move on
                    metamsg = queue.popleft()
                    msg = metamsg['_raw']
                    try:
                        index = metamsg['index']
                        source = metamsg['source']
                        sourcetype = metamsg['sourcetype']
                        host = metamsg['host']
                        hostRegex = metamsg['hostRegex']
                    except KeyError:
                        pass
                        
                    logger.debug("Flushing output for sample '%s' in app '%s' for queue '%s'" % (self._sample.name, self._app, self._sample.source))
                    try:
                        if self._splunkMethod == 'https':
                            connmethod = httplib.HTTPSConnection
                        else:
                            connmethod = httplib.HTTPConnection
                        splunkhttp = connmethod(self._splunkHost, self._splunkPort)
                        splunkhttp.connect()
                        urlparms = [ ]
                        if index != None:
                            urlparms.append(('index', index))
                        if source != None:
                            urlparms.append(('source', source))
                        if sourcetype != None:
                            urlparms.append(('sourcetype', sourcetype))
                        if hostRegex != None:
                            urlparms.append(('host_regex', hostRegex))
                        elif host != None:
                            urlparms.append(('host', host))
                        url = '/services/receivers/simple?%s' % (urllib.urlencode(urlparms))
                        headers = {'Authorization': "Splunk %s" % self._sample.sessionKey }

                        while msg:
                            if msg[-1] != '\n':
                                msg += '\n'
                            streamout += msg
                            try:
                                msg = queue.popleft()['_raw']
                            except IndexError:
                                msg = False

                        splunkhttp.request("POST", url, streamout, headers)
                        logger.debug("POSTing to url %s on %s://%s:%s with sessionKey %s" \
                                    % (url, self._splunkMethod, self._splunkHost, self._splunkPort, self._sample.sessionKey))

                    except httplib.HTTPException, e:
                        logger.error('Error connecting to Splunk for logging for sample %s.  Exception "%s" Config: %s' % (self._sample.name, e.args, self))
                        raise IOError('Error connecting to Splunk for logging for sample %s' % self._sample)

                    try:
                        response = splunkhttp.getresponse()
                        data = response.read()
                        if response.status != 200:
                            logger.error("Data not written to Splunk.  Splunk returned %s" % data)
                    except httplib.BadStatusLine:
                        logger.error("Received bad status from Splunk for sample '%s'" % self._sample)
                    logger.debugv("Closing splunkhttp connection")
                    if splunkhttp != None:
                        splunkhttp.close()
                        splunkhttp = None


def load():
    """Returns an instance of the plugin"""
    return SplunkStreamOutputPlugin