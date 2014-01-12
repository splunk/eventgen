import Queue as PQueue
try:
    import billiard as multiprocessing
except ImportError, e:
    import multiprocessing
import logging
import json
import threading
try:
    import zmq
    import errno
except ImportError, e:
    pass

class Queue:
    def __init__(self, depth, queueing, threading, queueUrl):
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        logger.info("Creating Queue of depth %d, queueing %s, threading %s, queueUrl %s" % \
                (depth, queueing, threading, queueUrl))
        if queueing == 'python':
            if threading == 'thread':
                self.q = PQueue.Queue(depth)
            else:
                self.q = multiprocessing.Queue(depth)

        self.queueing = queueing
        self.depth = depth
        self.queueUrl = queueUrl

    def initMQ(self, worker=True):
        if self.worker:
            context = zmq.Context()
            self.receiver = context.socket(zmq.PULL)
            self.receiver.setsockopt(zmq.RCVHWM, self.depth)
            self.receiver.bind(self.queueUrl)
            self.sender = context.socket(zmq.PUSH)
            self.sender.setsockopt(zmq.SNDHWM, self.depth)
            self.sender.bind(self.queueUrl)
        else:
            context = zmq.Context()
            self.receiver = context.socket(zmq.PULL)
            self.receiver.setsockopt(zmq.RCVHWM, self.depth)
            self.receiver.bind(self.queueUrl)
            self.sender = context.socket(zmq.PUSH)
            self.sender.setsockopt(zmq.SNDHWM, self.depth)
            self.sender.bind(self.queueUrl)

    def put(self, item, block, timeout):
        if self.queueing == 'python':
            self.q.put(item, block, timeout)
        elif self.queueing == 'zeromq':
            self.sender.send_json(item)
            # while True:
            #     try:
            #         self.sender.send_json(item)
            #     except zmq.ZMQError as e:
            #         if e.errno == errno.EINTR:
            #             # interrupted, try again
            #             continue
            #         else:
            #             # real error, raise it
            #             raise
            


    def get(self, block, timeout):
        if self.queueing == 'python':
            return self.q.get(block, timeout)
        elif self.queueing == 'zeromq':
            return self.receiver.recv_json()
            # while True:
            #     try:
            #         return self.receiver.recv_json()
            #     except zmq.ZMQError as e:
            #         if e.errno == errno.EINTR:
            #             # interrupted, try again
            #             continue
            #         else:
            #             # real error, raise it
            #             raise


