import datetime
from datetime import timedelta

from splunk_eventgen.lib.generatorplugin import GeneratorPlugin
from splunk_eventgen.lib.logging_config import logger


class CounterGenerator(GeneratorPlugin):
    validSettings = ["count_template", "start_count", "end_count", "count_by"]
    defaultableSettings = ["count_template", "start_count", "end_count", "count_by"]

    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)
        self.start_count = 0.0
        self.end_count = 0.0
        self.count_by = 1.0
        self.count_template = (
            "{event_ts}-0700 Counter for sample:{samplename}, "
            + "Now processing event counting {loop_count} of {max_loop} cycles. Counter Values:"
            + " Start_Count: {start_count} Current_Counter:{current_count}"
            + " End_Count:{end_count} Counting_By: {count_by}"
        )

    def update_start_count(self, target):
        try:
            if "." in target:
                self.start_count = round(float(target), 5)
            else:
                self.start_count = int(target)
        except Exception:
            logger.warn(
                "Failed setting start count to {0}.  Make sure start_count is an int/float".format(
                    target
                )
            )
            logger.warn("Setting start_count to 0")
            self.start_count = 0

    def update_end_count(self, target):
        try:
            if "." in target:
                self.end_count = round(float(target), 5)
            else:
                self.end_count = int(target)

        except Exception:
            logger.warn(
                "Failed setting end count to {0}.  Make sure end_count is an int/float".format(
                    target
                )
            )
            logger.warn("Setting end_count to 0")
            self.end_count = 0.0

    def update_count_by(self, target):
        try:
            if "." in target:
                self.count_by = round(float(target), 5)
            else:
                self.count_by = int(target)
        except Exception:
            logger.warn(
                "Failed setting count_by to {0}.  Make sure count_by is an int/float".format(
                    target
                )
            )
            logger.warn("Setting count_by to 1")
            self.count_by = 1.0

    def update_count_template(self, target):
        self.count_template = str(target)

    def gen(self, count, earliest, latest, samplename=None):
        try:
            if hasattr(self._sample, "start_count"):
                self.update_start_count(self._sample.start_count)
            if hasattr(self._sample, "end_count"):
                self.update_end_count(self._sample.end_count)
            if hasattr(self._sample, "count_by"):
                self.update_count_by(self._sample.count_by)
            if hasattr(self._sample, "count_template"):
                self.update_count_template(self._sample.count_template)
            # count if not supplied is set to -1
            if count < 0:
                # if the user didn't supply end_count and they didn't supply a count, just take a guess they want the
                # default assuming that start_count is larger than the end_count (counting backwards)
                if not self.end_count and not self.start_count > self.end_count:
                    logger.warn(
                        "Sample size not found for count=-1 and generator=splitcounter, defaulting to count=60"
                    )
                    self.update_end_count(60)
                    count = 1
                else:
                    count = 1
            elif not self.end_count and count != 1:
                self.update_end_count(count)
                count = 1
            # if the end_count is lower than start_count, check if they want to count backwards.  Some people might not
            # want to do math, so if end_count is lower, but they want to count by a positive number, instead assume
            # they are trying to say "start at number x, count by y, and end after z cyles of y".
            if self.end_count < self.start_count:
                if self.count_by > 0:
                    logger.warn(
                        "end_count lower than start_count. Assuming you want start_count + end_count"
                    )
                    self.end_count = self.start_count + self.end_count
                elif self.count_by == 0:
                    logger.warn("Can't count by 0, assuming 1 instead.")
                    self.count_by = 1
            countdiff = abs(self.end_count - self.start_count)
            time_interval = timedelta.total_seconds((latest - earliest)) / countdiff
            for i in range(count):
                current_count = self.start_count
                while current_count != self.end_count:
                    current_time_object = earliest + datetime.timedelta(
                        0, time_interval * (current_count + 1)
                    )
                    msg = self.count_template.format(
                        samplename=samplename,
                        event_ts=current_time_object,
                        loop_count=i + 1,
                        max_loop=count,
                        start_count=self.start_count,
                        current_count=current_count,
                        end_count=self.end_count,
                        count_by=self.count_by,
                    )
                    self._out.send(msg)
                    if type(current_count) == float or type(self.count_by) == float:
                        current_count = round(current_count + self.count_by, 5)
                    else:
                        current_count = current_count + self.count_by
                # Since the while loop counts both directions, we end when they are equal
                # however we need to make sure we don't forget to run the last iteration
                else:
                    current_time_object = earliest + datetime.timedelta(
                        0, time_interval * (current_count + 1)
                    )
                    msg = self.count_template.format(
                        samplename=samplename,
                        event_ts=current_time_object,
                        loop_count=i + 1,
                        max_loop=count,
                        start_count=self.start_count,
                        current_count=current_count,
                        end_count=self.end_count,
                        count_by=self.count_by,
                    )
                    self._out.send(msg)
                    self._out.flush()
            return 0
        except Exception as e:
            raise e


def load():
    return CounterGenerator
