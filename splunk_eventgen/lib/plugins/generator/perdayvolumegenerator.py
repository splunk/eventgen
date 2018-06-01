from __future__ import division
from generatorplugin import GeneratorPlugin
import datetime, time
import random

class PerDayVolumeGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    #TODO: Make this work with replay mode.
    def gen(self, count, earliest, latest, samplename=None):
        # count in this plugin is a measurement of byteself._sample.
        size = count
        self.logger.debug("PerDayVolumeGenerator Called with a Size of: %s with Earliest: %s and Latest: %s" % (size, earliest, latest))
        # very similar to the default generator.  only difference is we go by size instead of count.
        try:
            self._sample.loadSample()
            self.logger.debug("File sample loaded successfully.")
        except TypeError:
            self.logger.error("Error loading sample file for sample '%s'" % self._sample.name)
            return

        self.logger.debug("Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'" % (self._sample.name, self._sample.app, size, earliest, latest))
        startTime = datetime.datetime.now()

        # Create a counter for the current byte size of the read in samples
        currentSize = 0
        # If we're random, fill random events from sampleDict into eventsDict
        eventsDict = [ ]
        if self._sample.randomizeEvents:
            sdlen = len(self._sample.sampleDict)
            self.logger.debugv("Random filling eventsDict for sample '%s' in app '%s' with %d bytes" % (self._sample.name, self._sample.app, size))
            while currentSize < size:
                currentevent = self._sample.sampleDict[random.randint(0, sdlen-1)]
                eventsDict.append(currentevent)
                currentSize += len(currentevent['_raw'])

        # If we're bundlelines, create count copies of the sampleDict
        elif self._sample.bundlelines:
            self.logger.debugv("Bundlelines, filling eventsDict for sample '%s' in app '%s' with %d copies of sampleDict" % (self._sample.name, self._sample.app, size))
            while currentSize <= size:
                sizeofsample = sum(len(sample['_raw']) for sample in self._sample.sampleDict)
                eventsDict.extend(self._sample.sampleDict)
                currentSize += sizeofsample

        # Otherwise fill count events into eventsDict or keep making copies of events out of sampleDict until
        # eventsDict is as big as count
        else:
            self.logger.debug("Simple replay in order, processing")
            # I need to check the sample and load events in order until the size is smaller than read events from file
            # or i've read the entire file.
            linecount = 0
            currentreadsize = 0
            linesinfile = len(self._sample.sampleDict)
            self.logger.debugv("Lines in files: %s " % linesinfile)
            while currentreadsize <= size:
                targetline = linecount % linesinfile
                sizeremaining = size - currentreadsize

                #targetlinesize = syself._sample.getsizeof(self._sample.sampleDict[targetline])
                self.logger.debugv("Printed Line: %s" % self._sample.sampleDict[targetline])
                targetlinesize =len(self._sample.sampleDict[targetline]['_raw'])

                self.logger.debugv("Target Line: %s, Target Size Remaining: %s, TargetLineSize: %s" % (targetline, sizeremaining, targetlinesize))
                if targetlinesize <= sizeremaining or targetlinesize*.9 <= sizeremaining:
                    currentreadsize += targetlinesize
                    eventsDict.append(self._sample.sampleDict[targetline])
                else:
                    break
                linecount += 1

            self.logger.debugv("Events fill complete for sample '%s' in app '%s' length %d" % (self._sample.name, self._sample.app, len(eventsDict)))


        for x in range(len(eventsDict)):
            event = eventsDict[x]['_raw']

            # Maintain state for every token in a given event
            # Hash contains keys for each file name which is assigned a list of values
            # picked from a random line in that file
            mvhash = { }

            ## Iterate tokens
            for token in self._sample.tokens:
                token.mvhash = mvhash
                # self.logger.debugv("Replacing token '%s' of type '%s' in event '%s'" % (token.token, token.replacementType, event))
                event = token.replace(event, et=earliest, lt=latest, s=self._sample)
                if token.replacementType == 'timestamp' and self._sample.timeField != '_raw':
                    self._sample.timestamp = None
                    token.replace(self._sample.sampleDict[x][self._sample.timeField], et=self._sample.earliestTime(), lt=self._sample.latestTime(), s=self._sample)
            if(self._sample.hostToken):
                # clear the host mvhash every time, because we need to re-randomize it
                self._sample.hostToken.mvhash = {}

            host = eventsDict[x]['host']
            if (self._sample.hostToken):
                host = self._sample.hostToken.replace(host, s=self._sample)

            if self._sample.timestamp == None:
                self._sample.timestamp = self._sample.now()
            l = [ { '_raw': event,
                    'index': eventsDict[x]['index'],
                    'host': host,
                    'hostRegex': self._sample.hostRegex,
                    'source': eventsDict[x]['source'],
                    'sourcetype': eventsDict[x]['sourcetype'],
                    '_time': time.mktime(self._sample.timestamp.timetuple()) } ]

            self._out.bulksend(l)
            self._sample.timestamp = None

        endTime = datetime.datetime.now()
        timeDiff = endTime - startTime
        timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
        self.logger.debugv("Interval complete, flushing feed")
        self._out.flush(endOfInterval=True)
        self.logger.info("Generation of sample '%s' in app '%s' completed in %s secondself._sample." % (self._sample.name, self._sample.app, timeDiffFrac) )

def load():
    return PerDayVolumeGenerator