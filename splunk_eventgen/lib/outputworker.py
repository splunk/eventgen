from __future__ import division
import os, sys
import logging
import logging.handlers
from collections import deque
import threading
from Queue import Empty
try:
    import billiard as multiprocessing
except ImportError, e:
    import multiprocessing
import json
import time
import marshal
import json
import datetime

class OutputProcessWorker(multiprocessing.Process):
    def __init__(self, num):
        self.worker = OutputRealWorker(num, self.stop)

        multiprocessing.Process.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        while c.generatorQueueSize.value() > 0 or c.outputQueueSize.value() > 0 or self.worker.working:
            time.sleep(0.1)
        logger.info("Stopping OutputProcessWorker %d" % self.worker.num)
        self.worker.stopping = True

class OutputThreadWorker(threading.Thread):
    def __init__(self, num):
        self.worker = OutputRealWorker(num, self.stop)

        threading.Thread.__init__(self)

    def run(self):
        self.worker.run()

    def stop(self):
        while c.generatorQueueSize.value() > 0 or c.outputQueueSize.value() > 0 or self.worker.working:
            time.sleep(0.1)
        logger.info("Stopping OutputThreadWorker %d" % self.worker.num)
        self.worker.stopping = True

class OutputRealWorker:

    def __init__(self, num, stop):
        from eventgenconfig import Config
        
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'OutputRealWorker', 'sample': 'null'})
        globals()['logger'] = adapter

        globals()['c'] = Config()

        self.stopping = False
        self.working = False

        self.num = num
        self.stop = stop

    def run(self):
        logger.debug("Starting OutputWorker %d" % self.num)
        if c.profiler:
            import cProfile
            globals()['threadrun'] = self.real_run
            cProfile.runctx("threadrun()", globals(), locals(), "eventgen_outputworker_%s" % self.num)
        else:
            self.real_run()

    def real_run(self):
        while not (self.stopping and c.outputQueueSize.value() == 0 and not self.working):
            try:
                # Grab a queue to be written for plugin name, get an instance of the plugin, and call the flush method
                # logger.debugv("Grabbing output items from python queue")
                name, queue = c.outputQueue.get(block=True, timeout=1.0)
                # logger.debugv("Got %d output items from python queue for plugin '%s'" % (len(queue), name))
                # name, queue = c.outputQueue.get(False, 0)
                c.outputQueueSize.decrement()
                # we throw an exception if the queue is emtpy, if no exception is thrown it must have work...
                self.working = True
                tmp = [len(s['_raw']) for s in queue]
                c.eventsSent.add(len(tmp))
                c.bytesSent.add(sum(tmp))
                if c.splunkEmbedded and len(tmp)>0:
                    metrics = logging.getLogger('eventgen_metrics')
                    metrics.error(json.dumps({'timestamp': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'), 
                            'sample': name, 'events': len(tmp), 'bytes': sum(tmp)}))
                tmp = None
                plugin = c.getPlugin(name)
                plugin.flush(deque(queue[:]))
            except Empty:
                # If the queue is empty, do nothing and start over at the top.  Mainly here to catch interrupts.
                # time.sleep(0.1)
                self.working = False
                # stop running if i'm not doing anything and there's nothing in the queue and I'm told to stop
                # and all generation has finished and stopped.
                if c.stopping.value() > 0 and c.pluginsStarted.value == 0:
                    self.stop()
                # pass
        logger.info("OutputRealWorker %d stopped" % self.num)
