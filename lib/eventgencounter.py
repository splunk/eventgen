import multiprocessing
import threading

class Counter:
    def __init__(self, initval=0, model='thread'):
        if model == 'thread':
            self.lock = threading.Lock()
            # self.val = initval
            # self.incval = 0
            # self.decval = 0
        else:
            self.lock = multiprocessing.Lock()
            
        self.val = multiprocessing.RawValue('i', initval)
        self.incval = multiprocessing.RawValue('i', 0)
        self.decval = multiprocessing.RawValue('i', 0)

    def increment(self):
        with self.lock:
            self.val.value += 1
            self.incval.value += 1

    def decrement(self):
        with self.lock:
            self.val.value -= 1
            self.decval.value += 1

    def value(self):
        with self.lock:
            return self.val.value

    def totalincrements(self):
        with self.lock:
            return self.incval.value

    def totaldecrements(self):
        with self.lock:
            return self.decval.value