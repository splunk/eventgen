try:
	import zmq
except ImportError, e:
	pass
import threading

class ZMQProxy(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)

	def run(self):
		context = zmq.Context(1)
		# Socket facing clients
		frontend = context.socket(zmq.PULL)
		frontend.bind("tcp://*:5557")

		# Socket facing services
		backend  = context.socket(zmq.PUSH)
		backend.bind("tcp://*:5558")

		zmq.device(zmq.QUEUE, frontend, backend)

		# We never get here
		frontend.close()
		backend.close()
		context.term()