# The Splunk Event Generator

The Splunk Event Generator is a utility which allows its user to easily build real-time event generators based on a robust configuration file definition.  The user can easily take a sample file and build anything from a replayed set of events, to a noise generator, to complicated transaction flows through configuration without having to write any code.

## License

The Splunk Event Generator is licensed under the Apache License 2.0. Details can be found in the LICENSE file.

## Support

This software is released as-is.  Splunk provides no warranty and no support on this software.  If you have any issues with the software, please feel free to post an [Issue](https://github.com/splunk/eventgen/Issues) on our Issues page.

## Contributing

We welcome contributions to our open source projects.  If you are interested in contributing, please follow the appropriate link:

* [Individual Contributor](http://dev.splunk.com/goto/individualcontributions)
* [Company Contributor](http://dev.splunk.com/view/companycontributions/SP-CAAAEDR)

# Intro

Welcome to Splunk's configurable Event Generator.  This project was originally started by David Hazekamp (dhazekamp@splunk.com) and then enhanced by Clint Sharp (clint@splunk.com).  The goals of this project are ambitious but simple:

* Eliminate the need for hand coded event generators in Splunk apps.
* Allow for portability of event generators between applications, and allow templates to be quickly adapted between use cases.
* Allow every type of event or transaction to be modeled inside the eventgen.

## Features

We've accomplished all those goals.  This version of the eventgen was derived from the original SA-Eventgen, is completely backwards compatible, but nearly completely rewritten. The original version contains most of the features you would need, including:

* A robust configuration language and specification to define how we should model events for replacement.
* Overridable defaults, which simplifies the setup of each individual sample.
* A flattening setup, where the eventgen.conf can be configured using regular expressions with lower entries inheriting from entries above.
* Support to be deployed as a Splunk app and gather samples and events from all apps installed in that deployment.  Splunk's Enterprise Security Suite uses this to great effect with its use of Technology Adapters which provide props and transforms for a variety of data types and also includes the event generators along with them to show sample data in the product.
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


# Tutorial

Please see our [Tutorial in the README directory](README/Tutorial.md).
