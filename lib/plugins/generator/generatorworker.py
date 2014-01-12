from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
import threading
try:
    import billiard as multiprocessing
except ImportError, e:
    import multiprocessing
import Queue
import datetime
from eventgenconfig import Config

class GeneratorProcessWorker(multiprocessing.Process):
    def __init__(self, num, q1, q2):
        self.worker = GeneratorRealWorker(num, q1, q2)

        multiprocessing.Process.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        self.worker.stopping = True

class GeneratorThreadWorker(threading.Thread):
    def __init__(self, num, q1, q2):
        self.worker = GeneratorRealWorker(num, q1, q2)

        threading.Thread.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        self.worker.stopping = True

class GeneratorRealWorker:
    stopping = False

    def __init__(self, num, q1, q2):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        globals()['c'] = Config()

        logger.debug("Starting GeneratorRealWorker")

        self._pluginCache = { }

        self.num = num
        c.generatorQueue = q1
        c.outputQueue = q2

    def run(self):
        if c.profiler:
            import cProfile
            globals()['threadrun'] = self.real_run
            cProfile.runctx("threadrun()", globals(), locals(), "eventgen_generatorworker_%s" % self.num)
        else:
            self.real_run()

    def real_run(self):
        while not self.stopping:
            try:
                # Grab item from the queue to generate, grab an instance of the plugin, then generate
                samplename, count, earliestts, latestts = c.generatorQueue.get(block=True, timeout=1.0)
                earliest = datetime.datetime.fromtimestamp(earliestts)
                latest = datetime.datetime.fromtimestamp(latestts)
                c.generatorQueueSize.decrement()
                if samplename != None:
                    if samplename in self._pluginCache:
                        plugin = self._pluginCache[samplename]
                        plugin.updateSample(sample)
                    else:
                        for s in c.samples:
                            if s.name == samplename:
                                sample = s
                                break
                        plugin = c.getPlugin('generator.'+sample.generator)(sample)
                        self._pluginCache[sample.name] = plugin
                    # logger.info("GeneratorWorker %d generating %d events from '%s' to '%s'" % (self.num, count, \
                    #             datetime.datetime.strftime(earliest, "%Y-%m-%d %H:%M:%S"), \
                    #             datetime.datetime.strftime(latest, "%Y-%m-%d %H:%M:%S")))
                    plugin.gen(count, earliest, latest)
                else:
                    logger.debug("Received sentinel, shutting down GeneratorWorker %d" % self.num)
                    self.stop()
            except Queue.Empty:
                # Queue empty, do nothing... basically here to catch interrupts
                pass

    def stop(self):
        self.stopping = True

def load():
    if globals()['threadmodel'] == 'thread':
        return GeneratorThreadWorker
    else:
        return GeneratorProcessWorker