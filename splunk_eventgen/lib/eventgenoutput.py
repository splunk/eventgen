from __future__ import division
import logging
import logging.handlers
from collections import deque
from Queue import Full
import json
import time

#TODO: Figure out why we load plugins from here instead of the base plugin class.
class Output(object):
    """
    Base class which loads output plugins in BASE_DIR/lib/plugins/output and handles queueing
    """

    def __init__(self, sample):
        self.__plugins = {}

        # Logger already setup by config, just get an instance
        logobj = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logobj, {'module': 'Output', 'sample': sample.name})
        globals()['logger'] = adapter

        self._app = sample.app
        self._sample = sample
        self._outputMode = sample.outputMode
        self.MAXQUEUELENGTH = sample.maxQueueLength
        
        self._queue = deque([])
        self._workers = [ ]


    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def _update_outputqueue(self, queue):
        pass
        #self._queue = queue

    def updateConfig(self, config):
        self.confg = config

    def send(self, msg):
        """
        Adds msg to the output buffer, flushes if buffer is more than MAXQUEUELENGTH
        """
        ts = self._sample.timestamp if self._sample.timestamp != None else self._sample.now()
        self._queue.append({'_raw': msg, 'index': self._sample.index,
                        'source': self._sample.source, 'sourcetype': self._sample.sourcetype,
                        'host': self._sample.host, 'hostRegex': self._sample.hostRegex,
                        '_time': int(time.mktime(ts.timetuple()))})

        if len(self._queue) >= self.MAXQUEUELENGTH:
            self.flush()

    def bulksend(self, msglist):
        """
        Accepts list, msglist, and adds to the output buffer.  If the buffer exceeds MAXQUEUELENGTH, then flush.
        """
        self._queue.extend(msglist)

        if len(self._queue) >= self.MAXQUEUELENGTH:
            self.flush()

    def flush(self, endOfInterval=False):
        """
        Flushes output buffer, unless endOfInterval called, and then only flush if we've been called
        more than maxIntervalsBeforeFlush tunable.
        """
        flushing = False
        #TODO: Fix interval flushing somehow with a queue, not sure I even want to support this feature anymore.
        '''if endOfInterval:
            logger.debugv("Sample calling flush, checking increment against maxIntervalsBeforeFlush")
            c.intervalsSinceFlush[self._sample.name].increment()
            if c.intervalsSinceFlush[self._sample.name].value() >= self._sample.maxIntervalsBeforeFlush:
                logger.debugv("Exceeded maxIntervalsBeforeFlush, flushing")
                flushing = True
                c.intervalsSinceFlush[self._sample.name].clear()
            else:
                logger.debugv("Not enough events to flush, passing flush routine.")
        else:
            logger.debugv("maxQueueLength exceeded, flushing")
            flushing = True'''

        #TODO: This is set this way just for the time being while I decide if we want this feature.
        flushing = True
        if flushing:
            # q = deque(list(self._queue)[:])
            q = list(self._queue)
            logger.debugv("Flushing queue for sample '%s' with size %d" % (self._sample.name, len(q)))
            self._queue.clear()
            if self.config.useOutputQueue:
                while True:
                    try:
                        c.outputQueue.put((self._sample.name, q), block=True, timeout=1.0)
                        c.outputQueueSize.increment()
                        # logger.info("Outputting queue")
                        break
                    except Full:
                        logger.warning("Output Queue full, looping again")
                        pass
            else:
                tmp = [len(s['_raw']) for s in q]
                c.eventsSent.add(len(tmp))
                c.bytesSent.add(sum(tmp))
                if c.splunkEmbedded and len(tmp)>0:
                    metrics = logging.getLogger('eventgen_metrics')
                    metrics.error(json.dumps({'timestamp': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'), 
                            'sample': name, 'events': len(tmp), 'bytes': sum(tmp)}))
                tmp = None
                plugin = c.getPlugin(self._sample.name)
                plugin.flush(deque(q[:]))
