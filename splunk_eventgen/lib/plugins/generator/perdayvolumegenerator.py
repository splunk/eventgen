from __future__ import division

import datetime
import random
import time

from generatorplugin import GeneratorPlugin


class PerDayVolumeGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    #TODO: Make this work with replay mode.
    def gen(self, count, earliest, latest, samplename=None):
        # count in this plugin is a measurement of byteself._sample.
        size = count
        self.logger.debug("PerDayVolumeGenerator Called with a Size of: %s with Earliest: %s and Latest: %s" %
                          (size, earliest, latest))
        # very similar to the default generator.  only difference is we go by size instead of count.
        try:
            self._sample.loadSample()
            self.logger.debug("File sample loaded successfully.")
        except TypeError:
            self.logger.error("Error loading sample file for sample '%s'" % self._sample.name)
            return

        self.logger.debug("Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'" %
                          (self._sample.name, self._sample.app, size, earliest, latest))
        startTime = datetime.datetime.now()

        # Create a counter for the current byte size of the read in samples
        currentSize = 0
        # Replace event tokens before calculating the size of the event
        updated_sample_dict = GeneratorPlugin.replace_tokens(self, self._sample.sampleDict, earliest, latest)

        # If we're random, fill random events from sampleDict into eventsDict
        eventsDict = []
        if self._sample.randomizeEvents:
            sdlen = len(updated_sample_dict)
            self.logger.debugv("Random filling eventsDict for sample '%s' in app '%s' with %d bytes" %
                               (self._sample.name, self._sample.app, size))
            while currentSize < size:
                currentevent = updated_sample_dict[random.randint(0, sdlen - 1)]
                eventsDict.append(currentevent)
                currentSize += len(currentevent['_raw'])

        # If we're bundlelines, create count copies of the sampleDict
        elif self._sample.bundlelines:
            self.logger.debugv(
                "Bundlelines, filling eventsDict for sample '%s' in app '%s' with %d copies of sampleDict" %
                (self._sample.name, self._sample.app, size))
            while currentSize <= size:
                sizeofsample = sum(len(sample['_raw']) for sample in updated_sample_dict)
                eventsDict.extend(updated_sample_dict)
                currentSize += sizeofsample

        # Otherwise fill count events into eventsDict or keep making copies of events out of sampleDict until
        # eventsDict is as big as count
        else:
            self.logger.debug("Simple replay in order, processing")
            # I need to check the sample and load events in order until the size is smaller than read events from file
            # or i've read the entire file.
            linecount = 0
            currentreadsize = 0
            linesinfile = len(updated_sample_dict)
            self.logger.debugv("Lines in files: %s " % linesinfile)
            while currentreadsize <= size:
                targetline = linecount % linesinfile
                sizeremaining = size - currentreadsize
                targetlinesize = len(updated_sample_dict[targetline]['_raw'])
                if size < targetlinesize:
                    self.logger.error(
                        "Size is too small for sample {}. For this interval, we need {} bytes but size of one event is {} bytes."
                        .format(self._sample.name, size, targetlinesize))
                    break
                if targetlinesize <= sizeremaining or targetlinesize * .9 <= sizeremaining:
                    currentreadsize += targetlinesize
                    eventsDict.append(updated_sample_dict[targetline])
                else:
                    break
                linecount += 1
            self.logger.debugv("Events fill complete for sample '%s' in app '%s' length %d" %
                               (self._sample.name, self._sample.app, len(eventsDict)))

        # Ignore token replacement here because we completed it at the beginning of event generation
        GeneratorPlugin.build_events(self, eventsDict, startTime, earliest, latest, ignore_tokens=True)


def load():
    return PerDayVolumeGenerator
