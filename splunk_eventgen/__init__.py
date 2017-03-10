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
        self._create_timer_threadpool()

    def _create_timer_threadpool(self, threadcount=100):
        self.sampleQueue = Queue(maxsize=0)
        num_threads = threadcount
        for i in range(num_threads):
            worker = Thread(target=self._worker_do_work, args=(self.sampleQueue, ))
            worker.setDaemon(True)
            worker.start()

    def _create_generator_pool(self):
        pass

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
                t = Timer(1.0, sample=s, config=self.config)
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
