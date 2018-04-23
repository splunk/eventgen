# Plugin Architecture

As of version 3.0, the Eventgen now allows for plugins which extend our core functionality.  There are three types of Plugins:

* Output
	* Output plugins take generated lists of events and send them to a particular type of output
* Rating
	* Rating plugins determine how the count of events or specific randomly rated values should be rated
* Generator
	* Generates lists of event dictionaries to be handled by output plugins


## Anatomy of a Plugin

Plugins inherit from a class per plugin type and are placed in their appropriate directory, either in the Eventgen app itself or inside another Splunk App's ``lib/plugins/<type>`` directory.  Lets take a look at the simplest plugin available to us, the Devnull output plugin:

```python
from __future__ import division
from outputplugin import OutputPlugin
import sys

class DevNullOutputPlugin(OutputPlugin):
    MAXQUEUELENGTH = 1000

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)
        self.firsttime = True

    def flush(self, q):
        if self.firsttime:
            self.f = open('/dev/null', 'w')
        buf = '\n'.join(x['_raw'].rstrip() for x in q)
        self.f.write(buf)

def load():
    """Returns an instance of the plugin"""
    return DevNullOutputPlugin
```

First, we import the OutputPlugin superclass.  For output plugins, they define a constant MAXQUEUELENGTH to determine the maximum amount of items in queue before forcing a queue flush.  

``__init__()`` is very simple.  It calls its superclass init and sets one variable, firsttime.  ``flush()`` is also very simple.  If its the first time, open the file /dev/null, otherwise, output the queue by writing it to the already open file.

Every Eventgen plugin defines a class and a ``load()`` method. The load() method is a universal function for determinig the class defined in the file.

Now, lets look at a slightly more complicated plugin, splunkstream.py in ``lib/plugins/output/splunkstream.py``.  We're going to look just at the top of the class as its being defined:

```python
class SplunkStreamOutputPlugin(OutputPlugin):
    MAXQUEUELENGTH = 100

    validSettings = [ 'splunkMethod', 'splunkUser', 'splunkPass', 'splunkHost', 'splunkPort' ]
    complexSettings = { 'splunkMethod': ['http', 'https'] }
    intSettings = [ 'splunkPort' ]
```

MAXQUEUELENGTH should look normal, but these other class variables bear a little explaination.

### Configuration Validation
Config validation is a modular system in Eventgen, and plugins must be allowed to specify additional configuration parameters that the main Eventgen will consider valid and store.  *Note that eventgen.conf.spec generation is not yet automated, which means plugins must ship with the default distribution and eventgen.conf.spec must be maintained manually.*  Eventually spec file generation will be automated as well.

The main configuration of Eventgen validates itself by a list of configuration parameters assigned by type, and each of the configuration parameters is validated by that type.  The settings list is required:

* validSettings 				|   Defines the list of valid settings for this plugin

The following lists are optional and likely to be used by many plugins:

* intSettings			|   Will validate the settings as integers
* floatSettings			|   Will validate the settings as floating point numbers
* boolSettings			|   Will validate the settings as booleans
* jsonSettings			|   Will validate the settings as a JSON string
* defaultableSettings	|   Settings which can be specified in the [global] stanza and will roll down to individual stanzas
* complexSettings       |   A dictionary of lists or function callbacks, containing a setting name with list of valid options or a callback function to validate the setting.

## Methods required per plugin type

Each plugin type will define a different method required.

**Plugin Type** | **Method** | **Returns** | **Notes**
--- | --- | --- | ---
Rater | ``rate()`` | Integer count of events to generate | n/a
Generator | ``gen(count, earliest, latest) `` | Success (0) | Events get put into an output queue by calling the Sample's ``send()`` or ``bulksend()`` methods in the output object.
Output | ``flush(q)`` | Success (0) | Gets a deque list q to operate upon and output as configured.

# Example Generator Plugin

We reviewed a simple Output Plugin earlier, lets look at a simple Generator Plugin:

```python
from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import itertools
from collections import deque

class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        globals()['logger'] = logger

        from eventgenconfig import Config
        globals()['c'] = Config()

    def gen(self, count, earliest, latest):
        l = [ {'_raw': '2014-01-05 23:07:08 WINDBAG Event 1 of 100000'} for i in xrange(count) ]

        self._out.bulksend(l)
        return 0

def load():
    return WindbagGenerator
```

For this generator plugin, notice we inherit from GeneratorPlugin instead of OutputPlugin.  This plugin is also quite simple.  In its ``__init__()`` method, it calls the superclass ``__init__()`` and it sets up two global variables, c, which holds the config (and is a Singleton pattern which can be instantiated many times) and a copy of the logger which we'll use for logging in most plugins.

Secondly, it defines a gen() method, which generates ``count`` events between ``earliest`` and ``latest`` time.  In this case, we ignore the timestamp and return just event text.  Then we call bulksend.  This plugin has several performance optimizations: using a list constructor instead of a loop and using bulksend instead of send.  Lets look how this could be implemented in a slightly less performant but easier to understand way:

```python
    def gen(self, count, earliest, latest):
        for x in xrange(count):
            self._sample.send({ '_raw': '2014-01-05 23:07:08 WINDBAG Event 1 of 100000' })

        return 0
```

Here, we use ``send()`` instead of ``bulksend()`` and a loop to make it easier to understand.

# Shipping a Plugin

When you've developed a plugin that you want to use in your app, shipping it with your app is easy.  Place any Eventgen plugin in your Splunk app's ``bin/`` directory and we'll search for and find any plugins referenced by a ``outputMode``, ``generator`` or ``rater`` config statement.