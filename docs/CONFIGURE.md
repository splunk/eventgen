
## Configure ##

Now you probably wonder about how much data should Eventgen send? Or where should Eventgen send data to? Or how does Eventgen send data? Or what type of data do you want Eventgen to send?
After Eventgen is installed in any of the forms mentioned above, it is time to configure Eventgen.
There are two key concepts behind the configuration process of Eventgen:

* `eventgen.conf`: This is a ini-style configuration file that Eventgen parses to set global, default, and even sample-specific settings. These settings include which plugin to use, how much data to send, and where to send it to. For more information, see [this section](TUTORIAL.md#the-configuration-file).
* `sample files`: This is a collection of text files that Eventgen will read on initiation. Samples act as templates for the raw data that Eventgen pumps out. As such, these templates can include tokens or specific replacement strings that will get modified during processing-time (ex. timestamps updated in real-time). For more information, see [this section](TUTORIAL.md#the-sample-file).

In addition, common use cases work around bundling these relevant files.
Because Eventgen configs can be tightly coupled with custom sample files, they can be bundled up into a package itself, in the format:
```
bundle/
	default/
		eventgen.conf
	samples/
		users.sample
		hosts.sample
		firewall.logs
```
