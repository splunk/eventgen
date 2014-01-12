# TODO Make output thread or process configurable
# TODO Plugins define lists which contains a list of key value pairs, of which the key is the config
#      parameter and the value is either a list of acceptable values or a callback function to parse the value
# TODO Move config validation from config object to splunkstream plugin
# TODO Main output object puts items into the queue.  There will be at least one of these per sample thread/process
#      so it doesn't make sense to multithread this, it's already multithreaded putting items in the queue.  Flush
#      method is what puts jobs on the work queue for the workers to pick up.  Main output object knows when to flush
#      based on plugin type and provides a manual flush method which puts the jobs on the queue.
# TODO Main eventgen.py creates a configurable number of output workers, which will keep popping items off the
#      queue until its empty, each instantiating a copy of the plugin object for each worker exection time (copies
#      of worker objects should be cached to avoid creating them on every execution) and then processing the items
#      according to the given plugin type.

from __future__ import division
import os, sys
import logging
import logging.handlers
import httplib, httplib2
import urllib
import re
import base64
from xml.dom import minidom
import time
from collections import deque
import shutil
import pprint
import base64
import threading
import copy
from Queue import Full
import json
import time

class Output:
    """Base class which loads output plugins in BASE_DIR/lib/plugins/output and handles queueing"""

    def __init__(self, sample):
        """ Initialize the plugin list """
        self.__plugins = {}

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()
        self._app = sample.app
        self._sample = sample
        self._outputMode = sample.outputMode
        
        self._queue = deque([])
        self._workers = [ ]

        self.MAXQUEUELENGTH = c.getPlugin(self._sample.name).MAXQUEUELENGTH

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def send(self, msg):
        # ts = self._sample.timestamp if self._sample.timestamp != None else self._sample.now()
        self._queue.append({'_raw': msg, 'index': self._sample.index,
                        'source': self._sample.source, 'sourcetype': self._sample.sourcetype,
                        'host': self._sample.host, 'hostRegex': self._sample.hostRegex,
                        '_time': time.mktime(self._sample.timestamp.timetuple())})

        if len(self._queue) >= self.MAXQUEUELENGTH:
            self.flush()

    def bulksend(self, msglist):
        self._queue.extend(msglist)

        if len(self._queue) >= self.MAXQUEUELENGTH:
            self.flush()

    def flush(self):
        # q = deque(list(self._queue)[:])
        q = list(self._queue)
        logger.debugv("Flushing queue for sample '%s' with size %d" % (self._sample.name, len(q)))
        self._queue.clear()
        while not self._sample.stopping:
            try:
                c.outputQueue.put((self._sample.name, q), block=True, timeout=1.0)
                c.outputQueueSize.increment()
                # logger.info("Outputting queue")
                break
            except Full:
                logger.warn("Output Queue full, looping again")
                pass



# The max number of threads setup for HTTP type outputs
MAX_WORKERS = 5


# This is used only for the HTTP output outputModes
# This allows us to iowait while we keep on generating events
# in the background
class Worker(threading.Thread):
    func = None
    queue = None
    running = None

    def __init__(self, func, queue):
        self.func = func
        self.queue = queue
        self.running = False
        threading.Thread.__init__(self)

    def run(self):
        self.running = True
        try:
            self.func(self.queue)
        except:
            import traceback
            sys.stderr.write(traceback.format_exc())
            self.running = False
        self.running = False
        sys.exit(0)

class OutputOrig:
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
    _splunkHost = None
    _splunkPort = None
    _splunkMethod = None
    _splunkUser = None
    _splunkPass = None
    _splunkhttp = None
    _projectID = None
    _accessToken = None
    _workers = None
    
    validOutputModes = ['spool', 'file', 'splunkstream']
    validSplunkMethods = ['http', 'https']
    
    # Queue of outputs.  Will be sent to host when flush() is called
    _queue = None
    
    def __init__(self, sample):
        from eventgenconfig import Config
        self._c = Config()
        self._app = sample.app
        self._sample = sample
        self._outputMode = sample.outputMode
        
        self._queue = deque([])
        self._workers = [ ]
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
            
        if self._outputMode == 'spool':
            self._spoolDir = sample.pathParser(sample.spoolDir)
            self._spoolFile = sample.spoolFile
        elif self._outputMode == 'file':
            if sample.fileName == None:
                logger.error('outputMode file but file not specified for sample %s' % self._sample.name)
                raise ValueError('outputMode file but file not specified for sample %s' % self._sample.name)
                
            self._file = sample.fileName
            self._fileMaxBytes = sample.fileMaxBytes
            self._fileBackupFiles = sample.fileBackupFiles
            
            # 9/7/12 Replacing python logging with our own logging handler code
            # self._fileLogger = logging.getLogger('eventgen_realoutput_'+self._file)
            # formatter = logging.Formatter('%(message)s')
            # handler = logging.handlers.RotatingFileHandler(filename=self._file, maxBytes=self._fileMaxBytes,
            #                                                 backupCount=self._fileBackupFiles)
            # handler.setFormatter(formatter)
            # self._fileLogger.addHandler(handler)
            # self._fileLogger.setLevel(logging.DEBUG)

            self._fileHandle = open(self._file, 'a')
            self._fileLength = os.stat(self._file).st_size
            logger.debug("Configured to log to '%s' with maxBytes '%s' with backupCount '%s'" % \
                            (self._file, self._fileMaxBytes, self._fileBackupFiles))
        elif self._outputMode == 'splunkstream':
            if c.splunkEmbedded:
                try:
                    import splunk.auth
                    self._sample.splunkUrl = splunk.auth.splunk.getLocalServerInfo()
                    results = re.match('(http|https)://([^:/]+):(\d+).*', self._sample.splunkUrl)
                    self._splunkMethod = results.groups()[0]
                    self._splunkHost = results.groups()[1]
                    self._splunkPort = results.groups()[2]
                except:
                    import traceback
                    trace = traceback.format_exc()
                    logger.error('Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s.  Stacktrace: %s' % (self._sample.name, trace))
                    raise ValueError('Error parsing host from splunk.auth.splunk.getLocalServerInfo() for sample %s' % self._sample.name)
            else:
                if sample.splunkHost == None:
                    logger.error('outputMode splunkstream but splunkHost not specified for sample %s' % self._sample.name)
                    raise ValueError('outputMode splunkstream but splunkHost not specified for sample %s' % self._sample.name)  
                elif sample.splunkHost == '[':
                    try:
                        sample.splunkHost = json.loads(sample.splunkHost)
                    except:
                        logger.error('splunkHost configured as JSON, but unparseable for sample %s' % self._sample.name)
                        raise ValueError('splunkHost configured as JSON, but unparseable for sample %s' % self._sample.name)
                if sample.splunkUser == None:
                    logger.error('outputMode splunkstream but splunkUser not specified for sample %s' % self._sample.name)
                    raise ValueError('outputMode splunkstream but splunkUser not specified for sample %s' % self._sample.name)     
                if sample.splunkPass == None:
                    logger.error('outputMode splunkstream but splunkPass not specified for sample %s' % self._sample.name)
                    raise ValueError('outputMode splunkstream but splunkPass not specified for sample %s' % self._sample.name)
                        
                self._splunkHost = sample.splunkHost
                self._splunkPort = sample.splunkPort
                self._splunkMethod = sample.splunkMethod
                self._splunkUser = sample.splunkUser
                self._splunkPass = sample.splunkPass
                self._sample.splunkUrl = '%s://%s:%s' % (self._splunkMethod, self._splunkHost, self._splunkPort)
                
                try:
                    myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
                    response = myhttp.request(self._sample.splunkUrl + '/services/auth/login', 'POST',
                                                headers = {}, body=urllib.urlencode({'username': self._splunkUser, 
                                                                                    'password': self._splunkPass}))[1]
                    self._sample.sessionKey = minidom.parseString(response).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue
                except:
                    logger.error('Error getting session key for non-SPLUNK_EMBEEDED for sample %s' % self._sample.name)
                    raise IOError('Error getting session key for non-SPLUNK_EMBEEDED for sample %s' % self._sample.name)
                    
            logging.debug("Retrieved session key '%s' for Splunk session for sample %s'" % (self._sample.sessionKey, self._sample.name))    
        elif self._outputMode == 'stormstream':        
            self._accessToken = sample.accessToken
            self._projectID = sample.projectID
            
        logger.debug("Output init completed.  Output: %s" % self)
        
    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()
            
    def send(self, msg):
        """Queues a message for output to configured outputs"""
        if self._outputMode in ('splunkstream', 'stormstream'):
                self._queue.append({'_raw': msg, 'index': self._sample.index,
                                    'source': self._sample.source, 'sourcetype': self._sample.sourcetype,
                                    'host': self._sample.host, 'hostRegex': self._sample.hostRegex})
        else:
            self._queue.append({'_raw': msg})

        if self._outputMode in ('splunkstream', 'stormstream') and len(self._queue) > 1000:
            self.flush()
        elif len(self._queue) > 10:
            self.flush()
        
    def flush(self, force=False):
        """Flushes output from the queue out to the specified output"""
        # Force a flush with a queue bigger than 1000, or unless forced
        if (len(self._queue) >= 1000 or (force and len(self._queue) > 0)) \
                and self._outputMode in ('splunkstream', 'stormstream'):
            # For faster processing, we need to break these up by source combos
            # so they'll each get their own thread.
            # Fixes a bug where we're losing source and sourcetype with bundlelines type transactions
            queues = { }
            for row in self._queue:
                if row['source'] is None:
                    row['source'] = ''
                if row['sourcetype'] is None:
                    row['sourcetype'] = ''
                if not row['source']+'_'+row['sourcetype'] in queues:
                    queues[row['source']+'_'+row['sourcetype']] = deque([])

            # logger.debug("Queues setup: %s" % pprint.pformat(queues))
            m = self._queue.popleft()
            while m:
                queues[m['source']+'_'+m['sourcetype']].append(m)
                try:
                    m = self._queue.popleft()
                except IndexError:
                    m = False

            logger.debug("Creating workers, limited to %s" % MAX_WORKERS)
            for k, v in queues.items():
                # Trying to limit to MAX_WORKERS
                w = Worker(self._flush, v)
                
                for i in xrange(0, len(self._workers)):
                    if not self._workers[i].running:
                        del self._workers[i]
                        break

                while len(self._workers) > MAX_WORKERS:
                    logger.info("Waiting for workers, limited to %s" % MAX_WORKERS)
                    for i in xrange(0, len(self._workers)):
                        if not self._workers[i].running:
                            del self._workers[i]
                            break
                    time.sleep(0.5)
                self._workers.append(w)
                
                w.start()
        elif (len(self._queue) >= 1000 or (force and len(self._queue) > 0)) \
                and self._outputMode in ('spool'):
            q = copy.deepcopy(self._queue)
            self._queue.clear()
            self._flush(q)

        elif self._outputMode in ('file'):
            # q = copy.deepcopy(self._queue)
            # self._queue.clear()
            # self._flush(q)

            self._flush(self._queue)

            # w = Worker(self._flush, q)
            # w.start()

    # 9/15/12 CS Renaming to internal function and wrapping with a future
    def _flush(self, queue):
        """Internal function which does the real flush work"""
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

            if self._outputMode == 'spool':
                nowtime = int(time.mktime(time.gmtime()))
                workingfile = str(nowtime) + '-' + self._sample + '.part'
                self._workingFilePath = os.path.join(c.greatgrandparentdir, self._app, 'samples', workingfile)
                logger.debug("Creating working file '%s' for sample '%s' in app '%s'" % (workingfile, self._sample.name, self._app))
                self._workingFH = open(self._workingFilePath, 'w')
            elif self._outputMode == 'splunkstream':
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
                    url = '/services/receivers/stream?%s' % (urllib.urlencode(urlparms))
                    splunkhttp.putrequest("POST", url)
                    splunkhttp.putheader("Authorization", "Splunk %s" % self._sample.sessionKey)
                    splunkhttp.putheader("x-splunk-input-mode", "streaming")
                    splunkhttp.endheaders()
                    logger.debug("POSTing to url %s on %s://%s:%s with sessionKey %s" \
                                % (url, self._splunkMethod, self._splunkHost, self._splunkPort, self._sample.sessionKey))
                except httplib.HTTPException, e:
                    logger.error('Error connecting to Splunk for logging for sample %s.  Exception "%s" Config: %s' % (self._sample.name, e.args, self))
                    raise IOError('Error connecting to Splunk for logging for sample %s' % self._sample)
            try:
                while msg:
                    if self._outputMode == 'spool':
                        self._workingFH.write(msg)
                    elif self._outputMode == 'file':
                        # # 5/9/12 CS We log as error so that even the most restrictive 
                        # # filter will push to file
                        # if msg[-1] == '\n':
                        #     msg = msg[:-1]
                        # self._fileLogger.error(msg)

                        if msg[-1] != '\n':
                            msg += '\n'

                        self._fileHandle.write(msg)
                        self._fileLength += len(msg)

                        # If we're at the end of the max allowable size, shift all files
                        # up a number and create a new one
                        if self._fileLength > self._fileMaxBytes:
                            self._fileHandle.flush()
                            self._fileHandle.close()
                            if os.path.exists(self._file+'.'+str(self._fileBackupFiles)):
                                logger.debug('File Output: Removing file: %s' % self._file+'.'+str(self._fileBackupFiles))
                                os.unlink(self._file+'.'+str(self._fileBackupFiles))
                            for x in range(1, self._fileBackupFiles)[::-1]:
                                logger.debug('File Output: Checking for file: %s' % self._file+'.'+str(x))
                                if os.path.exists(self._file+'.'+str(x)):
                                    logger.debug('File Output: Renaming file %s to %s' % (self._file+'.'+str(x), self._file+'.'+str(x+1)))
                                    os.rename(self._file+'.'+str(x), self._file+'.'+str(x+1))
                            os.rename(self._file, self._file+'.1')
                            self._fileHandle = open(self._file, 'w')
                            self._fileLength = 0


                    elif self._outputMode == 'splunkstream':
                        if msg[-1] != '\n':
                            msg += '\n'
                        # logger.debug("Sending %s to self._splunkhttp" % msg)
                        splunkhttp.send(msg)
                    elif self._outputMode == 'stormstream':
                        streamout += msg
                    
                    msg = queue.popleft()['_raw']
                logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample.name))
            except IndexError:
                logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample.name))
        else:
            streamout = ""
            
        # Cleanup after writing queue
        if self._outputMode == 'spool':
            ## Move file to spool
            self._workingFH.close()
            spoolPath = self._spoolDir + os.sep + self._spoolFile
            logger.debug("Moving '%s' to '%s' for sample '%s' in app '%s'" % (self._workingFilePath, spoolPath, self._sample.name, self._app))
            if os.path.exists(self._workingFilePath):
                if os.path.exists(spoolPath):
                    os.system("cat %s >> %s" % (self._workingFilePath, spoolPath))
                    os.remove(self._workingFilePath)
                else:
                    shutil.move(self._workingFilePath, spoolPath)
            else:
                logger.error("File '%s' missing" % self._workingFilePath)
        elif self._outputMode == 'file':
            if not self._fileHandle.closed:
                self._fileHandle.flush()
        elif self._outputMode == 'splunkstream':
            #logger.debug("Closing self._splunkhttp connection")
            if splunkhttp != None:
                splunkhttp.close()
                splunkhttp = None
        elif self._outputMode == 'stormstream':
            if len(streamout) > 0:
                try:
                    self._splunkhttp = httplib.HTTPSConnection('api.splunkstorm.com', 443)
                    urlparms = [ ]
                    if self._sample.source != None:
                        urlparms.append(('source', self._sample.source))
                    if self._sample.sourcetype != None:
                        urlparms.append(('sourcetype', self._sample.sourcetype))
                    if self._sample.host != None:
                        urlparms.append(('host', self._sample.host))
                    if self._sample.projectID != None:
                        urlparms.append(('project', self._sample.projectID))
                    url = '/1/inputs/http?%s' % (urllib.urlencode(urlparms))
                    headers = {'Authorization': "Basic %s" % base64.b64encode(':'+self._accessToken)}
                    self._splunkhttp.request("POST", url, streamout, headers)
                    logger.debug("POSTing to url %s on https://api.splunkstorm.com with accessToken %s" \
                                % (url, base64.b64encode(self._accessToken+':')))
                except httplib.HTTPException:
                    logger.error('Error connecting to Splunk for logging for sample %s' % self._sample.name)
                    raise IOError('Error connecting to Splunk for logging for sample %s' % self._sample.name)
                try:
                    response = self._splunkhttp.getresponse()
                    data = response.read()
                    logger.debug("Data returned %s" % data)
                    self._splunkhttp.close()
                    self._splunkhttp = None
                except httplib.BadStatusLine:
                    logger.error("Received bad status from Storm for sample '%s'" % self._sample.name)