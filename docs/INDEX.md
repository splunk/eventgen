#What is Eventgen?

**The Splunk Event Generator is a utility which allows its users to easily build real-time event generators.**

**Eventgen features:**
* Eliminate the need for one-off, hand-coded event generators
* Allow every type of event or transaction to be modeled
* Allow users to quickly build robust configuration-based event generators without having to write code
* Ability to be executed inside of Splunk (relying on a comment event generation framework) as well as outside of Splunk
* Event output can easily be directed to a Splunk input (modular inputs, HEC, etc.), a text file, or any REST endpoint in an easily extendible way
* Easily configurable to make fake data look as real as possible, either by rating events and token replacements by time of the day or by allowing generators to replay real data replacing current time by generating data exactly at the same time =intervals as the original data
* For scenarios that cannot be built using simple token replacements, allow developers to more quickly build sophisticated event generators by simply writing a generator plugin module but re-using the rest of the framework

* [Getting Started](SETUP.md)
    * [Install](SETUP.md#install)
    * [Configure](SETUP.md#configure)
* [Tutorial](TUTORIAL.md)
---
* [Basics](BASICS.md)
* [Plugins](PLUGINS.md)
* [Architecture](ARCHITECTURE.md)
* [Performance](PERFORMANCE.md)
---
* [Reference](REFERENCE.md)
    * [eventgen.conf.spec](REFERENCE.md#eventgenconfspec)
    * [REST API Reference](REFERENCE.md#rest-api-reference)
* [Changelog](CHANGELOG.md)

