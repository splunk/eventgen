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
from eventgenoutput import Output
try:
    import zmq
except ImportError, e:
    pass
import marshal

class GeneratorProcessWorker(multiprocessing.Process):
    def __init__(self, num, q1, q2):
        self.worker = GeneratorRealWorker(num, q1, q2)

        multiprocessing.Process.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        logger.info("Stopping GeneratorProcessWorker %d" % self.worker.num)
        self.worker.stopping = True

class GeneratorThreadWorker(threading.Thread):
    def __init__(self, num, q1, q2):
        self.worker = GeneratorRealWorker(num, q1, q2)

        threading.Thread.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        logger.info("Stopping GeneratorThreadWorker %d" % self.worker.num)
        self.worker.stopping = True

class GeneratorRealWorker:

    def __init__(self, num, q1, q2):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'GeneratorRealWorker', 'sample': 'null'})
        globals()['logger'] = adapter

        globals()['c'] = Config()

        logger.debug("Starting GeneratorRealWorker")

        self.stopping = False

        self._pluginCache = { }

        self.num = num
        c.generatorQueue = q1
        c.outputQueue = q2

    def run(self):
        if c.profiler:
            import cProfile
            # 2/1/15 CS Fixing bug with profiling in thread mode
            # Making a copy of globals and then passing each thread its own threadsafe copy
            temp = globals()
            temp['threadrun'] = self.real_run
            # locals()['threadrun'] = self.real_run
            cProfile.runctx("threadrun()", temp, locals(), "eventgen_generatorworker_%s" % self.num)
        else:
            self.real_run()

    def real_run(self):
        if c.queueing == 'zeromq':
            context = zmq.Context()
            self.receiver = context.socket(zmq.PULL)
            self.receiver.connect(c.zmqBaseUrl+(':' if c.zmqBaseUrl.startswith('tcp') else '/')+str(c.zmqBasePort+3))

        while not self.stopping:
            try:
                # Grab item from the queue to generate, grab an instance of the plugin, then generate
                if c.queueing == 'python':
                    # logger.debugv("Grabbing generator items from python queue")
                    samplename, count, earliestts, latestts = c.generatorQueue.get(block=True, timeout=1.0)
                    # logger.debugv("Got a generator items from python queue for sample '%s'" % (samplename))
                elif c.queueing == 'zeromq':
                    # logger.debugv("Grabbing generator items from zeromq queue")
                    samplename, count, earliestts, latestts = marshal.loads(self.receiver.recv())
                    # logger.debugv("Got a generator items from zeromq queue for sample '%s'" % (samplename))
                earliest = datetime.datetime.fromtimestamp(earliestts/1000)
                latest = datetime.datetime.fromtimestamp(latestts/1000)
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
                        # with c.copyLock:
                        plugin = c.getPlugin('generator.'+sample.generator, sample)(sample)
                        self._pluginCache[sample.name] = plugin
                    # logger.info("GeneratorWorker %d generating %d events from '%s' to '%s'" % (self.num, count, \
                    #             datetime.datetime.strftime(earliest, "%Y-%m-%d %H:%M:%S"), \
                    #             datetime.datetime.strftime(latest, "%Y-%m-%d %H:%M:%S")))
                    plugin.gen(count, earliest, latest, samplename=samplename)
                else:
                    logger.debug("Received sentinel, shutting down GeneratorWorker %d" % self.num)
                    self.stop()
            except Queue.Empty:
                # Queue empty, do nothing... basically here to catch interrupts
                pass
        logger.info("GeneratorRealWorker %d stopped" % self.num)

def load():
    if globals()['threadmodel'] == 'thread':
        return GeneratorThreadWorker
    else:
        return GeneratorProcessWorker
