from __future__ import print_function

import datetime
import pprint
import sys

from splunk_eventgen.lib.outputplugin import OutputPlugin


class CounterOutputPlugin(OutputPlugin):
    name = "counter"
    MAXQUEUELENGTH = 1000
    useOutputQueue = True

    dataSizeHistogram = {}
    eventCountHistogram = {}
    flushCount = 0
    lastPrintAt = 0

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

    def flush(self, q):
        CounterOutputPlugin.flushCount += 1
        for e in q:
            ts = datetime.datetime.fromtimestamp(int(e["_time"]))
            text = e["_raw"]
            day = ts.strftime("%Y-%m-%d")
            CounterOutputPlugin.dataSizeHistogram[
                day
            ] = CounterOutputPlugin.dataSizeHistogram.get(day, 0) + len(text)
            CounterOutputPlugin.eventCountHistogram[day] = (
                CounterOutputPlugin.eventCountHistogram.get(day, 0) + 1
            )

    def _output_end(self):
        if CounterOutputPlugin.flushCount - CounterOutputPlugin.lastPrintAt > 0:
            self._print_info("----- print the output histogram -----")
            self._print_info("--- data size histogram ---")
            self._print_info(pprint.pformat(CounterOutputPlugin.dataSizeHistogram))
            self._print_info("--- event count histogram ---")
            self._print_info(pprint.pformat(CounterOutputPlugin.eventCountHistogram))
            CounterOutputPlugin.lastPrintAt = CounterOutputPlugin.flushCount

    def _print_info(self, msg):
        print("{} {}".format(datetime.datetime.now(), msg), file=sys.stderr)


def load():
    """Returns an instance of the plugin"""
    return CounterOutputPlugin
