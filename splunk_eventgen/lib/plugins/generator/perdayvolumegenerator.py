import datetime
import random

from splunk_eventgen.lib.generatorplugin import GeneratorPlugin
from splunk_eventgen.lib.logging_config import logger


class PerDayVolumeGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    # TODO: Make this work with replay mode.
    def gen(self, count, earliest, latest, samplename=None):
        # count in this plugin is a measurement of byteself._sample.
        size = count
        logger.debug(
            "PerDayVolumeGenerator Called with a Size of: %s with Earliest: %s and Latest: %s"
            % (size, earliest, latest)
        )
        # very similar to the default generator.  only difference is we go by size instead of count.
        try:
            self._sample.loadSample()
            logger.debug("File sample loaded successfully.")
        except TypeError:
            logger.error(
                "Error loading sample file for sample '%s'" % self._sample.name
            )
            return

        logger.debug(
            "Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'"
            % (self._sample.name, self._sample.app, size, earliest, latest)
        )
        startTime = datetime.datetime.now()

        # Pre-generate each event in the sample once, so we can replace tokens and calculate any volume differences
        preReplacementSize = sum(
            [len(event["_raw"]) for event in self._sample.sampleDict]
        )
        allEvents = self.replace_tokens(self._sample.sampleDict, earliest, latest)
        postReplacementSize = sum([len(event["_raw"]) for event in allEvents])
        replacementVolumeRatio = preReplacementSize / postReplacementSize
        size = size * replacementVolumeRatio
        logger.debug(
            "Token replacement size factor: {}, new interval target size: {}".format(
                replacementVolumeRatio, size
            )
        )
        del allEvents

        # Create a counter for the current byte size of the read in samples
        currentSize = 0

        # If we're random, fill random events from sampleDict into eventsDict
        eventsDict = []
        if self._sample.randomizeEvents:
            sdlen = len(self._sample.sampleDict)
            logger.debug(
                "Random filling eventsDict for sample '%s' in app '%s' with %d bytes"
                % (self._sample.name, self._sample.app, size)
            )
            while currentSize < size:
                currentevent = self._sample.sampleDict[random.randint(0, sdlen - 1)]
                eventsDict.append(currentevent)
                currentSize += len(currentevent["_raw"])

        # If we're bundlelines, create count copies of the sampleDict
        elif self._sample.bundlelines:
            logger.debug(
                "Bundlelines, filling eventsDict for sample '%s' in app '%s' with %d copies of sampleDict"
                % (self._sample.name, self._sample.app, size)
            )
            while currentSize <= size:
                sizeofsample = sum(
                    len(sample["_raw"]) for sample in self._sample.sampleDict
                )
                eventsDict.extend(self._sample.sampleDict)
                currentSize += sizeofsample

        # Otherwise fill count events into eventsDict or keep making copies of events out of sampleDict until
        # eventsDict is as big as count
        else:
            logger.debug("Simple replay in order, processing")
            # I need to check the sample and load events in order until the size is smaller than read events from file
            # or i've read the entire file.
            linecount = 0
            currentreadsize = 0
            linesinfile = len(self._sample.sampleDict)
            logger.debug("Lines in files: %s " % linesinfile)
            while currentreadsize <= size:
                targetline = linecount % linesinfile
                sizeremaining = size - currentreadsize
                targetlinesize = len(self._sample.sampleDict[targetline]["_raw"])
                if size < targetlinesize:
                    logger.error(
                        "Size is too small for sample {}. We need {} bytes but size of one event is {} bytes.".format(
                            self._sample.name, size, targetlinesize
                        )
                    )
                    break
                if targetlinesize <= sizeremaining:
                    currentreadsize += targetlinesize
                    eventsDict.append(self._sample.sampleDict[targetline])
                else:
                    break
                linecount += 1
            logger.debug(
                "Events fill complete for sample '%s' in app '%s' length %d"
                % (self._sample.name, self._sample.app, len(eventsDict))
            )

        # replace tokens and send events
        send_objects = self.replace_tokens(eventsDict, earliest, latest)
        del eventsDict
        self.send_events(send_objects, startTime)


def load():
    return PerDayVolumeGenerator
