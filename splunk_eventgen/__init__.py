#!/usr/bin/env python
# encoding: utf-8
from lib.eventgenconfig import Config
from lib.eventgentimer import Timer
import time
import logging
import os
from Queue import Queue
from threading import Thread

__version__ = "0.6.0"

if __name__ == "__main__":
    print __version__


class EventGenerator(object):
    def __init__(self, args):
        '''
        This object will allow you to generate and control eventgen.  It should be handed the parse_args object
        from __main__ and will hand the argument object to the config parser of eventgen5.  This will provide the
        bridge to using the old code with the newer style.  As things get moved from the config parser, this should
        start to control all of the configuration items that are global, and the config object should only handle the
        localized .conf entries.
        :param args: __main__ parse_args() object.
        '''
        self.config = None
        self.args = args
        if getattr(self.args, "configfile"):
            self.reload_conf()
        # Logger is setup by Config, just have to get an instance
        # TODO: The config object shouldn't setup the logger, this should.  It needs to be moved here.
        self.logobj = logging.getLogger('eventgen')
        from lib.eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(self.logobj, {'sample': 'null', 'module': 'main'})
        self.logger = adapter
        self._create_generator_pool()
        self._create_timer_threadpool()
        self._create_output_threadpool()

    def _create_timer_threadpool(self, threadcount=100):
        '''
        Timer threadpool is used to contain the timer object for each sample.  A timer will stay active
        until the end condition is met for the sample.  If there is no end condition, the timer will exist forever.
        :param threadcount: is how many active timers we want to allow inside of eventgen.  Default 100.  If someone
                            has over 100 samples, additional samples won't run until the first ones end.
        :return:
        '''
        self.sampleQueue = Queue(maxsize=0)
        num_threads = threadcount
        for i in range(num_threads):
            worker = Thread(target=self._worker_do_work, args=(self.sampleQueue, ))
            worker.setDaemon(True)
            worker.start()

    def _create_output_threadpool(self, threadcount=1):
        '''
        the output thread pool is used for output plugins that need to control file locking, or only have 1 set thread
        to send all the data out of.  this FIFO queue just helps make sure there are file collisions or write collisions.
        There's only 1 active thread for this queue, if you're ever considering upping this, don't.  Just shut off the
        outputQueue and let each generator directly output it's data.
        :param threadcount: is how many active output threads we want to allow inside of eventgen.  Default 1
        :return:
        '''
        #TODO: Make this take the config param and figure out what we want to do with this.
        self.outputQueue = Queue(maxsize=10000)
        num_threads = threadcount
        for i in range(num_threads):
            worker = Thread(target=self._worker_do_work, args=(self.outputQueue, ))
            worker.setDaemon(True)
            worker.start()

    def _create_generator_pool(self, workercount=10):
        '''
        The generator pool has two main options, it can run in multiprocessing or in threading.  We check the argument
        from configuration, and then build the appropriate queue type.  Each time a timer runs for a sample, if the
        timer says it's time to generate, it will create a new generator plugin object, and place it in this queue.
        :param workercount: is how many active workers we want to allow inside of eventgen.  Default 10.  If someone
                            has over 10 generators working, additional samples won't run until the first ones end.
        :return:
        '''
        if self.args.multiprocess:
            import multiprocessing
            self.workerQueue = multiprocessing.Queue(maxsize=500)
            self.workerPool = multiprocessing.Pool(processes=workercount,
                                                   initializer=self._worker_do_work,
                                                   initargs=(self.workerQueue,))
        else:
            self.workerQueue = Queue(maxsize=500)
            worker_threads = workercount
            for i in range(worker_threads):
                worker = Thread(target=self._worker_do_work, args=(self.workerQueue, ))
                worker.setDaemon(True)
                worker.start()

    @staticmethod
    def _worker_do_work(queue):
        while True:
            item = queue.get()
            item.run()
            queue.task_done()

    def start(self):
        self.logger.info('Starting eventgen')

        for s in self.config.samples:
            if s.interval > 0 or s.mode == 'replay':
                #TODO: Move these timers into a threading queue, and have them handle sticking things into the multiprocess queue
                self.logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app) )
                # This is where the timer is finally sent to a queue to be processed.  Needs to move to this object.
                t = Timer(1.0, sample=s, config=self.config, genqueue=self.workerQueue)
                self.sampleQueue.put(t)
        try:
            ## Only need to start timers once
            if os.name != "nt":
                self.config.set_exit_handler(self.config.handle_exit)
            # Every 5 seconds, get values and output basic statistics about our operations
            #TODO: Figure out how to do this better...
            #generatorsPerSec = (generatorDecrements - generatorQueueCounter) / 5
            #outputtersPerSec = (outputDecrements - outputQueueCounter) / 5
            #outputQueueCounter = outputDecrements
            #generatorQueueCounter = generatorDecrements
            #self.logger.info('OutputQueueDepth=%d  GeneratorQueueDepth=%d GeneratorsPerSec=%d OutputtersPerSec=%d' % (self.config.outputQueueSize.value(), self.config.generatorQueueSize.value(), generatorsPerSec, outputtersPerSec))
            #kiloBytesPerSec = self.config.bytesSent.valueAndClear() / 5 / 1024
            #gbPerDay = (kiloBytesPerSec / 1024 / 1024) * 60 * 60 * 24
            #eventsPerSec = self.config.eventsSent.valueAndClear() / 5
            #self.logger.info('GlobalEventsPerSec=%s KilobytesPerSec=%1f GigabytesPerDay=%1f' % (eventsPerSec, kiloBytesPerSec, gbPerDay))

        except KeyboardInterrupt:
            self.config.handle_exit()


    def stop(self):
        # empty the sample queue:
        self.config.stopping = True

    def reload_conf(self, config=None):
        '''
        This method will allow a user to supply a new .conf file for generation and reload the sample files.
        :param config:
        :return:
        '''
        if config:
            self.args.configfile = config
        self.config = Config(self.args)
        self.config.parse()
