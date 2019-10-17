## The Configuration File ##

The primary source of configuration done in Eventgen is governed by the `eventgen.conf` file. 

* If deployed using containers, Eventgen will look for `eventgen.conf` in bundles under the `default` directory. For instance, if your bundle is named `datamix-app`, you should archive your `eventgen.conf` in `datamix-app/default/eventgen.conf`.
* If deployed as a Splunk App, Eventgen will look for `eventgen.conf` files for every app installed in Splunk, and will generate events for every `eventgen.conf` file it finds. This is convenient if you want to design event generation into a Technology Addon (TA) or other type of Splunk app. You can ship Eventgen configurations with your app and distribute the Eventgen app separately.

The INI format of `eventgen.conf` can have one or more stanzas. Each stanza name is a sample file it will be reading from. There a number of options available in each stanza. For instance, breaking down this tutorial file option-by-option, we can see how this file will be used to set up Eventgen:

### Simple Configuration
Sample conf from [sample bundle](https://github.com/splunk/eventgen/tree/develop/tests/sample_bundle.zip).
```
[film.json]
index = main
count = 1000
mode = sample
end = 1
autotimestamp = true
sourcetype = json
source = film.json

token.0.token = "FILM_ID":(\d+)
token.0.replacementType = integerid
token.0.replacement = 0

token.1.token = "REGION_ID":(\d+)
token.1.replacementType = seqfile
token.1.replacement = $SPLUNK_HOME/etc/apps/sample_conf/samples/count10.txt
```

```
[film.json]
```
This is the sample file name under `samples` folder.

```
index = main
```
Destination index of the generated data in Splunk.

```
count = 1000
```
Maximum number of events to generate per sample file.

```
mode = sample
```
In sample mode, eventgen will generate count (+/- rating) events every configured interval.

```
end = 1
```
After Eventgen started, it will only generate one time with 1000 events based on the configuration.
The value is `-1` by default and the data generation will not end.

```
autotimestamp = true
```
Eventgen will detect timestamp from sample if any.

```
sourcetype = json
source = film.json
```
Set the `sourcetype` and `source` in Splunk.

```
token.0.token = "FILM_ID":(\d+)
token.0.replacementType = integerid
token.0.replacement = 0
```
Eventgen will replace the matched token with an increasing integer id starting with 0. In this case it will generate 1000 events with `FILM_ID` with value from 0 to 999.

```
token.1.token = "REGION_ID":(\d+)
token.1.replacementType = seqfile
token.1.replacement = $SPLUNK_HOME/etc/apps/sample_conf/samples/count10.txt
```
Eventgen will replace the matched token with value from file `count10.txt` located in `samples` folder.

Extract and place the `sample_bundle` under `$SPLUNK_HOME/etc/apps` folder, enable `SA-Eventgen` modular input in Splunk.
Search with `index=main sourcetype=json source=film.json` and check the results. 

### More Complicated Configuration

```
[sample.tutorial0]
mode = replay
timeMultiple = 2

outputMode = httpevent
httpeventServers = {"servers": [{"protocol": "https", "port": "8088", "key": "00000000-0000-0000-0000-000000000000", "address": "localhost"}]}
end = 1
index = main
sourcetype = httpevent


token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}
token.0.replacementType = replaytimestamp
token.0.replacement = %Y-%m-%d %H:%M:%S

token.1.token = @@integer
token.1.replacementType = random
token.1.replacement = integer[0:10]
```

```
[sample.tutorial0]
```
This is the stanza name and the name of the sample file in Eventgen or your bundle that you want to read from. You can also specify a regex here to match multiple files of similar extensions/naming conventions.

```
mode = replay
```
Specify replay mode. This will leak out events at the same timing as they appear in the file (with intervals between events like they occurred in the source file). Default mode is `sample`, so this is required for replay mode.

```
timeMultiple = 2
```
This will slow down the replay by a factor of 2 by multiplying all time intervals between events by 2.
For example, let's assume that you have 3 events generated like below:

```
12:05:04 helloworld1
12:05:06 helloworld2
12:05:09 helloworld3
```

Applying `timeMultiple=2` would instead generate 3 events like below:
```
12:05:04 helloworld1
12:05:08 helloworld2
12:05:14 helloworld3
```

```
outputMode = httpevent
```
There are various `outputMode` available (see the [spec](REFERENCE.md#eventgenconfspec)). The `httpevent` mode will output via the Splunk [HEC](http://dev.splunk.com/view/event-collector/SP-CAAAE6M) endpoint straight into Splunk.
```
httpeventServers = {"servers": [{"protocol": "https", "port": "8088", "key": "00000000-0000-0000-0000-000000000000", "address": "localhost"}]}
```
This is the Splunk destination server to receive the generated events. Change the detail information in your environment. Please refer [HEC](http://dev.splunk.com/view/event-collector/SP-CAAAE6M) for more detail.

```
end = 1
```
Generate one time for the sample events.

```
index = main
sourcetype = httpevent
```
Events destination `index` and `sourcetype` in Splunk.

```
token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}
token.0.replacementType = replaytimestamp
token.0.replacement = %Y-%m-%d %H:%M:%S
```
This is a `replaytimestamp` replacement, which will find the timestamp specified by the regular expression and replace it with a current (or relative to the first event) time based on the stprtime format. Generally you'll define a regular expression and a strptime format to match.
For more information see [regular expressions](http://lmgtfy.com/?q=regex) and [striptime](http://lmgtfy.com/?q=strptime). You can also read more about the different replacement types on the [reference page](REFERENCE.md#eventgenconfspec).

```
token.1.token = @@integer
token.1.replacementType = random
token.1.replacement = integer[0:10]
```
This will replace token `@@integer` with a random integer between 0 and 10.

Go to $EVENTGEN_HOME and use the following command to generate data via Eventgen:
```
python -m splunk_eventgen generate splunk_eventgen/README/eventgen.conf.tutorial0
```

That's it, pretty simple! Check more example conf files under `splunk_eventgen/README` folder.

---

## The Sample File

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

## Use Jinja Templates with Eventgen

Traditionally, Eventgen sample files have been a collection of real logs that are used to replicate the data.
We added support for Jinja templates so that users can dynamically generate a sample file using a well-known and easy-to-learn Jinja module.
In addition to Jinja's ease of use, Jinja templates can include or inherit other templates so that users have freedom to stack different templates.

Simple conf file and Jinja template look like:

{% raw %}
```
# Conf File
[Test_Jinja]
end = 1
count = 1
generator = jinja
jinja_template_dir = templates
jinja_target_template = test_jinja.template
jinja_variables = {"large_number":50000}
earliest = -3s
latest = now
outputMode = stdout


# Jinja Template (file test_jinja.template)
{% for _ in range(0, large_number) %}
{%- time_now -%}
        {"_time":"{{ time_now_epoch }}", "_raw":"{{ time_now_formatted }}  I like little windbags
        Im at: {{ loop.index }} out of: {{ large_number }}
        I'm also hungry, can I have a pizza?"}
{% endfor %}
```
{% endraw %}

Running Eventgen with above conf file and template would result in below output.
```
2018-03-23T14:48:19  I like little windbags
        Im at: 0 out of: 50000
        I'm also hungry, can I have a pizza?
2018-03-23T14:48:19  I like little windbags
        Im at: 1 out of: 50000
        I'm also hungry, can I have a pizza?
2018-03-23T14:48:19  I like little windbags
        Im at: 2 out of: 50000
        I'm also hungry, can I have a pizza?
... and so on with the loop count
```
With above template, Eventgen iterates through a loop of 50000 and generate the data according to the template.
Note that the template is in a JSON format with a key "_raw" which is a raw string of data. It is necessary that you follow this pattern for Eventgen Jinja generator to work.

> If you are using `SA-Eventgen` app rather than PyPi module, put `eventgen.conf` and template files into a directory structure as outlined in the [configuration](CONFIGURE.md).
Default templates folder is `<bundle/samples/templates>`. You can also config absolute or relative path(relative to `eventgen.conf`) via `jinja_template_dir`.

Let's look at how to extend an existing template.

{% raw %}
```
{%- block head -%}
    {% include "another_jinja.template" %}
{%- endblock -%}
```
{% endraw %}

Adding above block imports the contents of another_jinja.template into your current template. You can include many templates.


{% raw %}
```
# extends block inherits a specified template
{% extends "super_jinja.template" %}
```
{% endraw %}

Adding above block makes your current template inherit the contents of super_jinja.template. You can only inherit from a single template.

Also, with Jinja templates, users can define mini functions (macro) inside of the template.

For example, using macro block allows you to define a function that is reusable in your template.

{% raw %}
```
{% macro input(name) -%}
    name = {{[0,1,2,3,4,5,6,7,8,9]|random}}
{%- endmacro -%}
```
{% endraw %}

Using macros will make your template reusable and easy to read.

These are a fraction of examples how flexible and dynamic Jinja module is. For more information about Jinja, see [Jinja2 Documentation](http://jinja.pocoo.org/docs/2.10/).

---

## Interact with RESTful Eventgen

Eventgen comes with server and controller architecture. This means easier scalability and control over multiple Eventgen instances.
For example, in the past, interacting with three Eventgen instances required a user to manually configure each instance and start.
Now, you only need to communicate with the controller to configure these Eventgen instances as long as they are all correctly connected to the messaging queue.
Please note Getting Started section for installation reference.

There is an [Eventgen API Reference](REFERENCE.html#rest-api-reference) that you can also reference.

---
