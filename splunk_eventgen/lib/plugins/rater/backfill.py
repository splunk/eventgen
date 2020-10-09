from queue import Full

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.plugins.rater.config import ConfigRater
from splunk_eventgen.lib.timeparser import timeParserTimeMath


class BackfillRater(ConfigRater):
    name = "BackfillRater"
    stopping = False

    def __init__(self, sample):
        super(BackfillRater, self).__init__(sample)
        logger.debug(
            "Starting BackfillRater for %s" % sample.name
            if sample is not None
            else "None"
        )
        self.sample = sample
        self.samplerater = None

    def queue_it(self, count):
        try:
            realtime = self.sample.now(realnow=True)
            if "-" in self.sample.backfill[0]:
                mathsymbol = "-"
            else:
                mathsymbol = "+"
            backfillnumber = ""
            backfillletter = ""
            for char in self.sample.backfill:
                if char.isdigit():
                    backfillnumber += char
                elif char != "-":
                    backfillletter += char
            backfillearliest = timeParserTimeMath(
                plusminus=mathsymbol,
                num=backfillnumber,
                unit=backfillletter,
                ret=realtime,
            )
            while backfillearliest < realtime:
                et = backfillearliest
                lt = timeParserTimeMath(
                    plusminus="+", num=self.sample.interval, unit="s", ret=et
                )
                genPlugin = self.generatorPlugin(sample=self.sample)
                genPlugin.updateCounts(count=count, start_time=et, end_time=lt)
                genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
                try:
                    # Need to lock on replay mode since event duration is dynamic.  Interval starts counting
                    # after the replay has finished.
                    if self.sample.generator == "replay":
                        genPlugin.run()
                    else:
                        self.generatorQueue.put(genPlugin)
                except Full:
                    logger.warning("Generator Queue Full. Skipping current generation.")
                # due to replays needing to iterate in reverse, it's more efficent to process backfill
                # after the file has been parsed.  This section is to allow replay mode to take
                # care of all replays on it's first run. and sets backfilldone
                if self.sample.generator == "replay":
                    backfillearliest = realtime
                else:
                    backfillearliest = lt
            if self.sample.generator != "replay":
                self.sample.backfilldone = True

        except Exception as e:
            logger.error("Failed queuing backfill, exception: {0}".format(e))


def load():
    return BackfillRater
