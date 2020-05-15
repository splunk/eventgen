import sys
import json

from splunk_eventgen.lib.outputplugin import OutputPlugin


class PregenOutputPlugin(OutputPlugin):
    name = "pregen"
    MAXQUEUELENGTH = 10
    useOutputQueue = True

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

    def flush(self, q):
        out = ""
        if len(q) > 0:
            m = q.pop(0)
            while m:
                out  = json.dumps(m)
                sys.stdout.write(f"{out}\n")
                try:
                    m = q.pop(0)
                except IndexError:
                    m = False            
            sys.stdout.flush()


def load():
    """Returns an instance of the plugin"""
    return PregenOutputPlugin
