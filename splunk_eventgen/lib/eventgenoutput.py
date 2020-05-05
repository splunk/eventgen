import datetime
import time
from queue import Full

from splunk_eventgen.lib.logging_config import logger, metrics_logger


# TODO: Figure out why we load plugins from here instead of the base plugin class.
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
        self.output_counter = None

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        # temp = dict([(key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def _update_outputqueue(self, queue):
        self.outputQueue = queue

    def setOutputCounter(self, output_counter):
        self.output_counter = output_counter

    def updateConfig(self, config):
        self.config = config
        # TODO: This is where the actual output plugin is loaded, and pushed out.  This should be handled way better...
        self.outputPlugin = self.config.getPlugin(
            "output." + self._sample.outputMode, self._sample
        )

    def send(self, msg):
        """
        Adds msg to the output buffer, flushes if buffer is more than MAXQUEUELENGTH
        """
        ts = (
            self._sample.timestamp
            if self._sample.timestamp is not None
            else self._sample.now()
        )
        self._queue.append(
            {
                "_raw": msg,
                "index": self._sample.index,
                "source": self._sample.source,
                "sourcetype": self._sample.sourcetype,
                "host": self._sample.host,
                "hostRegex": self._sample.hostRegex,
                "_time": int(time.mktime(ts.timetuple())),
            }
        )

        if len(self._queue) >= self.MAXQUEUELENGTH:
            self.flush()

    def bulksend(self, msglist):
        """
        Accepts list, msglist, and adds to the output buffer.  If the buffer exceeds MAXQUEUELENGTH, then flush.
        """
        try:
            self._queue.extend(msglist)
            if len(self._queue) >= self.MAXQUEUELENGTH:
                self.flush()
        except Exception as e:
            # We don't want to exit if there's a single bad event
            logger.error(
                "Caught Exception {} while appending/flushing output queue. There may be a ".format(
                    e
                )
                + "faulty event or token replacement in your sample."
            )

    def flush(self, endOfInterval=False):
        """
        Flushes output buffer, unless endOfInterval called, and then only flush if we've been called
        more than maxIntervalsBeforeFlush tunable.
        """
        flushing = True
        if flushing:
            q = self._queue
            logger.debug(
                "Flushing queue for sample '%s' with size %d"
                % (self._sample.name, len(q))
            )
            self._queue = []
            outputer = self.outputPlugin(self._sample, self.output_counter)
            outputer.updateConfig(self.config)
            outputer.set_events(q)
            # When an outputQueue is used, it needs to run in a single threaded nature which requires to be put back
            # into the outputqueue so a single thread worker can execute it. When an outputQueue is not used, it can be
            # ran by multiple processes or threads. Therefore, no need to put the outputer back into the Queue. Just
            # execute it.
            # if outputPlugin must be used for useOutputQueue, use outputQueue regardless of user config useOutputQueue:
            if self.outputPlugin.useOutputQueue or self.config.useOutputQueue:
                try:
                    self.outputQueue.put(outputer)
                except Full:
                    logger.warning("Output Queue full, looping again")
            else:
                if self.config.splunkEmbedded:
                    tmp = [len(s["_raw"]) for s in q]
                    if len(tmp) > 0:
                        metrics_logger.info(
                            {
                                "timestamp": datetime.datetime.strftime(
                                    datetime.datetime.now(), "%Y-%m-%d %H:%M:%S"
                                ),
                                "sample": self._sample.name,
                                "events": len(tmp),
                                "bytes": sum(tmp),
                            }
                        )
                    tmp = None
                outputer.run()
            q = None
