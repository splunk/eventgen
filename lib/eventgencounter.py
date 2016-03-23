import multiprocessing
import threading

class Counter:
    """
    Provides a Counter which will work utilizing either threading or multiprocessing.
    """

    def __init__(self, initval=0, model='thread'):
        """
        Initialize the counter with initval.

        Chooses threading model based on passed thread parameter.
            'thread'          : Utlizes threading.Lock()
            'multiprocessing' : Utilizes multiprocessing.Lock()
        """

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
            
            self.val = multiprocessing.RawValue('l', initval)
            self.incval = multiprocessing.RawValue('l', 0)
            self.decval = multiprocessing.RawValue('l', 0)

    def increment(self):
        """
        Gets lock and increments value
        """
        with self.lock:
            self.val.value += 1
            self.incval.value += 1

    def decrement(self):
        """
        Gets lock and decrements value
        """
        with self.lock:
            self.val.value -= 1
            self.decval.value += 1

    def value(self):
        """
        Gets lock and returns value
        """
        with self.lock:
            return self.val.value

    def valueAndClear(self):
        """
        Gets lock, returns value and resets value to zero
        """
        with self.lock:
            val = self.val.value
            self.val.value = 0
            return val

    def clear(self):
        """
        Gets lock, sets value to 0
        """
        with self.lock:
            self.val.value = 0

    def totalincrements(self):
        """
        Gets lock, returns total number of increments since instantiation
        """
        with self.lock:
            return self.incval.value

    def totaldecrements(self):
        """
        Gets lock, returns total number of decrements since instantiation
        """
        with self.lock:
            return self.decval.value

    def add(self, val):
        """
        Gets lock, adds value to the counter
        """
        with self.lock:
            self.val.value += val

    def sub(self, val):
        """
        Gets lock, subtracts value from the counter
        """
        with self.lock:
            self.val.value -= val