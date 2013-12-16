from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging

class DefaultGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, count, earliest, latest):
        try:
            partialInterval = self._sample.gen(count)
        # 11/24/13 CS Blanket catch for any errors
        # If we've gotten here, all error correction has failed and we
        # need to gracefully exit providing some error context like what sample
        # we came from
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            import traceback
            logger.error('Exception in sample: %s\n%s' % (self._sample.name, \
                    traceback.format_exc()))
            sys.stderr.write('Exception in sample: %s\n%s' % (self._sample.name, \
                    traceback.format_exc()))
            sys.exit(1)

        self.countdown = partialInterval

        ## Sleep for partial interval
        # If we're going to sleep for longer than the default check for kill interval
        # go ahead and flush output so we're not just waiting
        if partialInterval > self.time:
            logger.debugv("Flushing because we're sleeping longer than a polling interval")
            self._sample._out.flush()

            # Make sure that we're sleeping an accurate amount of time, including the
            # partial seconds.  After the first sleep, we'll sleep in increments of
            # self.time to make sure we're checking for kill signals.
            sleepTime = self.time + (partialInterval % self.time)
            self.countdown -= sleepTime
        else:
            sleepTime = partialInterval
            self.countdown = 0
          
        logger.debug("Generation of sample '%s' in app '%s' sleeping for %f seconds" \
                    % (self._sample.name, self._sample.app, partialInterval) ) 
        logger.debug("Queue depth for sample '%s' in app '%s': %d" % (self._sample.name, self._sample.app, c.outputQueue.qsize()))   
        if sleepTime > 0:
            self._sample.saveState()
            time.sleep(sleepTime)
        self._sample.gen(count)


def load():
    return DefaultGenerator