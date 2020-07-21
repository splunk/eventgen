# What is Eventgen?

Splunk Event Generator (Eventgen) is a utility that helps users easily build real-time event generators and eliminates the need for one-off, hard-coded event generators.

**Eventgen features:**
* Allows every type of events or transactions to be modeled
* Allows users to quickly build robust configuration-based event generators without having to write code
* Can be executed inside of Splunk (relying on a common event generation framework) as well as outside of Splunk
* Event output can easily be directed to a Splunk input (modular inputs, HEC, etc.), a text file, or any REST endpoint in an extensible way
* Easily configurable to make fake data look as real as possible, either by ordering events and token replacements by time of the day or by allowing generators to replay real data replacing current time by generating data exactly at the same time intervals as the original data
* For scenarios in which simple token replacements do not work, developers can quickly build sophisticated event generators by writing a generator plugin module while re-using the rest of the framework

## Table of Contents

* [Getting Started](SETUP.md)
    * [Install](SETUP.md#install)
    * [Configure](CONFIGURE.md)
    * [Upgrade](UPGRADE.md)
* [Tutorial](TUTORIAL.md)
* [Basics](BASICS.md)
* [Plugins](PLUGINS.md)
* [Architecture](ARCHITECTURE.md)
* [Contribute](CONTRIBUTE.md)
* [Performance](PERFORMANCE.md)
* [Reference](REFERENCE.md)
    * [eventgen.conf.spec](REFERENCE.md#eventgenconfspec)
    * [REST API Reference](REFERENCE.md#rest-api-reference)
* [Changelog](CHANGELOG.md)

