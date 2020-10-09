# Welcome

Welcome to the basics of Eventgen.
This should hopefully get you through setting up a working eventgen instance. For a complete reference of all available configuration options, please check out the [eventgen.conf.spec](REFERENCE.md#eventgenconfspec).  In the event you hit an issue, please post to the Issues page of the eventgen github repository (github.com/splunk/eventgen).

## Replay Example

Replay mode is likely to cover 90% of the use cases you can imagine.  Eventgen can take an export from another Splunk instance, or just a plain text file, and replay those events while replacing the time stamps. Eventgen will pause the amount of time between each event just like what happened in the original, so the events will appear to be coming out in real time.  When Eventgen reaches the end of the file, it can be configured to start over, stop or rest an interval and begin all over.  By default replay mode it will rest the default interval (60s) and then automatically start over from the beginning.

### Making a Splunk Export

To build a seed for your new Eventgen, start by taking an export from an existing Splunk instance.  Replay also can take a regular log file (in which case, you can omit sampletype=csv).  There are a few considerations.
* First, Eventgen assumes its sample files are in chronological order.
* Second, csv only uses `index`, `host`, `source`, `sourcetype` and `_raw` fields.  When using splunk search to build your replay, please append `| reverse | fields index, host, source, sourcetype, _raw` to your Splunk search and then doing an export to CSV format.
* Third, make sure you find all the different time formats inside the log file and set up tokens to replace for them, so limiting your initial search to a few sourcetypes is probably advisable.
* Forth, if not using a csv, token.0. should always be used to find and replace the replaytimestamp.  Eventgen needs to be told which field / regex to use for finding out the difference in time between events.

Please note, replaytimestamp means replace a replay with the time difference of the original event difference, where timestamp will always replace the time with "now".

### Running the example
You can easily run these examples by hand.  For testing purposes, change `outputMode = stdout` or `outputMode = modinput` to visually examine the data. Run the command below from directory `$EVENTGEN_HOME/splunk_eventgen`.

    python -m splunk_eventgen generate README/eventgen.conf.tutorial1

You should now see events showing up on your terminal window.  Eventgen will sleep between events as it sees gaps in the events in the source log.

### Wrapping up the first example
Find a real world example of what you want to generate events off, extract it from Splunk or a log file, and toss it into Eventgen.  Assuming that meets all your needs, you might want to skip to the [Deployment](#deployment) section.

## Basic Sample

Next, lets build a basic noise generator from a log file.  This will use sample mode, which take a file and either dump the entire file, or randomly select subset of that file every X seconds, defined by the count and interval.  It's important to remember, the default interval is set to 60s, even if you do not specify an interval, there will be one added to your stanza.  `Count` is used to specify how many events should leak out per `interval`.   Sample mode is the original way eventgen ran, and it's still very useful for generating random data where you want to engineer the data generated from the ground up. Run the command below from directory `$EVENTGEN_HOME/splunk_eventgen`:

    python -m splunk_eventgen generate README/eventgen.conf.tutorial2

### Grabbing and rating events

In the samples directory there is a file called `sample.tutorial2`.  It contains some random noise pulled from Router and Switch logs.  The sample will select 20 events from the file, every 15s and then allow that output to change slightly based on the time of day.

When defining a new config file, decide which defaults to override, and place them in your `eventgen.conf`.  In this example, the default time of day and day of week are varied.  There's a variety of defaults that can be overwritten.  See [eventgen.conf.spec](https://github.com/splunk/eventgen/blob/master/README/eventgen.conf.spec) in the README directory for reference.

Below is the contents of configuration directives used in `sample.tutorial2`:

```
[sample.tutorial2]
interval = 15
earliest = -15s
latest = now
count = 20
hourOfDayRate = { "0": 0.8, "1": 1.0, "2": 0.9, "3": 0.7, "4": 0.5, "5": 0.4, "6": 0.4, "7": 0.4, "8": 0.4, "9": 0.4, "10": 0.4, "11": 0.4, "12": 0.4, "13": 0.4, "14": 0.4, "15": 0.4, "16": 0.4, "17": 0.4, "18": 0.4, "19": 0.4, "20": 0.4, "21": 0.4, "22": 0.5, "23": 0.6 }
dayOfWeekRate = { "0": 0.7, "1": 0.7, "2": 0.7, "3": 0.5, "4": 0.5, "5": 1.0, "6": 1.0 }
randomizeCount = 0.2
randomizeEvents = true

outputMode = file
fileName = /tmp/ciscosample.log

## Replace timestamp Feb  4 07:52:53
token.0.token = \w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}
token.0.replacementType = timestamp
token.0.replacement = %b %d %H:%M:%S
```
Eventgen has 3 major sections, rating, generating, and outputing.  The first block located here lets the `generator` know how many events to create, and how:
First:
```
interval = 15
earliest = -15s
latest = now
```
In the first three lines, the generator will be told to run every 15s, and to make sure the earliest event is placed 15s into the past.  The last event will end exactly when the generator started (otherwise known as `now`), effectively creating a backfill for 15s.
```
count = 20
hourOfDayRate = { "0": 0.8, "1": 1.0, "2": 0.9, "3": 0.7, "4": 0.5, "5": 0.4, "6": 0.4, "7": 0.4, "8": 0.4, "9": 0.4, "10": 0.4, "11": 0.4, "12": 0.4, "13": 0.4, "14": 0.4, "15": 0.4, "16": 0.4, "17": 0.4, "18": 0.4, "19": 0.4, "20": 0.4, "21": 0.4, "22": 0.5, "23": 0.6 }
dayOfWeekRate = { "0": 0.7, "1": 0.7, "2": 0.7, "3": 0.5, "4": 0.5, "5": 1.0, "6": 1.0 }
randomizeCount = 0.2
randomizeEvents = true
```
The next 5 lines in the first section tell the generator how much data to generate.  In this case, a base count of 20, that then will be multiplied by the ratios for `hourOfDayRate`,`dayOfWeekRate`, and `randomizeCount`.  `hourOfDayRate` is a JSON formatted hash, with a string identifier for the current hour and a float representing the multiplier we want to use for that hour.  These ratios can be any valid floating point value.  `dayOfWeekRate` is similar, but the number is the day of the week, starting with Sunday.  `randomizeCount` says to introduce 20% randomness, which means plus or minus 10% of the rated total, to every rated count. `randomizeEvents` makes sure we don't grab the same lines from the file every time.

The next section configures the `output` plugin.
```
outputMode = file
fileName = /tmp/ciscosample.log
```
The output plugin is set to output to a file.  The file outputMode rotates based on size (by default 10 megabytes) and keeps the most recent 5 files around.

The last section deals with data manipulation.
```
## Replace timestamp Feb  4 07:52:53
token.0.token = \w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}
token.0.replacementType = timestamp
token.0.replacement = %b %d %H:%M:%S
```
This token substitution is for the timestamp.  Events will have their timestamp overridden based on earliest and latest configs above.
`token` is the configuration statement, `0` is the token number (use a different number for every token).  The third part of the token name defines the three subitems of token configuration.  The first, `token`, defines a regular expression used on the events to match a given field.  The second, `replacementType`, defines how to replace the matched field (for a list of different `replacementType`s please see [eventgen.conf.spec](https://github.com/splunk/eventgen/blob/master/README/eventgen.conf.spec)).  The third subitem, `replacement`, specifies the configuration for the `replacementType`.  In this case, defines a strptime format to use on output.  For a reference on how to configure strptime, please see python's documentation on strptime format strings.

## Second example, building events from scratch

Replaying random events from a file is an easy way to build an eventgen.  Sometimes, like in Eventgen we're building for VMware, the events you're modeling are so complicated it's simplest way to do it without investing a lot of time modeling all the tokens you want to subtitute etc.  Also, sometimes so many tokens need to move together, it's easiest just to replay the file with new timestamps.  However, if we're building a new demo from scratch, a lot of times we want to generate events from a basic template with values we're providing from files.  Let's look at an example:
```
# Note, these samples assume you're installed as an app or a symbolic link in
# $SPLUNK_HOME/etc/apps/eventgen.  If not, please change the paths below.

[sample.tutorial3]
interval = 1
earliest = -1s
latest = now
count = 10000
hourOfDayRate = { "0": 0.30, "1": 0.10, "2": 0.05, "3": 0.10, "4": 0.15, "5": 0.25, "6": 0.35, "7": 0.50, "8": 0.60, "9": 0.65, "10": 0.70, "11": 0.75, "12": 0.77, "13": 0.80, "14": 0.82, "15": 0.85, "16": 0.87, "17": 0.90, "18": 0.95, "19": 1.0, "20": 0.85, "21": 0.70, "22": 0.60, "23": 0.45 }
dayOfWeekRate = { "0": 0.55, "1": 0.97, "2": 0.95, "3": 0.90, "4": 0.97, "5": 1.0, "6": 0.99 }
randomizeCount = 0.2
outputMode = stdout

token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}
token.0.replacementType = timestamp
token.0.replacement = %Y-%m-%d %H:%M:%S

token.1.token = transType=(\w+)
token.1.replacementType = file
token.1.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/orderType.sample

token.2.token = transID=(\d+)
token.2.replacementType = integerid
token.2.replacement = 10000

token.3.token = transGUID=([0-9a-fA-F]+)
token.3.replacementType = random
token.3.replacement = guid

token.4.token = userName=(\w+)
token.4.replacementType = file
token.4.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/userName.sample

token.5.token = city="(\w+)"
token.5.replacementType = mvfile
token.5.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:2

token.6.token = state=(\w+)
token.6.replacementType = mvfile
token.6.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:3

token.7.token = zip=(\d+)
token.7.replacementType = mvfile
token.7.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:1

token.8.token = value=(\d+)
token.8.replacementType = random
token.8.replacement = float[0.000:10.000]
```

### Defining tokens

If you look at the `sample.tutorial3` file, you'll see that we took just one sample event and placed it in the file.  Eventgen will look at this one event, continue to replay it a number of times defined by our rating parameters, and then substitute in tokens we're going to define.  First, let's get the one token we understand out of the way, the timestamp:
```
token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}
token.0.replacementType = timestamp
token.0.replacement = %Y-%m-%d %H:%M:%S
```
Now, let's look at some new token substitutions we haven't seen:
```
token.2.token = transID=(\d+)
token.2.replacementType = integerid
token.2.replacement = 100000

token.3.token = transGUID=([0-9a-fA-F]+)
token.3.replacementType = random
token.3.replacement = hex(24)

token.4.token = userName=(\w+)
token.4.replacementType = file
token.4.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/userName.sample
```

There are three types of substitutions here. `integerid` is a constantly incrementing integer.  The replacement value is the seed to start with, and state will be saved between runs such that it will always increment.  Random supports integer, float, hex digits, ipv4, ipv6, mac, and string types.  These will just randomly generate digits.  In the case of integer, we also have a unix timestamp in this event we don't use, so we're telling it just to generate a random integer that looks like a timestamp.  For the two hex tokens, we're saying just generate some hex digits.  Note that where we have more complicated strings, we create a RegEx capture group with parenthesis to indicate the portion of the string we want Eventgen to replace.

Next, let's look at the file substitution:
```
token.1.token = transType=(\w+)
token.1.replacementType = file
token.1.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/orderType.sample
```
If you look in the sample file, you'll see various text values which are Order types for our application.  You'll also notice them repeated multiple times, which may seem strange.  The file based substitution will grab one line from a file, and then replace the RegEx capture group with the text it grabbed from the file.  This is very powerful, and we include many different types of common data with Eventgen, like internal and external IP addresses, usernames, etc, which may be useful for common applications.  Back to why in `orderType.sample` we see repeated values, because the selection is random, in this case we want the data to appear less than random.  We want a certain percentage of orders to be of type NewActivation, ChangeESN, etc, so we repeat the entries in the file multiple times to have some randomness, but according to the guidelines that a business would normally see!

We'll cover one more substitution type, mvfile:
```
token.5.token = city="(\w+)"
token.5.replacementType = mvfile
token.5.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:2

token.6.token = state=(\w+)
token.6.replacementType = mvfile
token.6.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:3

token.7.token = zip=(\d+)
token.7.replacementType = mvfile
token.7.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:1
```
`mvfile` is a multi-value file.  Because sometimes we need to replace more than one token based on the same random choice, we implemented the mvfile replacement type.  Mvfile will make a selection per event, and then re-use the same selection for all tokens in the event.  This allows us to replace City, State and Zip code together as you can see from the example above.  It can also be used to substitute the same choice into multiple tokens in the same event if that's required, as you can reuse the same file:column notation multiple times if you so choose.

Go take a look at the full file now.  You'll see we've built a model of 8 tokens we're replacing for every event.  We've modeled a set of business transactions without needing to write a single line of code.  Go ahead and run the tutorial and take a look at the output in Splunk (note to run this example, you'll need to set $SPLUNK_HOME and Eventgen app will need to be installed as SA-Eventgen)

## Third example, Sample Transaction Generation

The last example we'll run through is simpler, from a token perspective, but more complicated to model for a number of reasons.

### The first challenge and result: CSV input

The first challenge with modeling transactions is that they often contain multiple hosts, sources and sourcetypes.  In order to work around this, we implemented the sample type directive:

    [sample.mobilemusic.csv]
    sampletype = csv

If you look at sample.mobilemusic.csv, you'll see the CSV file has fields for index, host, source and sourcetype.  Just as we can specify those directives with `outputmode = splunkstream`, in `sampletype = csv` we'll pull those values directly from the file.  This allows us to model a transaction with different \_raw events with individual values per event for index, host, source and sourcetype, but define tokens which will work across them.

### The second challenge and result: bundlelines

The second challenge we encountered with transaction modeling was that we wanted to rate these transactions by hour of day and day of week like we do any other event type.  Without `sampletype = csv`, we'd create a multi-line event by changing breaker to be something like breaker = `[\r*\n\r*\n]` to say we only want to break the event when there's two newlines.  However, sampletype=csv prevents this because we have one entry per line in the CSV.  So we added a new directive called bundlelines.

    bundlelines = true

Bundlelines does exactly what we mentioned in the background by changing breaker for this group of events and creating a multiline event out of the CSV lines.  This allows us to rate by time of day and day of week properly with the whole CSV entry.

### The third challenge and result: replaytimestamp

Of course, when you think you've got the problem solved, you run up against your next challenge.  The data we were modeling contained different timestamp formats for each different sourcetype.  This is of course to be expected, and we were happy to have found it on our first transaction replay.

Because of what we went through earlier, inside Eventgen, this three line CSV file is now essentially inside Eventgen one three line event.  This means we can't really define different timestamp formats in different directives because we want the timestamps to look like they looked in the original transaction.  So we built replaytimestamp.  Replaytimestamp differs from timestamp in that its expecting there to be multiple timestamps in one event.  Replaytimestamp is also smart, in that it will read the timestamps in the event as its been generated and then introduce some randomness, but it will never exceed the length of the original transaction.  This means our generated transactions should look something like our original transactions.  However, we need to add some configuration language to support the multiple timestamp formats, so we end up with:

    token.0.token = ((\w+\s+\d+\s+\d{2}:\d{2}:\d{2}:\d{3})|(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}:\d{3}))
    token.0.replacementType = replaytimestamp
    token.0.replacement = ["%b %d %H:%M:%S:%f", "%Y-%m-%d %H:%M:%S:%f"]

The first line shows a really complicated RegEx.  This is essentially using RegEx to match both timestamp formats contained in the file.  If you look at the tutorial, you'll see both of these formats as they exist in other sample types, and in this case we bundled two capture groups together with a `|` to have our RegEx parser match both.

Secondly, in the replacement clause, we have a JSON formatted list.  This allows us to pass a user determined number of strptime formats.  Replaytimestamp will use these formats to parse the timestamps it finds with the RegEx.  It will then figure out differences between the events in the original event and introduce some randomness between them and then output them back in the strptime format it matched with.

<a id="deployment"></a>
# Deployment Options

## Command Line

This revision of Eventgen can be run by itself from a command line for testing.  This means you can simply run `splunk_eventgen generate eventgen.conf` and start seeing output, which is great for testing.  Command Line and Embedded Defaults are defined in the `splunk_eventgen/default/eventgen.conf` file in the [global] stanza.

## Splunk App

The original `SA-Eventgen` was written as a Splunk app, and this Eventgen release supports that deployment method as well.  In this deployment method, we will read configurations through Splunk's internal REST interface for grabbing config info, and Eventgen will look for configurations in every installed apps default and local directories in `eventgen.conf` file.  This is how ES is deployed, and it provides a very good example of this deployment method.  If you are writing a complicated Splunk application which will be deployed in multiple Applications, like ES, this is the recommended deployment method.

Install the latest SA-Eventgen App. There is no additional configuration required. SA-Eventgen app will automatically identify with any apps with `eventgen.conf`.

To start generating data, simply enable the SA-Eventgen modinput by going to Settings > Data Inputs > SA-Eventgen and by clicking "enable" on the default modular input stanza.

If you wish you add your bundle so that the modinput can detect your package:
Package your `eventgen.conf` and sample files into a directory structure as outlined in the [configuration](CONFIGURE.md). After that's done, copy/move the bundle into your `${SPLUNK_HOME}/etc/apps/` directory and restart Splunk. If you have specific samples enabled in your `eventgen.conf`, you should see data streaming into the specified Splunk index.

Make sure the bundle app permission is global. You can config this in two ways:
* Log in to Splunk Web and navigate to Apps > Manage Apps. Find the bundle app row and set the permission to 'Global' on the Sharing column.
* Create a folder `metadata` under the bundle with file `default.meta` and add the following content:
```
[]
export=system
```

## Backward Capability
If you are using Eventgen 5.x or even older versions, the `eventgen.conf` setting should be working in the latest Eventgen 6.x. If any thing broken, do not hesitate to open an issue on [GitHub](https://github.com/splunk/eventgen/issues/new/choose).

## Wrapping up

We hope the tutorial covers most use cases you would need.  If you have something you're struggling to model, please reach out to Tony Lee (tonyl@splunk.com).  We believe we can cover just about anything you'd want to model with this Eventgen, but if not, we're happy to add features to the software so that everyone can benefit!


