# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division
from outputplugin import OutputPlugin
import shutil
import logging
import time
import os

class SpoolOutputPlugin(OutputPlugin):
    name = 'spool'
    MAXQUEUELENGTH = 10

    validSettings = [ 'spoolDir', 'spoolFile' ]
    defaultableSettings = [ 'spoolDir', 'spoolFile' ]

    _spoolDir = None
    _spoolFile = None
    _workingFilePath = None
    _workingFH = None

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'SpoolOutputPlugin', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

        self._spoolDir = sample.pathParser(sample.spoolDir)
        self._spoolFile = sample.spoolFile

    def flush(self, q):
        if len(q) > 0:
            nowtime = int(time.mktime(time.gmtime()))
            workingfile = str(nowtime) + '-' + str(self._sample.name) + '.part'
            self._workingFilePath = os.path.join(c.greatgrandparentdir, self._app, 'samples', workingfile)
            logger.debug("Creating working file '%s' for sample '%s' in app '%s'" % (workingfile, self._sample.name, self._app))
            self._workingFH = open(self._workingFilePath, 'w')

            metamsg = q.popleft()
            msg = metamsg['_raw']

            logger.debug("Flushing output for sample '%s' in app '%s' for queue '%s'" % (self._sample.name, self._app, self._sample.source))

            try:
                while msg:
                    self._workingFH.write(msg)

                    msg = q.popleft()['_raw']
                logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample.name))
            except IndexError:
                logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample.name))
            
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


def load():
    """Returns an instance of the plugin"""
    return SpoolOutputPlugin
