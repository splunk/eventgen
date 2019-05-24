from __future__ import division

import datetime
import logging
import logging.handlers
import random
from config import ConfigRater


class SplitRater(ConfigRater):
    name = 'SplitRater'
    stopping = False

    def __init__(self, sample):

        self._setup_logging()
        self.logger.debug('Starting SplitterRater for %s' % sample.name if sample is not None else "None")
        self.sample = sample

    def rate(self):
        self._sample.count = int(self._sample.count)
        # Let generators handle infinite count for themselves
        base_count = self.base_rater.rate()
        #TODO: Subdivide down based on the cores.
        return base_count


def load():
    return SplitRater
