# TODO Sample object now incredibly overloaded and not threadsafe.  Need to make it threadsafe and make it simpler to get a
#       copy of whats needed without the whole object.

from __future__ import division
from generatorplugin import GeneratorPlugin
import logging
import datetime, time
import random
import sys

class PerDayVolumeGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'PerDayVolumeGenerator', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, size, earliest, latest, samplename=None):
        logger.debug("PerDayVolumeGenerator Called with a Size of: %s with Earliest: %s and Latest: %s" % (size, earliest, latest))
        # very similar to the default generator.  only difference is we go by size instead of count.
        s = self._samples[samplename]
        self._sample = s
        try:
            s.loadSample()
            logger.debug("File sample loaded successfully.")
        except TypeError:
            logger.error("Error loading sample file for sample '%s'" % self._sample.name)
            return

        logger.debug("Generating sample '%s' in app '%s' with count %d, et: '%s', lt '%s'" % (s.name, s.app, size, earliest, latest))
        startTime = datetime.datetime.now()

        # Create a counter for the current byte size of the read in samples
        currentSize = 0
        # If we're random, fill random events from sampleDict into eventsDict
        eventsDict = [ ]
        if s.randomizeEvents:
            sdlen = len(s.sampleDict)
            logger.debugv("Random filling eventsDict for sample '%s' in app '%s' with %d bytes" % (s.name, s.app, size))
            while currentSize < size:
                currentevent = s.sampleDict[random.randint(0, sdlen-1)]
                eventsDict.append(currentevent)
                currentSize += len(currentevent['_raw'])

        # If we're bundlelines, create count copies of the sampleDict
        elif s.bundlelines:
            logger.debugv("Bundlelines, filling eventsDict for sample '%s' in app '%s' with %d copies of sampleDict" % (s.name, s.app, size))
            while currentSize <= size:
                sizeofsample = sum(len(sample['_raw']) for sample in s.sampleDict)
                eventsDict.extend(s.sampleDict)
                currentSize += sizeofsample

        # Otherwise fill count events into eventsDict or keep making copies of events out of sampleDict until
        # eventsDict is as big as count
        else:
            logger.debug("Simple replay in order, processing")
            # I need to check the sample and load events in order until the size is smaller than read events from file
            # or i've read the entire file.
            linecount = 0
            currentreadsize = 0
            linesinfile = len(s.sampleDict)
            logger.debugv("Lines in files: %s " % linesinfile)
            while currentreadsize <= size:
                targetline = linecount % linesinfile
                sizeremaining = size - currentreadsize

                #targetlinesize = sys.getsizeof(s.sampleDict[targetline])
                logger.debugv("Printed Line: %s" % s.sampleDict[targetline])
                targetlinesize =len(s.sampleDict[targetline]['_raw'])

                logger.debugv("Target Line: %s, Target Size Remaining: %s, TargetLineSize: %s" % (targetline, sizeremaining, targetlinesize))
                if targetlinesize <= sizeremaining or targetlinesize*.9 <= sizeremaining:
                    currentreadsize += targetlinesize
                    eventsDict.append(s.sampleDict[targetline])
                else:
                    break
                linecount += 1

            logger.debugv("Events fill complete for sample '%s' in app '%s' length %d" % (s.name, s.app, len(eventsDict)))


        for x in range(len(eventsDict)):
            event = eventsDict[x]['_raw']

            # Maintain state for every token in a given event
            # Hash contains keys for each file name which is assigned a list of values
            # picked from a random line in that file
            mvhash = { }

            ## Iterate tokens
            for token in s.tokens:
                token.mvhash = mvhash
                # logger.debugv("Replacing token '%s' of type '%s' in event '%s'" % (token.token, token.replacementType, event))
                event = token.replace(event, et=earliest, lt=latest, s=s)
                if token.replacementType == 'timestamp' and s.timeField != '_raw':
                    s.timestamp = None
                    token.replace(s.sampleDict[x][s.timeField], et=s.earliestTime(), lt=s.latestTime(), s=s)
            if(s.hostToken):
                # clear the host mvhash every time, because we need to re-randomize it
                s.hostToken.mvhash =  {}

            host = eventsDict[x]['host']
            if (s.hostToken):
                host = s.hostToken.replace(host, s=s)

            if s.timestamp == None:
                s.timestamp = s.now()
            l = [ { '_raw': event,
                    'index': eventsDict[x]['index'],
                    'host': host,
                    'hostRegex': s.hostRegex,
                    'source': eventsDict[x]['source'],
                    'sourcetype': eventsDict[x]['sourcetype'],
                    '_time': time.mktime(s.timestamp.timetuple()) } ]

            self._out.bulksend(l)
            s.timestamp = None

        endTime = datetime.datetime.now()
        timeDiff = endTime - startTime
        timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
        logger.debugv("Interval complete, flushing feed")
        self._out.flush(endOfInterval=True)
        logger.debug("Generation of sample '%s' in app '%s' completed in %s seconds." % (s.name, s.app, timeDiffFrac) )

def load():
    return PerDayVolumeGenerator