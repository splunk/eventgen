from __future__ import division
import logging
import logging.handlers
import httplib, httplib2
import urllib
import re
import base64
from xml.dom import minidom
import time
from collections import deque
import os
import shutil
import pprint
import base64
    
class Output:
    """Output events, abstracting output method"""
    _app = None
    _sample = None
    
    _c = None
    _outputMode = None
    _spoolDir = None
    _spoolFile = None
    _workingFilePath = None
    _workingFH = None
    _fileName = None
    _fileMaxBytes = None
    _fileBackupFiles = None
    _fileLogger = None
    _sessionKey = None
    _splunkHost = None
    _splunkPort = None
    _splunkMethod = None
    _splunkUser = None
    _splunkPass = None
    _splunkUrl = None
    _splunkhttp = None
    index = None
    source = None
    sourcetype = None
    host = None
    _hostRegex = None
    _projectID = None
    _accessToken = None
    
    validOutputModes = ['spool', 'file', 'splunkstream']
    validSplunkMethods = ['http', 'https']
    
    # Queue of outputs.  Will be sent to host when flush() is called
    _queue = None
    
    def __init__(self, sample):
        from eventgenconfig import Config
        self._c = Config()
        self._app = sample.app
        self._sample = sample.name
        self._outputMode = sample.outputMode
        
        self._queue = deque([])
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
                
        if self._outputMode in ('splunkstream', 'stormstream'):
            self._index = sample.index
            self._source = sample.source
            self._sourcetype = sample.sourcetype
            self._host = sample.host
            self._hostRegex = sample.hostRegex
            
        if self._outputMode == 'spool':
            self._spoolDir = sample.pathParser(sample.spoolDir)
            self._spoolFile = sample.spoolFile
        elif self._outputMode == 'file':
            if sample.fileName == None:
                logger.error('outputMode file but file not specified for sample %s' % self._sample)
                raise ValueError('outputMode file but file not specified for sample %s' % self._sample)
                
            self._file = sample.fileName
            self._fileMaxBytes = sample.fileMaxBytes
            self._fileBackupFiles = sample.fileBackupFiles
            
            self._fileLogger = logging.getLogger('eventgen_realoutput')
            formatter = logging.Formatter('%(message)s')
            handler = logging.handlers.RotatingFileHandler(filename=self._file, maxBytes=self._fileMaxBytes,
                                                            backupCount=self._fileBackupFiles)
            handler.setFormatter(formatter)
            self._fileLogger.addHandler(handler)
            self._fileLogger.setLevel(logging.DEBUG)
            logger.debug("Configured to log to '%s' with maxBytes '%s' with backupCount '%s'" % \
                            (self._file, self._fileMaxBytes, self._fileBackupFiles))
        elif self._outputMode == 'splunkstream':
            if self._c.splunkEmbedded:
                try:
                    import splunk.auth
                    self._splunkUrl = splunk.auth.splunk.getLocalServerInfo()
                    results = re.match('(http|https)://([^:/]+):(\d+).*', self._splunkUrl)
                    self._splunkMethod = results.groups()[0]
                    self._splunkHost = results.groups()[1]
                    self._splunkPort = results.groups()[2]
                except:
                    import traceback
                    trace = traceback.format_exc()
                    logger.error('Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s.  Stacktrace: %s' % (self._sample, trace))
                    raise ValueError('Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s' % self._sample)
            else:
                if sample.splunkHost == None:
                    logger.error('outputMode splunkstream but splunkHost not specified for sample %s' % self._sample)
                    raise ValueError('outputMode splunkstream but splunkHost not specified for sample %s' % self._sample)  
                elif sample.splunkHost == '[':
                    try:
                        sample.splunkHost = json.loads(sample.splunkHost)
                    except:
                        logger.error('splunkHost configured as JSON, but unparseable for sample %s' % self._sample)
                        raise ValueError('splunkHost configured as JSON, but unparseable for sample %s' % self._sample)
                if sample.splunkUser == None:
                    logger.error('outputMode splunkstream but splunkUser not specified for sample %s' % self._sample)
                    raise ValueError('outputMode splunkstream but splunkUser not specified for sample %s' % self._sample)            
                if sample.splunkPass == None:
                    logger.error('outputMode splunkstream but splunkPass not specified for sample %s' % self._sample)
                    raise ValueError('outputMode splunkstream but splunkPass not specified for sample %s' % self._sample)
                        
                self._splunkHost = sample.splunkHost
                self._splunkPort = sample.splunkPort
                self._splunkMethod = sample.splunkMethod
                self._splunkUser = sample.splunkUser
                self._splunkPass = sample.splunkPass
                self._splunkUrl = '%s://%s:%s' % (self._splunkMethod, self._splunkHost, self._splunkPort)
                
                try:
                    myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
                    response = myhttp.request(self._splunkUrl + '/services/auth/login', 'POST',
                                                headers = {}, body=urllib.urlencode({'username': self._splunkUser, 
                                                                                    'password': self._splunkPass}))[1]
                    self._c.sessionKey = minidom.parseString(response).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue
                except:
                    logger.error('Error getting session key for non-SPLUNK_EMBEEDED for sample %s' % self._sample)
                    raise IOError('Error getting session key for non-SPLUNK_EMBEEDED for sample %s' % self._sample)
                    
            logging.debug("Retrieved session key '%s' for Splunk session for sample %s'" % (self._c.sessionKey, self._sample))    
        elif self._outputMode == 'stormstream':        
            self._accessToken = sample.accessToken
            self._projectID = sample.projectID
            
        logger.debug("Output init completed.  Output: %s" % self)
        
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        return pprint.pformat(temp)

    def __repr__(self):
        return self.__str__()
            
    def send(self, msg):
        """Queues a message for output to configured outputs"""
        self._queue.append(msg)
        if len(self._queue) > 10000:
            self.flush()
            
    def refreshconfig(self, sample):
        """Refreshes output config based on sample"""
        if self._outputMode in ('splunkstream', 'stormstream'):
            self._index = sample.index
            self._source = sample.source
            self._sourcetype = sample.sourcetype
            self._host = sample.host
            self._hostRegex = sample.hostRegex
            logger.debug("Refreshed config.  Set Index '%s': Source '%s': Sourcetype: '%s' Host: '%s' HostRegex: '%s'" % \
                        (self._index, self._source, self._sourcetype, self._host, self._hostRegex))
        
    def flush(self):
        """Flushes output from the queue out to the specified output"""
        if self._outputMode == 'spool':
            nowtime = int(time.mktime(time.gmtime()))
            workingfile = str(nowtime) + '-' + self._sample + '.part'
            self._workingFilePath = os.path.join(self._c.greatgrandparentdir, self._app, 'samples', workingfile)
            logger.debug("Creating working file '%s' for sample '%s' in app '%s'" % (workingfile, self._sample, self._app))
            self._workingFH = open(self._workingFilePath, 'w')
        elif self._outputMode == 'splunkstream':
            try:
                if self._splunkMethod == 'https':
                    connmethod = httplib.HTTPSConnection
                else:
                    connmethod = httplib.HTTPConnection
                self._splunkhttp = connmethod(self._splunkHost, self._splunkPort)
                self._splunkhttp.connect()
                urlparms = [ ]
                if self._index != None:
                    urlparms.append(('index', self._index))
                if self._source != None:
                    urlparms.append(('source', self._source))
                if self._sourcetype != None:
                    urlparms.append(('sourcetype', self._sourcetype))
                if self._hostRegex != None:
                    urlparms.append(('host_regex', self._hostRegex))
                elif self._host != None:
                    urlparms.append(('host', self._host))
                url = '/services/receivers/stream?%s' % (urllib.urlencode(urlparms))
                self._splunkhttp.putrequest("POST", url)
                self._splunkhttp.putheader("Authorization", "Splunk %s" % self._c.sessionKey)
                self._splunkhttp.putheader("x-splunk-input-mode", "streaming")
                self._splunkhttp.endheaders()
                logger.debug("POSTing to url %s on %s://%s:%s with sessionKey %s" \
                            % (url, self._splunkMethod, self._splunkHost, self._splunkPort, self._c.sessionKey))
            except httplib.HTTPException:
                logger.error('Error connecting to Splunk for logging for sample %s' % self._sample)
                raise IOError('Error connecting to Splunk for logging for sample %s' % self._sample)
        try:
            msg = self._queue.popleft()
            streamout = ""
            while msg:
                if self._outputMode == 'spool':
                    self._workingFH.write(msg)
                elif self._outputMode == 'file':
                    # 5/9/12 CS We log as error so that even the most restrictive 
                    # filter will push to file
                    if msg[-1] == '\n':
                        msg = msg[:-1]
                    self._fileLogger.error(msg)
                elif self._outputMode == 'splunkstream':
                    if msg[-1] != '\n':
                        msg += '\n'
                    # logger.debug("Sending %s to self._splunkhttp" % msg)
                    self._splunkhttp.send(msg)
                elif self._outputMode == 'stormstream':
                    streamout += msg
                    
                msg = self._queue.popleft()
            logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample))
        except IndexError:
            logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample))
            
        # Cleanup after writing queue
        if self._outputMode == 'spool':
            ## Move file to spool
            self._workingFH.close()
            spoolPath = self._spoolDir + os.sep + self._spoolFile
            logger.debug("Moving '%s' to '%s' for sample '%s' in app '%s'" % (self._workingFilePath, spoolPath, self._sample, self._app))
            if os.path.exists(self._workingFilePath):
                shutil.move(self._workingFilePath, spoolPath)
            else:
                logger.error("File '%s' missing" % self._workingFilePath)
        elif self._outputMode == 'splunkstream':
            #logger.debug("Closing self._splunkhttp connection")
            self._splunkhttp.close()
            self._splunkhttp = None
        elif self._outputMode == 'stormstream':
            try:
                self._splunkhttp = httplib.HTTPSConnection('api.splunkstorm.com', 443)
                urlparms = [ ]
                if self._source != None:
                    urlparms.append(('source', self._source))
                if self._sourcetype != None:
                    urlparms.append(('sourcetype', self._sourcetype))
                if self._host != None:
                    urlparms.append(('host', self._host))
                if self._projectID != None:
                    urlparms.append(('project', self._projectID))
                url = '/1/inputs/http?%s' % (urllib.urlencode(urlparms))
                headers = {'Authorization': "Basic %s" % base64.b64encode(self._accessToken+':')}
                self._splunkhttp.request("POST", url, streamout, headers)
                logger.debug("POSTing to url %s on https://api.splunkstorm.com with accessToken %s" \
                            % (url, base64.b64encode(self._accessToken+':')))
            except httplib.HTTPException:
                logger.error('Error connecting to Splunk for logging for sample %s' % self._sample)
                raise IOError('Error connecting to Splunk for logging for sample %s' % self._sample)
            try:
                response = self._splunkhttp.getresponse()
                data = response.read()
                logger.debug("Data returned %s" % data)
            except BadStatusLine:
                logger.error("Received bad status from Storm for sample '%s'" % self._sample)