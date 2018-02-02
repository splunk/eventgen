## The Configuration File ##

The primary source of configuration done in Eventgen is governed by the `eventgen.conf` file. 

* If deployed using containers, Eventgen will look for eventgen.conf in bundles under the `default` directory. For instance, if you bundle is named "datamix-app", you should archive your eventgen.conf in "datamix-app/default/eventgen.conf".
* If deployed as a Splunk App, Eventgen will look for eventgen.conf files for every app installed in Splunk, and will generate events for every eventgen.conf file it finds. This is convenient if you want to design event generation into a Technology Addon (TA) or other type of Splunk app. You can ship the eventgen configurations with you app and distribute the Eventgen app separately.

The INI format of eventgen.conf can have one or more stanzas, of which the stanza name is a sample file it will be reading from. There a number of options available in each stanza. For instance, breaking down this tutorial file option-by-option, we can see how this file will be used to setup Eventgen:

```
    [sample.tutorial1]
    mode = replay
    sampletype = csv
    timeMultiple = 2
    backfill = -15m
    backfillSearch = index=main sourcetype=splunkd

    outputMode = splunkstream
    splunkHost = localhost
    splunkUser = admin
    splunkPass = changeme

    token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}
    token.0.replacementType = timestamp
    token.0.replacement = %Y-%m-%d %H:%M:%S,%f
```

```
    [sample.tutorial1]
```
This is the stanza name and the name of the file in the samples/ directory of Eventgen or your bundle that you want to read from. You can also specify a regex here to match multiple files of similar extensions/naming conventions.

```
    mode = replay
```
Specify replay mode. This will leak out events at the same timing as they appear in the file (with gaps between events like they occurred in the source file). Default mode is sample, so this is required for replay mode.

```
    sampletype = csv
```
Specify that the input file is in CSV format, rather than a plain text file. With CSV input, we'll look for index, host, source, and sourcetype on a per event basis rather than setting them for the file as a whole.

```
    timeMultiple = 2
```
This will slow down the replay by a factor of 2 by multiplying all time between events by 2.

```
    backfill = -15m
```
Eventgen will startup and immediately fill in the last 15 minutes worth of events from this file. This is in Splunk relative time notation, and can be any valid relative time specifier (**NOTE:** the longer you make this, the longer it will take to get started).

```
    backfillSearch = index=main sourcetype=splunkd
```
A search to run to find the last events generated for this stanza. If this returns any results inside the backfill time window, eventgen will shorten the time window to start at the time of the last event it saw (**NOTE:** this only works with outputMode=splunkstream)

```
    outputMode = splunkstream
```
There are various outputModes available (see the [spec](REFERENCE.md#eventgenconfspec)). This will output via the Splunk [receivers/stream](http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTinput#receivers.2Fstream) endpoint straight into Splunk. This allows us to specify things like index, host, source and sourcetype to Splunk at index time. In this case, we're getting those values from sampletype = csv rather than specifying them here in the eventgen.conf for the sample.

```
    splunkHost = localhost
    splunkUser = admin
    splunkPass = changeme
```
Parameters for setting up outputMode = splunkstream. This is only required if we want to run Eventgen outside of Splunk. As a Splunk App and running as a scripted input, eventgen will gather this information from Splunk itself. Since we'll be running this from the command line for the tutorial, please customize your username and password in the tutorial.

```
    token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}
    token.0.replacementType = timestamp
    token.0.replacement = %Y-%m-%d %H:%M:%S,%f
```
The following 3 tokens are virtually the same, only with different regular expressions and strptime formats. This is a timestamp replacement, which will find the timestamp specified by the regular expression and replace it with a current (or relative to a backfill) time based on the stprtime format. Generally you'll define a regular expression and a strptime format to match. For more info on regular expressions and strptime, see [here](http://lmgtfy.com/?q=regex) and [here](http://lmgtfy.com/?q=strptime).

That's it, pretty simple!

---

## The Sample File ##

Sample files are seed files that Eventgen uses to send data. When a sample file matches the stanza in an eventgen.conf, it uses those configuration options to write data, using that sample file as a template. This flexible format lets you take real sample logs from anywhere and use it to replay/continuously feed data of the same variety. The use of tokens or regexes allow for dynamically-updated data, which is crucial for mimicking the latest timestamps or meeting specific cardinalities for fields.

When creating a bundle for Eventgen, you can have an unlimited number of sample files. Place all the sample files in `bundle/samples/` in order to get properly picked up by Eventgen during run-time.

Here are some examples of what sample files can look like:

```
# sample.tutorial1 -- CSV format
index,host,source,sourcetype,"_raw"
"main","csharp-mbp15.local","/Applications/splunk/var/log/splunk/metrics.log",splunkd,"09-15-2012 22:22:18.226 INFO  Metrics - group=mpool, max_used_interval=11259, max_used=95646, avg_rsv=251, capacity=268435456, used=0"
"main","csharp-mbp15.local","/Applications/splunk/var/log/splunk/metrics.log",splunkd,"09-15-2012 22:22:18.226 INFO  Metrics - group=pipeline, name=fschangemanager, processor=fschangemanager, cpu_seconds=0.000000, executes=1, cumulative_hits=506"
```

```
# sample.tutorial2
Mar  1 00:01:50.575: %SYS-5-CONFIG_I: Configured from console by console
Mar  1 00:01:51.047: %LINK-3-UPDOWN: Interface FastEthernet0/0, changed state to up
Mar  1 00:01:52.047: %LINEPROTO-5-UPDOWN: Line protocol on Interface FastEthernet0/0, changed state to up
Mar  1 00:02:25.499: %IP-4-DUPADDR: Duplicate address 192.168.1.1 on FastEthernet0/0, sourced by c201.168c.0000
Mar  1 00:04:37.815: OSPF: Rcv pkt from 192.168.1.2, FastEthernet0/0: Mismatch Authentication type. Input packet specified type 0, we use type 2
```

```
# sample.tutorial3
2012-09-14 16:30:20,072 transType=ReplaceMe transID=000000 transGUID=0A0B0C userName=bob city="City" state=State zip=00000 value=0
```

```
# sample.tutorial4 -- CSV format
index,host,source,sourcetype,_raw
main,proxy.splunk.com,/var/log/proxy.log,proxy,"Sep 14 17:28:11:000 Connection inbound from 5.5.5.5 to 10.2.1.35 on 10.12.0.20 open"
main,www.splunk.com,/var/log/httpd/access_log,access_custom,"2012-09-14 17:29:11:000 10.2.1.35 POST /playhistory/uploadhistory - 80 - 10.12.0.20 ""Mozilla/5.0 (Linux; U; Android 2.3.4; en-us; Sprint APX515CKT Build/GRJ22) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"" 200 0 0 468 1488"
main,proxy.splunk.com,/var/log/proxy.log,proxy,"Sep 14 17:30:11:000 Connection inbound from 5.5.5.5 to 10.2.1.35 on 10.12.0.20 closed"
```

---

## Interact with RESTful Eventgen

Eventgen comes with server and controller architecture. This means easier scalability and control over multiple Eventgen instances.
For example, in the past, interacting with three Eventgen instances required a user to manually configure each instance and start.
Now, you only need to communicate with the controller to configure these Eventgen instances as long as they are all correctly connected to the messaging queue.
Please note Getting Started section for installation reference.

There is an [Eventgen API Reference](REFERENCE.html#rest-api-reference) that you can also reference.

---

## For Orca Users: Running Eventgen with Orca ##

Orca 0.8.4 and above will natively support Eventgen 0.6.0 and above versions.

```
# Below command creates a specified number of eventgen instances as well as auto-configuring all servers and controllers.
orca create --egx <NUM>
```

In addition, you can configure a custom scenario for automatic bundle install.

```
# Paste this into your ~/.orca/orca.conf
# Below scenario will download an app from a specified path and start pumping out data
[egxtest]
indexers = 3
search_heads = 2
eventgenx_instances = 1
ansible_params = eventgen_app=https://repo.splunk.com/artifactory/Solutions/APP/ITSI_Performance_Testing/builds/develop/latest/ITSI_Performance_Testing-1.0.0-15.tgz,eventgen_volume=50,eventgen_start=now

# Simple run with this Orca command
orca create --sc egxtest
```


