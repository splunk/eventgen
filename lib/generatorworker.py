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
import datetime, time
import marshal
import random

class GeneratorProcessWorker(multiprocessing.Process):
    def __init__(self, num, q1, q2):
        self.worker = GeneratorRealWorker(num, q1, q2, self.stop)

        multiprocessing.Process.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        while c.generatorQueueSize.value() > 0 or self.worker.working:
            time.sleep(0.1)
        for (name, plugin) in self.worker._pluginCache.iteritems():
            plugin._out.flush()
        self.worker.stopping = True
        logger.info("Stopping GeneratorProcessWorker %d" % self.worker.num)

class GeneratorThreadWorker(threading.Thread):
    def __init__(self, num, q1, q2):
        self.worker = GeneratorRealWorker(num, q1, q2, self.stop)

        threading.Thread.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        while c.generatorQueueSize.value() > 0 or self.worker.working:
            time.sleep(0.1)
        for (name, plugin) in self.worker._pluginCache.iteritems():
            plugin._out.flush()
        self.worker.stopping = True
        c.pluginsStarted.decrement()
        logger.info("Stopping GeneratorThreadWorker %d" % self.worker.num)

class GeneratorRealWorker:

    def __init__(self, num, q1, q2, stop):
        from eventgenconfig import Config
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'GeneratorRealWorker', 'sample': 'null'})
        globals()['logger'] = adapter

        globals()['c'] = Config()

        self.stopping = False
        self.working = False

        self._pluginCache = { }

        self.num = num
        c.generatorQueue = q1
        c.outputQueue = q2
        self.stop = stop
        
        # 10/9/15 CS Prime plugin cache to avoid concurrency bugs when creating local copies of samples
        time.sleep(random.randint(0, 100)/1000)
        logger.debug("Priming plugin cache for GeneratorWorker%d" % num)
        with c.copyLock:
            while c.pluginsStarting.value() > 0:
                logger.debug("Waiting for exclusive lock to start for GeneratorWorker%d" % num)
                time.sleep(random.randint(0, 100)/1000)
            
            c.pluginsStarting.increment()
            for sample in c.samples:
                plugin = c.getPlugin('generator.'+sample.generator, sample)
                if plugin.queueable:
                    p = plugin(sample)
                    self._pluginCache[sample.name] = p
                    
            c.pluginsStarting.decrement()
            c.pluginsStarted.increment()
                    
                

    def run(self):
        logger.debug("Starting GeneratorWorker %d" % self.num)
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
        while not (self.stopping and c.generatorQueueSize.value() == 0 and not self.working):
            try:
                # Grab item from the queue to generate, grab an instance of the plugin, then generate
                # logger.debugv("Grabbing generator items from python queue")
                samplename, count, earliestts, latestts = c.generatorQueue.get(block=True, timeout=1.0)
                # logger.debugv("Got a generator items from python queue for sample '%s'" % (samplename))
                earliest = datetime.datetime.fromtimestamp(earliestts/10**6)
                latest = datetime.datetime.fromtimestamp(latestts/10**6)
                c.generatorQueueSize.decrement()
                if samplename != None:
                    self.working = True
                    if samplename in self._pluginCache:
                        plugin = self._pluginCache[samplename]
                        plugin.updateSample(samplename)
                    else:
                        for s in c.samples:
                            if s.name == samplename:
                                sample = s
                                break
                        plugin = c.getPlugin('generator.'+sample.generator, sample)(sample)
                        self._pluginCache[sample.name] = plugin
                    # logger.info("GeneratorWorker %d generating %d events from '%s' to '%s'" % (self.num, count, \
                    #             datetime.datetime.strftime(earliest, "%Y-%m-%d %H:%M:%S"), \
                    #             datetime.datetime.strftime(latest, "%Y-%m-%d %H:%M:%S")))
                    logger.debugv("Generating %d for sample '%s' stopping: %s" % (count, samplename, self.stopping))
                    plugin.gen(count, earliest, latest, samplename=samplename)
                    self.working = False
                else:
                    logger.debug("Received sentinel, shutting down GeneratorWorker %d" % self.num)
                    self.stop()
            except Queue.Empty:
                self.working = False
                # stop running if i'm not doing anything and there's nothing in the queue and I'm told to stop!
                if c.stopping.value() > 0 :
                    self.stop()
                # Queue empty, do nothing... basically here to catch interrupts
                # pass
        logger.info("GeneratorRealWorker %d stopped" % self.num)