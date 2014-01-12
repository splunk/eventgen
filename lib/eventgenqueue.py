import Queue as PQueue, multiprocessing
import logging
import json
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
        elif queueing == 'zeromq':
            context = zmq.Context()
            self.receiver = context.socket(zmq.PULL)
            self.receiver.setsockopt(zmq.RCVHWM, depth)
            self.receiver.connect(queueUrl)
            self.sender = context.socket(zmq.PUSH)
            self.sender.setsockopt(zmq.SNDHWM, depth)
            self.sender.bind(queueUrl)
        self.queueing = queueing

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
            self.receiver.recv_json()
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


