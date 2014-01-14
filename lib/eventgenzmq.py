try:
    import zmq
except ImportError, e:
    pass
import threading
import logging

class ZMQProxy(threading.Thread):
    def __init__(self):
        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

        threading.Thread.__init__(self)

    def run(self):
        context = c.zmqcontext
        # Socket facing clients
        frontend = context.socket(zmq.PULL)
        frontend.bind("tcp://*:5557")

        # Socket facing services
        backend  = context.socket(zmq.PUSH)
        backend.bind("tcp://*:5558")

        # zmq.device(zmq.QUEUE, frontend, backend)
        zmq.proxy(frontend, backend)

        # try:
        #     n = 0
        #     while True:
        #         message = frontend.recv()
        #         backend.send(message)
        #         n += 1
        #         if (n % 10) == 0:
        #             logger.info('%d messages proxied' % n)
        # finally:
        #     frontend.close()
        #     backend.close()
        #     context.term()

        # We never get here
        frontend.close()
        backend.close()
        context.term()