# Plugin Architecture

Eventgen allows for plugins which extend our core functionality. There are three types of Plugins:

* Output
	* Output plugins take generated lists of events and send the events to a specific target
* Rating
	* Rating plugins determine how the count of events or specific values should be rated
* Generator
	* Generates lists of event dictionaries to be handled by output plugins


## Anatomy of a Plugin

Plugins inherit from a base plugin class and are placed in their appropriate directory, either in Eventgen app itself or inside another Splunk App's ``lib/plugins/<type>`` directory.
Let's take a look at the simplest plugin available to us, the Devnull output plugin:

```python
from outputplugin import OutputPlugin
from logging_config import logger


class DevNullOutputPlugin(OutputPlugin):
    name = 'devnull'
    MAXQUEUELENGTH = 1000
    useOutputQueue = True

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)
        self.firsttime = True

    def flush(self, q):
        logger.info('flush data to devnull')
        if self.firsttime:
            self.f = open('/dev/null', 'w')
            self.firsttime = False
        buf = '\n'.join(x['_raw'].rstrip() for x in q)
        self.f.write(buf)


def load():
    """Returns an instance of the plugin"""
    return DevNullOutputPlugin

```

First, we import the OutputPlugin superclass. For output plugins, they define a constant `MAXQUEUELENGTH` to determine the maximum amount of items in queue before forcing a queue flush.

`useOutputQueue` is set to `True` here to use the output queue which functions as a reduce step when you need to maintain a single thread or a limited number of threads outputting data

``__init__()`` is very simple. It calls its superclass init and sets one variable, firsttime. ``flush()`` is also very simple.
If it's the first time, open the file /dev/null, otherwise, output the queue by writing it to the already open file.

Every Eventgen plugin defines a class and a ``load()`` method. The load() method is a universal function for determinig the class defined in the file.

Now, let's look at a slightly more complicated plugin, splunkstream.py in ``lib/plugins/output/splunkstream.py``. We're going to look just at the top of the class as its being defined:

```python
class SplunkStreamOutputPlugin(OutputPlugin):
    MAXQUEUELENGTH = 100

    validSettings = [ 'splunkMethod', 'splunkUser', 'splunkPass', 'splunkHost', 'splunkPort' ]
    complexSettings = { 'splunkMethod': ['http', 'https'] }
    intSettings = [ 'splunkPort' ]
```

`MAXQUEUELENGTH` should look normal, but these other class variables need a little explanation.

### Configuration Validation
Config validation is a modular system in Eventgen, and plugins must be allowed to specify additional configuration parameters that the main Eventgen will consider valid and store.
> Note that `eventgen.conf.spec` generation is not yet automated, which means plugins must ship with the default distribution and eventgen.conf.spec must be maintained manually.
Eventually spec file generation will be automated as well.

The main configuration of Eventgen validates itself by a list of configuration parameters assigned by type, and each of the configuration parameters is validated by that type.
The settings list is required:

* validSettings: Defines the list of valid settings for this plugin

The following lists are optional and likely to be used by many plugins:

* intSettings: Will validate the settings as integers
* floatSettings: Will validate the settings as floating point numbers
* boolSettings: Will validate the settings as booleans
* jsonSettings: Will validate the settings as a JSON string
* defaultableSettings: Settings which can be specified in the [global] stanza and will pass down to individual stanzas
* complexSettings: A dictionary of lists or function callbacks, containing a setting name with list of valid options or a callback function to validate the setting.

## Methods required per plugin type

Each plugin type will define a different method required.

**Plugin Type** | **Method** | **Returns** | **Notes**
--- | --- | --- | ---
Rater | ``rate()`` | Integer count of events to generate | N/A
Generator | ``gen(count, earliest, latest) `` | Success (0) | Events get put into an output queue by calling the Sample's ``send()`` or ``bulksend()`` methods in the output object.
Output | ``flush(q)`` | Success (0) | Gets a deque list q to operate upon and output as configured.

# Example Generator Plugin

We reviewed a simple Output Plugin earlier, let's look at a simple Generator Plugin:

```python
import datetime
from datetime import timedelta

from generatorplugin import GeneratorPlugin
from logging_config import logger


class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def gen(self, count, earliest, latest, samplename=None):
        if count < 0:
            logger.warning('Sample size not found for count=-1 and generator=windbag, defaulting to count=60')
            count = 60
        time_interval = timedelta.total_seconds((latest - earliest)) / count
        for i in xrange(count):
            current_time_object = earliest + datetime.timedelta(0, time_interval * (i + 1))
            msg = '{0} -0700 WINDBAG Event {1} of {2}'.format(current_time_object, (i + 1), count)
            self._out.send(msg)
        return 0


def load():
    return WindbagGenerator

```

For this generator plugin, notice we inherit from `GeneratorPlugin` instead of `OutputPlugin`. This plugin is also quite simple.

Secondly, it defines a `gen()` method, which generates ``count`` events between ``earliest`` and ``latest`` time. In this case, we ignore the timestamp and return just event text.
Then we call `bulksend`. This plugin has several performance optimizations: using a list constructor instead of a loop and using bulksend instead of send.
Let's see how this could be implemented in a slightly less performant but easier to understand way:

```python
    def gen(self, count, earliest, latest, samplename=None):
        for i in xrange(count):
            current_time_object = earliest + datetime.timedelta(0, time_interval * (i + 1))
            msg = '{0} -0700 WINDBAG Event {1} of {2}'.format(current_time_object, (i + 1), count)
            self._out.send(msg)
        return 0
```

Here, we use ``send()`` instead of ``bulksend()`` and a loop to make it easier to understand.

# Shipping a Plugin

When you've developed a plugin that you want to use in your app, shipping it with your app is easy.
Place any Eventgen plugin in your Splunk app's ``bin/`` directory and we'll search for and find any plugins referenced by a ``outputMode``, ``generator`` or ``rater`` config statement.
