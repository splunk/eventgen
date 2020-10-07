from collections import deque

from splunk_eventgen.lib.logging_config import logger, metrics_logger


class OutputPlugin(object):
    name = "OutputPlugin"

    def __init__(self, sample, output_counter=None):
        self._app = sample.app
        self._sample = sample
        self._outputMode = sample.outputMode
        self.events = None
        logger.debug(
            "Starting OutputPlugin for sample '%s' with output '%s'"
            % (self._sample.name, self._sample.outputMode)
        )
        self._queue = deque([])
        self.output_counter = output_counter

    def __str__(self):
        """Only used for debugging, outputs a pretty printed representation of this output"""
        # Eliminate recursive going back to parent
        # temp = dict([(key, value) for (key, value) in self.__dict__.items() if key != '_c'])
        # return pprint.pformat(temp)
        return ""

    def __repr__(self):
        return self.__str__()

    def set_events(self, events):
        self.events = events

    def updateConfig(self, config):
        self.config = config

    def run(self):
        if self.events:
            self.flush(self.events)
        if self.output_counter is not None:
            self.output_counter.collect(
                len(self.events), sum([len(e["_raw"]) for e in self.events])
            )
            metrics_logger.info(
                "Current Counts: {0}".format(self.output_counter.__dict__)
            )
        self.events = None
        self._output_end()

    def _output_end(self):
        pass


def load():
    return OutputPlugin
