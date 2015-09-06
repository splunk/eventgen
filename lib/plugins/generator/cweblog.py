from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import itertools
from collections import deque
import random
import subprocess
import re
from eventgenoutput import Output

class CWeblogGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger
        from eventgenconfig import Config
        globals()['c'] = Config()
    def gen(self, count, earliest, latest, **kwargs):
        # logger.debug("weblog: external_ips_len: %s webhosts_len: %s useragents_len: %s webserverstatus_len: %s" % \
                    # (self.external_ips_len, self.webhosts_len, self.useragents_len, self.webserverstatus_len))
        # path = c.grandparentdir.split(os.sep)
        # path.extend(['lib', 'plugins', 'generator', 'cweblog'])
        p = subprocess.Popen(c.grandparentdir + '/lib/plugins/generator/cweblog', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.stdin.write("%d;1;1\n" % count)
        linesstr = p.stdout.read()
        lines = re.split('\n', linesstr);
        l = [ { '_raw': line,
                'index': 'main',
                'sourcetype': 'access_combined',
                'host': 'log.buttercupgames.com',
                'source': '/opt/access_combined.log',
                '_time': 1 } for line in lines ]

        self._out.bulksend(l)
        return 0

def load():
    return CWeblogGenerator