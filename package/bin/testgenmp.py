import sys
import billiard as multiprocessing
import Queue
import cProfile
# while True:
#     print '111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111'

#while True:
#   print '2014-01-05 23:07:08 WINDBAG Event 1 of 100000'


class Getter(multiprocessing.Process):
    def __init__(self, q):
        self.q = q
        self._q = []

        multiprocessing.Process.__init__(self)


    def flush(self):
        buf = '\n'.join(self._q)
        # buf = ''
        # for x in self._q:
        #     buf += x+'\n'
        sys.stdout.write(buf)

    def run(self):
        globals()['threadrun'] = self.real_run
        cProfile.runctx("threadrun()", globals(), locals(), "prof_getter")

    def real_run(self):
        while True:
            try:
                self._q = self.q.get(block=True, timeout=1.0)
                self.flush()
            except Queue.Empty:
                pass


class Putter(multiprocessing.Process):
    def __init__(self, q):
        self.q = q

        multiprocessing.Process.__init__(self)


    def run(self):
        globals()['threadrun'] = self.real_run
        cProfile.runctx("threadrun()", globals(), locals(), "prof_putter")

    def real_run(self):
        while True:
            l = [ ]
            # for i in xrange(20000):
            #     l.append('2014-01-05 23:07:08 WINDBAG Event 1 of 100000')
            l = ['2014-01-05 23:07:08 WINDBAG Event 1 of 100000' for i in xrange(20000)]

            try:
                self.q.put(l, block=True, timeout=1.0)
            except Queue.Full:
                pass


if __name__ == '__main__':
    print 'running!'
    q = multiprocessing.Queue(20)
    g = Getter(q)
    # g.daemon = True
    p = Putter(q)
    # p.daemon = True

    p.start()
    g.start()

