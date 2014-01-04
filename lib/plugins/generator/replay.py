from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging

class ReplayGenerator(GeneratorPlugin):
    _rpevents = None

    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

        self.queueable = False

    def gen(self, count, earliest, latest):
        # Load sample from a file, using cache if possible, from superclass GeneratorPlugin
        self.loadSample()

        # Check to see if this is the first time we've run, or if we're at the end of the file
        # and we're running replay.  If so, we need to parse the whole file and/or setup our counters
        if self._rpevents == None:
            if self.sampletype == 'csv':
                self._rpevents = self.sampleDict
            else:
                if self.breaker != c.breaker:
                    self._rpevents = []
                    lines = '\n'.join(sampleLines)
                    breaker = re.search(self.breaker, lines)
                    currentchar = 0
                    while breaker:
                        self._rpevents.append(lines[currentchar:breaker.start(0)])
                        lines = lines[breaker.end(0):]
                        currentchar += breaker.start(0)
                        breaker = re.search(self.breaker, lines)
                else:
                    self._rpevents = sampleLines
            self._currentevent = 0

        # If we are replaying then we need to set the current sampleLines to the event
        # we're currently on
        if self.sampletype == 'csv':
            self.sampleDict = [ self._rpevents[self._currentevent] ]
            self.sampleLines = [ self._rpevents[self._currentevent]['_raw'].decode('string_escape') ]
        else:
            self.sampleLines = [ self._rpevents[self._currentevent] ]
        self._currentevent += 1
        # If we roll over the max number of lines, roll over the counter and start over
        if self._currentevent >= len(self._rpevents):
            logger.debug("At end of the sample file, starting replay from the top")
            self._currentevent = 0
            self._lastts = None

        # Ensure all lines have a newline
        for i in xrange(0, len(self.sampleLines)):
            if self.sampleLines[i][-1] != '\n':
                self.sampleLines[i] += '\n'




def load():
    return ReplayGenerator