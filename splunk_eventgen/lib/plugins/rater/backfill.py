from config import ConfigRater
from timeparser import timeParserTimeMath


class BackfillRater(ConfigRater):
    name = 'BackfillRater'
    stopping = False

    def __init__(self, sample):
        super(BackfillRater, self).__init__(sample)
        self.logger.debug('Starting BackfillRater for %s' % sample.name if sample is not None else "None")
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
            backfillearliest = timeParserTimeMath(plusminus=mathsymbol, num=backfillnumber, unit=backfillletter,
                                                  ret=realtime)
            while backfillearliest < realtime:
                if self.executions == int(self.end):
                    self.logger.info("End executions %d reached, ending generation of sample '%s'" % (int(
                        self.end), self.sample.name))
                    break
                et = backfillearliest
                lt = timeParserTimeMath(plusminus="+", num=self.interval, unit="s", ret=et)
                genPlugin = self.generatorPlugin(sample=self.sample)
                # need to make sure we set the queue right if we're using multiprocessing or thread modes
                genPlugin.updateConfig(config=self.config, outqueue=self.outputQueue)
                genPlugin.updateCounts(count=count, start_time=et, end_time=lt)
                try:
                    self.generatorQueue.put(genPlugin)
                    self.executions += 1
                except Full:
                    self.logger.warning("Generator Queue Full. Skipping current generation.")
                backfillearliest = lt
            self.sample.backfilldone = True

        except Exception as e:
            self.logger.error("Failed queuing backfill, exception: {0}".format(e))

def load():
    return BackfillRater
