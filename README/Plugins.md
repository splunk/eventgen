# Plugin Architecture

As of version 3.0, the Eventgen now allows for plugins which extend our core functionality.  Plugins define a type which determines which methods we expect it to have.  The following types are available:

* Output
	* Output plugins take generated tuples of events and send them to a particular type of output
* Rating
	* Rating plugins determine how the count of events or specific randomly rated values should be rated

Planned future plugins:

* Generator
	* Handling of event generation should be pluggable


## Anatomy of a Plugin

### Configuration Validation
A plugin is a Python class which defines a certain set of understood methods and properties.  Firstly, config validation is a modular system in Eventgen, and plugins must be allowed to specify additional configuration parameters that the main Eventgen will consider valid and store.  *Note that eventgen.conf.spec generation is not yet automated, which means plugins must ship with the default distribution and eventgen.conf.spec must be maintained manually.*  Eventually spec file generation will be automated as well.

The main configuration of Eventgen validates itself by a list of configuration parameters assigned by type, and each of the configuration parameters is validated by that type.  The settings list is required:

* settings 				|   Defines the list of valid settings for this plugin

The following lists are optional and likely to be used by many plugins:

* outputModes			|   Valid output modes (outputMode = <outputMode>)
* splunkMethods			|   Valid splunkMethods for outputMode = splunkstream or stormstream (splunkMethod=<splunkMethod>)
* intSettings			|   Will validate the settings as integers
* floatSettings			|   Will validate the settings as floating point numbers
* boolSettings			|   Will validate the settings as booleans
* jsonSettings			|   Will validate the settings as a JSON string
* defaultableSettings	|   Settings which can be specified in the [global] stanza and will roll down to individual stanzas

The following lists are optional and supported but not likely to be relevant to a plugin:

* tokenTypes			|   Subsections of the token stanza (token.X.<tokenType>)
* hostTokens			|   Subsections of the host token stanza (hostToken.<tokenType)
* replacementTypes      |   Valid replacementTypes in the token stanza (token.X.replacementType = <replacementType>)
* sampleTypes			|   Valid sample types (sampleType = <sampleType>)
* mode 					|   Valid modes (mode = <mode>)

### Settings Variables
For each setting specified in the settings list, there must be a variable of the same name for the class.  The setup code will assign the values of those configurations to those variables which will be accessible by the plugin.

### Type
Secondly, a plugin must define a type.  Right now, we support outputing and rating plugins.  This is a statically defined field for the object

type = 'output' | 'rating'

### Methods
Depending on the type the plugin will define a certain set of methods which will be called to invoke the functionality of the plugin.

#### Output
Output plugins define three methods, refreshconfig, send and flush.  

* refreshconfig(sample)
	* This grabs new config from the passed sample to reconfigure the output.  The generator will call this when configuration information changes about the metadata associated with the output (index, host, source, sourcetype).
* send(msg)
	* Sends a message to the output.  The architecture assumes queueing and calls flush whenever metadata changes (see refreshconfig) but assumes the plugin will handle its own queueing and determine when best to flush the buffers.
* flush()
	* Flushes the output buffer for the plugin.


#### Rating