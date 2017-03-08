# The Splunk Event Generator

The Splunk Event Generator is a utility which allows its user to easily build real-time event generators.  This project was originally started by David Hazekamp (dhazekamp@splunk.com) and then enhanced by Clint Sharp (clint@splunk.com).  There are three overarching goals for the project:

The goals of this project are ambitious but simple:

* Eliminate the need for hand coded event generators in Splunk apps.
* Allow for portability of event generators between applications, and allow templates to be quickly adapted between use cases.
* Allow every type of event or transaction to be modeled inside the eventgen.

Eventgen delivers on these, and to it we had several key design goals:

* Allow users to build configuration-based event generators, quickly and robustly without having to write code
* Eventgens should be packagable in Splunk apps so the App can ship with the configuration to build an eventgen and rely on a common event generation framework
* Eventgens should be easily runnable inside and outside of Splunk
* Eventgens output should be configurable allowing the same eventgen to output easily to a Splunk modular input, to a text file, or to a REST endpoint and all in an easily expandable way
* Eventgens should be easily configurable to make fake data look as real as possible, either by rating events and token replacements by time of the day or by allowing generators to replay real data substituting current time by generating at the exact same timing intervals as the original data
* For scenarios that can't be built using simple token replacements, allow developers to more quickly build sophisticated event generators by simply writing a generator module but re-using the rest of the framework
* Last but not least, generators should be able to scale up to consume 100% of even of the largest machine

The user can easily take a sample file and build anything from a replayed set of events, to a noise generator, to complicated transaction flows through configuration without having to write any code.  Developers who wish to utilize Eventgen's rich framework can also build their own generator plugins allowing them to model more complicated scenarios in code instead of simply configuration.

# Tutorial

Please see our [Tutorial in the README directory](README/Tutorial.md).

# Architecture

For an overview of the code and how Eventgen runs, please see our [Architecture guide in the README directory](README/Architecture.md).

# Plugins

For an overview of writing a plugin, please see our [Plugin documentation in the README directory](README/Plugins.md).

# Performance

Eventgen can scale to consume an entire machine easily with just a few configuration settings.  During testing, Eventgen on a 24 core machine can easily generate between 600-700k events per second of weblogs at 1.7 Gigabits/Sec (would require bonded Gigabit NICs to send out) generating nearly 20 Terabytes/Day of weblogs.  Detailed documentation on how to scale Eventgen is in our [Performance document in the README directory](README/Performance.md).

## License

The Splunk Event Generator is licensed under the Apache License 2.0. Details can be found in the LICENSE file.

## Support

This software is released as-is.  Splunk provides no warranty and no support on this software.  If you have any issues with the software, please feel free to post an [Issue](https://github.com/splunk/eventgen/Issues) on our Issues page.

## Contributing

We welcome contributions to our open source projects.  If you are interested in contributing, please follow the appropriate link:

* [Individual Contributor](http://dev.splunk.com/goto/individualcontributions)
* [Company Contributor](http://dev.splunk.com/view/companycontributions/SP-CAAAEDR)

# Changelog

Welcome to Splunk's configurable Event Generator.    

## Version 1.0 Features

* A robust configuration language and specification to define how we should model events for replacement.
* Overridable defaults, which simplifies the setup of each individual sample.
* A flattening setup, where the eventgen.conf can be configured using regular expressions with lower entries inheriting from entries above.
* Support to be deployed as a Splunk app and gather samples and events from all apps installed in that deployment.  Splunk's Enterprise Security Suite uses this to great effect with its use of Technology Add-Ons which provide props and transforms for a variety of data types and also includes the event generators along with them to show sample data in the product.
* A tokenized approach for modeling data, allowing replacements of timestamps, random data (mac address, ipv4, ipv6, integer, string data), static replacements, and random selections from a line in a file.
* Random timestamp distribution within a user specified range to allow randomness of events.
* Replay of a full file or a subset of the first X lines of the file.
* Generation of events based on a configurable interval.

On top of that, we've made very significant enhancements over that version:

* Added replay mode to allow us to replay a file from another Splunk instance to a new Splunk instance, leaking out events with proper time spaced between them to make it look like they are being generated in real time.
* Added backfill support to allow the event generator to start up and immediately generate a user configurable amount of time's worth of events in the past.  Also supports defining a search to only backfill where there is a gap.
* Added support to rate events and certain replacements by time of day and day of the week to model transaction flow inside a normal enterprise.
* Support to randomize the events coming from a sample file.  This allow us to feed a large sample of a few thousand lines and easily generate varied noise from that file.
* Added support to allow tokens to refer to the same CSV file, and pull multiple tokens from the same random selection.  This allows, for example, tokens to replace City, State and Zip from the same selection from a file.
* Added modular outputs to allow the Eventgen to output to a variety of different formats:
  1. Output to Splunk's receivers/stream REST endpoint.  This allows for us to configure index, host, source and sourcetype from within the Eventgen's config file!
  2. Legacy default of outputting to a spool file in $SPLUNK\_HOME/var/spool/splunk (or another directory configured for that particular sample).
  3. Output to a rotating Log file.  This was added so that the file can be read by a Splunk forwarder but also be read by competing products for our competitive lab.
  4. Output to Splunk Storm using Storm's REST input API.  Also allows host, source and sourcetype to specified in the config file.
* Added CSV sample inputs to allow overriding Index, Host, Source and Sourcetype on a per-event basis.  With this, we can model complicated sets of data, like VMWare's, or model transactions which may take place across a variety of sources and sourcetypes.
* Added float and hex random replacement types.
* Added rated random replacement types, which allow a random value to be generated and then rated by time of day or day of week.
* Allow the eventgen to be deployed as a Splunk app, as a scripted input inside another app, or run standalone from the command line (with caveats, see Deployment Options below).
* Wrote new threading code to ensure the Eventgen will stop properly when Splunk stops.
* Completely rewrote the configuration code to make it much simpler to enhance the eventgen when needed.

### Version 1.1 Changelog
* Added half a dozen performance enhancements to increase the performance of sample mode over 6x, and replay mode nearly 4x.  Can generate many thousands of events per second.
* Added support for using %s as a time format.  This will either read or generate a UNIX epoch timestamp in second since the epoch.
* Fixed bug not allowing mvfile substitutions on Windows.
* Added the ability to randomize hosts sent in the metadata to Splunk.using a random selection from a file.
* Simplified configuration by making file and mvfile the same thing configuration wise.  Using file with a semicolon and a column number will make it perform like mvfile now.  
* Fixed a bug causing backfill to generate about 20% more events than normal mode when using outputmode SplunkStream.
* Added support for timeMultiple which will slow down replay mode by <integer> factor, making a 10 minute sample of data play back in 20 minutes, or 60 minutes, etc, depending on the multiple.
* Allowed DEBUG logging to be turned on from the global config.
* Added integerid replacementType.  This will use a constantly incrementing ID as a replacement type.  Will update a state file whenever a sample sleeps or the program is shutting down.
* Removed need to have different defaults file and config file name if you're embedding into a Splunk App instead of shipping the eventgen as its own app.

## Version 2.0 Changelog
* Significant performance improvements
* New token replacements
* New rating to allow for outage-scenario type modeling

## Version 3.0 Changelog
For some reason that I can't remember, Version 3 became like the 13th floor on an American elevator.  We skipped it.

## Version 4.0 Changelog
This version is nearly 2 years in the making.  We have nearly completely refactored and rewritten huge sections of the codebase.

*Features:*
* New [plugin architecture](README/Plugins.md) to implement modular system
  * Generator Plugins allow for a use case where you want to write a few lines of python to model complicated simulations of transactions or other interactions that doing simple random replacements on a set of data would not allow you to do
  * Plugins can specify configuration variables required and provide validation rules & callbacks for validation
  * Plugins, written in python, will be available by simply dropping them in the bin directory of any Splunk App (or into the proper directory in Eventgen itself)
* [Massive scalability improvements](README/Performance.md): single instance can now spawn as many worker processes as required to generate Terabytes of data per day
* New UI for viewing performance, output of samples, and looking at Eventgen internal logs for troubleshooting
* New command line interface for testing and debugging
  * Simply point eventgen at your app directory `python eventgen.py <path/to/app>`
  * Test a single sample easily, overriding output to stdout for easy viewing
  * Turn up verbosity to investigate eventgen internals while testing
  * Scalability tuneables available in command line options for performance testing (Geneartors, Outputters, disabling output queue, etc)
* Specify time range to generate events for
  * Generate events for a fixed or relative time range
  * Easily generate a file, for example, for an entire month
* Autotimestamp feature to minimize configuration by auto-detecting an adding tokens for common timestamp formats
* Enhancements to Replay mode to detect and support reverse chronological samples and to fail more gracefully when timestamps are not found (only discard that event instead of fail the whole sample)
* Rewritten Tutorial documentation

*Internals:*
* Complete refactor of the codebase
  * Code now greatly more readable and understandable
  * Added [architecture documentation](README/Architecture.md) to help future developers
* Core code base now handles:
  * Configuration management
  * Concurrency, worker management and communication
* All other logic has been moved to a pluggable, modular system with plugins for
  * Rating event counts
  * Generating events
  * Outputting Events
* New Modular Input, S2S and HTTP Event Collector Output Plugins
* Added number of test scenarios and configs under the tests directory

