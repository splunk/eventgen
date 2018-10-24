# Welcome

Thanks for checking out the tutorial.
This should hopefully get you through setting up a working event generator.  It's only a tutorial though, so if you want a complete reference of all of the available configuration options, please check out the [eventgen.conf.spec](REFERENCE.md#eventgenconfspec) in the README directory.  With that, feel free to dig right in, and feel free to post to the Issues page if you have any questions.

## Replay Example

The first example we'll show you should likely cover 90% of the use cases you can imagine.  Eventgen can take an export from another Splunk instance, or just a plain text file, and replay those events while replacing the time stamps. Eventgen will pause the amount of time between each event just like it happened in the original, so the events will appear to be coming out in real time.  When Eventgen reaches the end of the file, it will automatically start over from the beginning.  Since this allows you to use real data as your eventgen, like we said earlier, it'll cover 9 out of 10 of most people's use cases.

### Making a Splunk export

To build a seed for your new Eventgen, I recommend taking an export from an existing Splunk instance.  You could also take a regular log file and use it for replay (in which case, you can omit sampletype=csv).  There are a few considerations.  First, Eventgen assumes its sample files are in chronological order.  Second, it only uses index, host, source, sourcetype and \_raw fields.  To accommodate that, whatever search you write, we recommend appending '| reverse | fields index, host, source, sourcetype, _raw' to your Splunk search and then doing an export to CSV format.  Third, make sure you find all the different time formats inside the log file and set up tokens to replace for them, so limiting your initial search to a few sourcetypes is probably advisable.

This example was pulled from a simple search of \_internal on my Splunk instance.

### Running the example
You can easily run these examples by hand.  In fact, for testing purposes, I almost always change outputMode = stdout to visually examine the data. Run the command below from the base directory of Eventgen.

    python -m splunk_eventgen generate splunk_eventgen/README/eventgen.conf.tutorial1

You should now see events showing up on your terminal window.  You can see Eventgen will sleep between events as it sees gaps in the events in the source log.

### Wrapping up the first example
This will cover most, if not all, of most people's use cases.  Find a real world example of what you want to generate events off, extract it from Splunk or a log file, and toss it into Eventgen.  Assuming that meets all your needs, you might want to skip to the [Deployment](#deployment) section.

## Basic Sample

Next, lets build a basic noise generator from a log file.  This will use sample mode, which take a file and replay all or a subset of that file every X seconds, defined by the interval.  Sample mode is the original way eventgen ran, and it's still very useful for generating random data where you want to engineer the data generated from the ground up. To run the example:

    python -m splunk_eventgen generate splunk_eventgen/README/eventgen.conf.tutorial2

### Grabbing and rating events

We have a file in the samples directory called sample.tutorial2 that we'll use as the seed for our event generator.  It contains some random noise pulled from Router and Switch logs.  It will provide a good basis of showing how we can very quickly take a customer's log file and randomly sample it and make it show up in real time.  We won't get too sophisticated with substitutions in this example, just a timestamp, and some more varied interfaces to make it look interesting.

When we're defining a new config file, we need to decide which defaults we're going to override.  By default for example, we'll rate events by time of day and day of week.  Do we want to override that?  There's a variety of defaults we should consider.  They're listed in the [eventgen.conf.spec](https://github.com/splunk/eventgen/blob/master/README/eventgen.conf.spec) in the README directory for reference.

Let's list out the file here and then break down the config directives we've not seen before:

    [cisco.sample]
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

First:

    interval = 15
    earliest = -15s
    latest = now
Let's us decide how often we want to generate events and how we want to generate time stamps for these events.  In this case, every 15 seconds should be sufficient, but depending on your use case you may want to generate only once an hour, once every minute, or every second. We'll generally want to set earliest to a value that's equal to a splunk relative time specifier opposite of interval.  So, if we set it to an hour, or 3600, we'll want earliest to be -3600s or -1h.  For this example, lets generate every 15 seconds.

    count = 20
    hourOfDayRate = { "0": 0.8, "1": 1.0, "2": 0.9, "3": 0.7, "4": 0.5, "5": 0.4, "6": 0.4, "7": 0.4, "8": 0.4, "9": 0.4, "10": 0.4, "11": 0.4, "12": 0.4, "13": 0.4, "14": 0.4, "15": 0.4, "16": 0.4, "17": 0.4, "18": 0.4, "19": 0.4, "20": 0.4, "21": 0.4, "22": 0.5, "23": 0.6 }
    dayOfWeekRate = { "0": 0.7, "1": 0.7, "2": 0.7, "3": 0.5, "4": 0.5, "5": 1.0, "6": 1.0 }
    randomizeCount = 0.2
    randomizeEvents = true
Eventgen by default will rate events by the time of day and the day of the week and introduce some randomness every interval.  Also by default, we'll only grab the first X events from the log file every time. For this example, we're looking at router and switch events, which actually is the opposite of the normal business flow.  We expect to see more events overnight for a few hours during maintenance windows and calm down during the day, so we'll need to override the default rating which looks like a standard business cycle.
    
hourOfDayRate is a JSON formatted hash, with a string identifier for the current hour and a float representing the multiplier we want to use for that hour.  In general, I've always configured the rate to be between 0 and 1, but nothing limits you from putting it at any valid floating point value.  dayOfWeekRate is similar, but the number is the day of the week, starting with Sunday.  In this example, Saturday and Sunday early mornings should have the greatest number of events, with fewer events evenly distributed during the week.  randomizeCount says to introduce 20% randomess, which means plus or minus 10% of the rated total, to every rated count just to make sure we don't have a flat rate of events.  randomizeEvents we discussed previously, it makes sure we don't grab the same lines from the file every time.

    outputMode = file
    fileName = /tmp/ciscosample.log
As you saw with the last example, we can output straight to Splunk, but in this case we're going to do a simple output to file.  The file outputMode rotates based on size (by default 10 megabytes) and keeps the most recent 5 files around.

    ## Replace timestamp Feb  4 07:52:53
    token.0.token = \w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}
    token.0.replacementType = timestamp
    token.0.replacement = %b %d %H:%M:%S
As we've seen before, here's a simple token substitution for the timestamp.  This will make the events appear to be coming in sometime during the last 15 seconds, based on earliest and latest configs above.

Let's look in detail at this configuration format.  token is the configuration statement, 0 is the token number (we'll want a different number for every token we define, although they can be non-contiguous).  The third part defines the three subitems of token configuration.  The first, token, defines a regular expression we're going to look for in the events as they stream through Eventgen.  The second, replacementType, defines what type of replacement we're going to need.  This is a timestamp, but we also offer a variety of other token replacement types such as random for randomly generated values, file for grabbing lines out of files, static for replacing with static strings, etc.  We'll cover those in detail later.  The third subitem, replacement, is specific for the replacementType, and in this case defines a strptime format we're going to use to output the time using strftime.  For a reference on how to configure strptime, check python's documentation on strptime format strings.

This should now replay random events from the file we have configured.  Go ahead and cd to $EVENTGEN\_HOME/bin and run python eventgen.py ../README/eventgen.conf.tutorial1.  In another shell, tail -f /tmp/ciscosample.log and you should see events replaying from the cisco.sample file!  You can reuse this same example to easily replay a customer log file, of course accounting for the different regular expressions and strptime formats you'll need for their timestamps.  Remember to customize interval, earliest, and count for the number of events you want the generator to build.

## Second example, building events from scratch

Replaying random events from a file is an easy way to build an eventgen.  Sometimes, like in Eventgen we're building for VMware, the events you're modeling are so complicated it's simplest way to do it without investing a lot of time modeling all the tokens you want to subtitute etc.  Also, sometimes so many tokens need to move together, it's easiest just to replay the file with new timestamps.  However, if we're building a new demo from scratch, a lot of times we want to generate events from a basic template with values we're providing from files.  Let's look at an example:

    [sample.tutorial3]
    interval = 3
    earliest = -3s
    latest = now
    count = 10
    hourOfDayRate = { "0": 0.30, "1": 0.10, "2": 0.05, "3": 0.10, "4": 0.15, "5": 0.25, "6": 0.35, "7": 0.50, "8": 0.60, "9": 0.65, "10": 0.70, "11": 0.75, "12": 0.77, "13": 0.80, "14": 0.82, "15": 0.85, "16": 0.87, "17": 0.90, "18": 0.95, "19": 1.0, "20": 0.85, "21": 0.70, "22": 0.60, "23": 0.45 }
    dayOfWeekRate = { "0": 0.55, "1": 0.97, "2": 0.95, "3": 0.90, "4": 0.97, "5": 1.0, "6": 0.99 }
    randomizeCount = 0.2
    backfill = -1h
    backfillSearch = sourcetype=be_log

    outputMode = splunkstream
    index=main
    host=host1.foobar.com
    source=/var/log/be/event.log
    sourcetype=be_log

    # Host/User/pass only necessary if running outside of splunk!
    splunkHost = localhost
    splunkUser = admin
    splunkPass = changeme

    token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}
    token.0.replacementType = timestamp
    token.0.replacement = %Y-%m-%d %H:%M:%S

    token.1.token = transType=(\w+)
    token.1.replacementType = file
    token.1.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/orderType.sample

    token.2.token = transID=(\d+)
    token.2.replacementType = integerid
    token.2.replacement = 100000

    token.3.token = transGUID=([0-9a-fA-F]+)
    token.3.replacementType = random
    token.3.replacement = hex(24)

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
    
### Output modes
    index=main
    host=host4.foobar.com
    source=eventgen
    sourcetype=business_event

Note here that we've specified index, host, source and sourceType.  In the past examples, this has been defined in the actual sample file on a per event basis by specifying sampletype = csv, but here we're reading from a plain text file so we need to specify this in the config file if we're setup as outputMode = splunkstream.

### Defining tokens

If you look at the sample.tutorial3 file, you'll see that we took just one sample event and placed it in the file.  Eventgen will look at this one event, continue to replay it a number of times defined by our rating parameters, and then substitute in tokens we're going to define.  First, let's get the one token we understand out of the way, the timestamp:

    token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}
    token.0.replacementType = timestamp
    token.0.replacement = %Y-%m-%d %H:%M:%S

Now, let's look at some new token substitutions we haven't seen:

    token.2.token = transID=(\d+)
    token.2.replacementType = integerid
    token.2.replacement = 100000

    token.3.token = transGUID=([0-9a-fA-F]+)
    token.3.replacementType = random
    token.3.replacement = hex(24)

    token.4.token = userName=(\w+)
    token.4.replacementType = file
    token.4.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/userName.sample

There are three types of substitutions here.  Integerid is a constantly incrementing integer.  The replacement value is the seed to start with, and state will be saved between runs such that it will always increment.  Random supports integer, float, hex digits, ipv4, ipv6, mac, and string types.  These will just randomly generate digits.  In the case of integer, we also have a unix timestamp in this event we don't use, so we're telling it just to generate a random integer that looks like a timestamp.  For the two hex tokens, we're saying just generate some hex digits.  Note that where we have more complicated strings, we create a RegEx capture group with parenthesis to indicate the portion of the string we want Eventgen to replace.

Next, let's look at the file substitution:

    token.1.token = transType=(\w+)
    token.1.replacementType = file
    token.1.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/orderType.sample

If you look in the sample file, you'll see various text values which are Order types for our application.  You'll also notice them repeated multiple times, which may seem strange.  The file based substitution will grab one line from a file, and then replace the RegEx capture group with the text it grabbed from the file.  This is very powerful, and we include many different types of common data with Eventgen, like internal and external IP addresses, usernames, etc, which may be useful for common applications.  Back to why in orderType.sample we see repeated values, because the selection is random, in this case we want the data to appear less than random.  We want a certain percentage of orders to be of type NewActivation, ChangeESN, etc, so we repeat the entries in the file multiple times to have some randomness, but according to the guidelines that a business would normally see!

We'll cover one more substitution type, mvfile:

    token.5.token = city="(\w+)"
    token.5.replacementType = mvfile
    token.5.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:2

    token.6.token = state=(\w+)
    token.6.replacementType = mvfile
    token.6.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:3

    token.7.token = zip=(\d+)
    token.7.replacementType = mvfile
    token.7.replacement = $SPLUNK_HOME/etc/apps/SA-Eventgen/samples/markets.sample:1
Mvfile is a multi-value file.  Because sometimes we need to replace more than one token based on the same random choice, we implemented the mvfile replacement type.  Mvfile will make a selection per event, and then re-use the same selection for all tokens in the event.  This allows us to replace City, State and Zip code together as you can see from the example above.  It can also be used to substitute the same choice into multiple tokens in the same event if that's required, as you can reuse the same file:column notation multiple times if you so choose.

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

This revision of Eventgen can be run by itself from a command line for testing.  This means you can simply run bin/eventgen.py and start seeing output, which is great for testing.  Please note to do this you'll want to set the $SPLUNK\_HOME environment variable properly so your configurations will work.  **Command Line and Embedded Defaults are defined in the lib/eventgen\_defaults file in the [global] stanza**.

## Splunk App

The original SA-Eventgen was written as a Splunk app, and this Eventgen release supports that deployment method as well.  In this deployment method, we will read configurations through Splunk's internal REST interface for grabbing config info, and Eventgen will look for configurations in every installed apps default and local directories in eventgen.conf file.  This is how ES is deployed, and it provides a very good example of this deployment method.  If you are writing a complicated Splunk application which will be deployed in multiple Applications, like ES, this is the recommended deployment method as it will simply your needs of building scripted inputs for each of those individual applications.  Installed a separate application, there is also a setup.xml provided which allows for easy disabling of the scripted input in Eventgen application.  **Defaults are defined in the default/eventgen.conf file in App mode**.

In your app's eventgen.conf file, sample files for file and mvfile substitution should be referenced using `$SPLUNK_HOME/etc/apps/<your_app>/samples/<file>`.

## Scripted Input

If you are writing an Eventgen for one application, like the Operational Intelligence demo, bundling two applications together is more complex than required and complicates distribution.  In this case, Eventgen supports being deployed as a scripted input inside your application.  **Note, you must set 'passAuth = splunk-system-user' in your inputs.conf for this to work**.  An example inputs.conf entry:

    [script://./bin/eventgen.py]
    disabled = false
    interval = 300
    passAuth = splunk-system-user
    sourcetype = eventgen
    index = _internal

Note, the interval can be set to anything.  Eventgen will stay running as soon as Splunk launches it.  To embed Eventgen into your application, you need to include everything in the bin and lib directories in your application.  In Scripted Input mode, we also read eventgen-standalone.conf in the default and local directories, and again **it will not flatten these configurations, so the local file will completely override the default**.  It is recommended that when deploying standalone, you only write one configuration file in the local directory.  Remember to copy any stock samples you are using into your apps samples directory as well.  **Defaults are defined in the lib/eventgen\_defaults file in the [global] stanza**.

In your app's eventgen.conf file, sample files for file and mvfile substitution should be referenced using `$SPLUNK_HOME/etc/apps/<your_app>/samples/<file>`.

## Wrapping up

We hope the tutorial covers most use cases you would need.  If you have something you're struggling to model, please reach out to Tony Lee (tonyl@splunk.com).  We believe we can cover just about anything you'd want to model with this Eventgen, but if not, we're happy to add features to the software so that everyone can benefit!