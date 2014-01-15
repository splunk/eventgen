import multiprocessing
import threading

class Counter:
    def __init__(self, initval=0, model='thread'):
        if model == 'thread':
            self.lock = threading.Lock()
            
            class Value:
                def __init__(self, value=None):
                    self.value = value
            self.val = Value(initval)
            self.incval = Value(0)
            self.decval = Value(0)
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

    def valueAndClear(self):
        with self.lock:
            val = self.val.value
            self.val.value = 0
            return val

    def totalincrements(self):
        with self.lock:
            return self.incval.value

    def totaldecrements(self):
        with self.lock:
            return self.decval.value

    def add(self, val):
        with self.lock:
            self.val.value += val

    def sub(self, val):
        with self.lock:
            self.val.value -= val