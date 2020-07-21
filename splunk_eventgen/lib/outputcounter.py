import time

from splunk_eventgen.lib.logging_config import logger


class OutputCounter(object):
    """
    This object is used as a global variable for outputer to collect how many events and how much size of
    raw events egx has generated, and use them to calculate a real-time throughput.
    """

    def __init__(self):
        self.event_size_1_min = 0
        self.event_count_1_min = 0
        self.current_time = time.time()
        self.throughput_count = 0
        self.throughput_volume = 0
        self.total_output_volume = 0
        self.total_output_count = 0

    def update_throughput(self, timestamp):
        # B/s, count/s
        delta_time = timestamp - self.current_time
        self.throughput_volume = self.event_size_1_min / (delta_time)
        self.throughput_count = self.event_count_1_min / (delta_time)
        self.current_time = timestamp
        self.event_count_1_min = 0
        self.event_size_1_min = 0
        logger.debug(
            "Current throughput is {} B/s, {} count/s".format(
                self.throughput_volume, self.throughput_count
            )
        )

    def collect(self, event_count, event_size):
        timestamp = time.time()
        self.total_output_count += event_count
        self.total_output_volume += event_size
        self.event_count_1_min += event_count
        self.event_size_1_min += event_size
        if timestamp - self.current_time >= 60:
            # update the throughput per mins
            self.update_throughput(timestamp)
