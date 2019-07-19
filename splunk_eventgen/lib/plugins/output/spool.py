# import sys, os
# path_prepend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(path_prepend)
# from eventgenoutputtemplates import OutputTemplate

from __future__ import division

import os
import time

from outputplugin import OutputPlugin
from logging_config import logger


class SpoolOutputPlugin(OutputPlugin):
    useOutputQueue = True
    name = 'spool'
    MAXQUEUELENGTH = 10

    validSettings = ['spoolDir', 'spoolFile']
    defaultableSettings = ['spoolDir', 'spoolFile']

    _spoolDir = None
    _spoolFile = None

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)
        self._spoolDir = sample.pathParser(sample.spoolDir)
        self._spoolFile = sample.spoolFile
        self.spoolPath = self._spoolDir + os.sep + self._spoolFile

    def flush(self, q):
        if len(q) > 0:
            logger.debug("Flushing output for sample '%s' in app '%s' for queue '%s'" %
                              (self._sample.name, self._app, self._sample.source))
            # Keep trying to open destination file as it might be touched by other processes
            data = ''.join(event['_raw'] for event in q if event.get('_raw'))
            while True:
                try:
                    with open(self.spoolPath, 'a') as dst:
                        dst.write(data)
                    break
                except:
                    time.sleep(0.1)
            logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample.name))


def load():
    """Returns an instance of the plugin"""
    return SpoolOutputPlugin
