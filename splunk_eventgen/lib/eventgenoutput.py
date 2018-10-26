from __future__ import division
import logging
import logging.handlers
from Queue import Full
import json
import time
import datetime

#TODO: Figure out why we load plugins from here instead of the base plugin class.
class Output(object):
    """
    Base class which loads output plugins in BASE_DIR/lib/plugins/output and handles queueing
    """

    def __init__(self, sample):
        self.__plugins = {}
        self._app = sample.app
        self._sample = sample
        self._outputMode = sample.outputMode
        self.MAXQUEUELENGTH = sample.maxQueueLength
        self._queue = []
        self._setup_logging()


    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        temp = dict([ (key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    # loggers can't be pickled due to the lock object, remove them before we try to pickle anything.
    def __getstate__(self):
        temp = self.__dict__
        if getattr(self, 'logger', None):
            temp.pop('logger', None)
        return temp

    def __setstate__(self, d):
        self.__dict__ = d
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger('eventgen')

    def _update_outputqueue(self, queue):
        self.outputQueue = queue

    def updateConfig(self, config):
        self.config = config
        #TODO: This is where the actual output plugin is loaded, and pushed out.  This should be handled way better...
        self.outputPlugin = self.config.getPlugin('output.' + self._sample.outputMode, self._sample)

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
            q = self._queue
            self.logger.debug("Flushing queue for sample '%s' with size %d" % (self._sample.name, len(q)))
            self._queue = []
            outputer = self.outputPlugin(self._sample)
            outputer.updateConfig(self.config)
            outputer.set_events(q)
            # When an outputQueue is used, it needs to run in a single threaded nature which requires to be put back into the outputqueue so a single thread worker can execute it.
            # When an outputQueue is not used, it can be ran by multiple processes or threads. Therefore, no need to put the outputer back into the Queue. Just execute it.
            # if outputPlugin must be used for useOutputQueue, use outputQueue regardless of user config useOutputQueue:
            if self.outputPlugin.useOutputQueue or self.config.useOutputQueue:
                try:
                    self.outputQueue.put(outputer)
                except Full:
                    self.logger.warning("Output Queue full, looping again")
            else:
                tmp = [len(s['_raw']) for s in q]
                # TODO: clean out eventsSend and bytesSent if they are not being used in config
                # self.config.eventsSent.add(len(tmp))
                # self.config.bytesSent.add(sum(tmp))
                if self.config.splunkEmbedded and len(tmp)>0:
                    metrics = logging.getLogger('eventgen_metrics')
                    metrics.info({'timestamp': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'),
                            'sample': self._sample.name, 'events': len(tmp), 'bytes': sum(tmp)})
                tmp = None
                outputer.run()
