import Queue as PQueue
try:
    import billiard as multiprocessing
except ImportError, e:
    import multiprocessing
import logging
import json
import threading

class Queue:
    """
    Abstraction of threading or multiprocessing Queue
    """
    def __init__(self, depth, threading):
        # Logger already setup by config, just get an instance
        logobj = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logobj, {'module': 'Queue', 'sample': 'null'})
        self.logger = adapter

        # logger.info("Creating Queue of depth %d, threading %s" % (depth, threading))
        if threading == 'thread':
            self.q = PQueue.Queue(depth)
        else:
            self.q = multiprocessing.Manager().Queue(depth)

        self.depth = depth

    def put(self, item, block, timeout):
        """
        Put item in queue, with block and timeout passed through
        """
        self.q.put(item, block, timeout)

    def get(self, block, timeout):
        """
        Get an item from the queue, with block and timeout passed through
        """
        return self.q.get(block, timeout)


