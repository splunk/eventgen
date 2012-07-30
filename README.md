# Intro

Welcome to Splunk's configurable Event Generator.  This project was originally started by David Hazekamp (dhazekamp@splunk.com) and then enhanced by Clint Sharp (clint@splunk.com).  The goals of this project are ambitious but simple:

* Eliminate the need for hand coded event generators in Splunk apps.
* Allow for portability of event generators between applications, and allow templates to be quickly adapted between use cases.
* Allow every type of event or transaction to be modeled inside the eventgen.

## Features

I believe we've accomplished all those goals.  This version of the eventgen was derived from the original SA-Eventgen, is completely backwards compatible, but nearly completely rewritten. The original version contains most of the features you would need, including:

* A robust configuration language and specification to define how we should model events for replacement.
* Overridable defaults, which simplifies the setup of each individual sample.
* A flattening setup, where the eventgen.conf can be configured using regular expressions with lower entries inheriting from entries above.
* Support to be deployed as a Splunk app and gather samples and events from all apps installed in that deployment.  ES uses this to great effect with its use of Technology Adapters which provide props and transforms for a variety of data types and also includes the event generators along with them to show sample data in the product.
* A tokenized approach for modeling data, allowing replacements of timestamps, random data (mac address, ipv4, ipv6, integer, string data), static replacements, and random selections from a line in a file.
* Random timestamp distribution within a user specified range to allow randomness of events.
* Replay of a full file or a subset of the first X lines of the file.
* Generation of events based on a configurable interval.

On top of that, I've made very significant enhancements over that version:

* Added support to rate events and certain replacements by time of day and day of the week to model transaction flow inside a normal enterprise.
* Support to randomize the events coming from a sample file.  This allow us to feed a large sample of a few thousand lines and easily generate varied noise from that file.
* Added support to allow tokens to refer to the same CSV file, and pull multiple tokens from the same random selection.  This allows, for example, tokens to replace City, State and Zip from the same selection from a file.
* Added modular outputs to allow the Eventgen to output to a variety of different formats:
  1. Output to Splunk's receivers/stream REST endpoint.  This allows for us to configure index, host, source and sourcetype from within the Eventgen's config file!
  2. Legacy default of outputting to a spool file in $SPLUNK\_HOME/var/spool/splunk (or another directory configured for that particular sample).
  3. Output to a rotating Log file.  This was added so that the file can be read by a Splunk forwarder but also be read by competing products for our competitive lab.
  4. Output to Splunk Storm using Storm's REST input API.  Also allows host, source and sourcetype to specified in the config file.
* Added CSV sample inputs to allow overriding Index, Host, Source and Sourcetype on a per-event basis.  With this, we can model complicated sets of data, like VMWare's, or model transactions which may take place across a variety of sources and sourcetypes.
* Added replay timestamps which instead of randomly generating a timestamp for all timestamps found in a sample will randomly generate the first timestamp and then model the future timestamps based on the seperation between timestamps in the source sample file.  Includes support for specifying multiple output time formats and input formats (through regex).  This along with CSV sample input files, allows us to basically take an export from a Splunk instance and model it coming back into a new one with replaced timestamps and other tokens.
* Added float and hex random replacement types.
* Added rated random replacement types, which allow a random value to be generated and then rated by time of day or day of week.
* Allow the eventgen to be deployed as a Splunk app, as a scripted input inside another app, or run standalone from the command line (with caveats, see Deployment Options below).
* Wrote new threading code to ensure the Eventgen will stop properly when Splunk stops.
* Completely rewrote the configuration code to make it much simpler to enhance the eventgen when needed.

# Deployment Options

## Command Line

This revision of the Eventgen can be run by itself from a command line for testing.  This means you can simply run bin/eventgen.py and start seeing output, which is great for testing.  Please note to do this you'll want to set the SPLUNK\_HOME environment variable properly so your configurations will work.  The tutorials use relative paths to make it simpler, but production configurations should always reference from SPLUNK\_HOME.  **Command Line and Embedded Defaults are defined in the lib/eventgen\_defaults file in the [global] stanza**.

## Splunk App

The original SA-Eventgen was written as a Splunk app, and this supports that deployment method as well.  In this deployment method, we will read configurations through Splunk's internal REST interface for grabbing config info, and the Eventgen will look for configurations in every installed apps default and local directories in the eventgen.conf file.  This is how ES is deployed, and it provides a very good example of this deployment method.  If you are writing a complicated Splunk application which will be deployed in multiple Applications, like ES, this is the recommended deployment method as it will simply your needs of building scripted inputs for each of those individual applications.  Installed a separate application, there is also a setup.xml provided which allows for easy disabling of the scripted input in the Eventgen application.  **Defaults are defined in the default/eventgen.conf file in App mode**.

In your app's eventgen.conf file, sample files for file and mvfile substitution should be referenced using `$SPLUNK_HOME/etc/apps/<your_app>/samples/<file>`.

## Scripted Input

If you are writing an Eventgen for one application, like the Operational Intelligence demo, bundling two applications together is more complexity than required and complicates distribution.  In this case, the eventgen supports being deployed as a scripted input inside your application.  **Note, you must set 'passAuth = splunk-system-user' in your inputs.conf for this work**.  An example inputs.conf entry:

    [script://./bin/eventgen.py]
    disabled = false
    interval = 300
    passAuth = splunk-system-user
    sourcetype = eventgen
    index = _internal

Note, the interval can be set to anything.  Eventgen will stay running as soon as Splunk launches it.  To embed into your application, you need to include everything in the bin and lib directories in your application.  In Scripted Input mode, we also read eventgen-standalone.conf in the default and local directories, and again **it will not flatten these configurations, so the local file will completely override the default**.  It is recommended when deploying standalone, only write one configuration file in the local directory.  Remember to copy any stock samples you are using into your apps samples directory as well.  **Defaults are defined in the lib/eventgen\_defaults file in the [global] stanza**.

In your app's eventgen.conf file, sample files for file and mvfile substitution should be referenced using `$SPLUNK_HOME/etc/apps/<your_app>/samples/<file>`.

# Tutorial

Now that we've covered how you can run the Eventgen and the various caveats, lets go through some basic to advanced examples you can use to build upon for your own use cases.  All of these examples assume you are running standalone mode.

## Basic Example

First, lets build a basic noise generator from a log file.  The full file is located in README/eventgen-standalone.conf.tutorial1, which you can pass as the first parameter to eventgen.py to use if don't want to type all of this out of want to see the finalized product to follow along with.  An example from the root of the eventgen application:

    python bin/eventgen.py README/eventgen-standalone.conf.tutorial1

### Grabbing and rating events

We have a file in the samples directory called cisco.sample that we'll use as the seed for our event generator.  It contains some random noise pulled from Router and Switch logs.  It will provide a good basis of showing how we can very quickly take a customer's log file and replay it and make it show up in real time.  We won't get too sophisticated with substitutions in this example, just a timestamp, and some more varied interfaces to make it look interesting.

When we're defining a new config file, we need to decide which defaults we're going to override.  By default for example, we'll rate events by time of day and day of week.  Do we want to override that?  There's a variety of defaults we should consider.  They're listed in the spec file in the README directory for reference.

Let's start with the stanza name.  That's the name of the file we want to use as a seed.  In this case, as we said earlier it's cisco.sample:

    [cisco.sample]
    
Now, let's decide how often we want to generate events and how we want to generate time stamps for these events.  In this case, every 15 seconds should be sufficient, but depending on your use case you may want to generate only once an hour, once every minute, or every second.  Depends on the use case.  We'll generally want to set earliest to a value that's equal to a splunk relative time specifier opposite of interval.  So, if we set it to an hour, or 3600, we'll want earliest to be -3600s or -1h.  For this example, lets generate every 15 seconds.

    [cisco.sample]
    interval = 15
    earliest = -15s
    latest = now
    
We've decided to generate events every 15 seconds.  Let's talk about how the eventgen determines how many events to generate every 15 seconds.  The eventgen by default will rate events by the time of day and the day of the week and introduce some randomness every interval.  Also by default, we'll only grab the first X events from the log file every time, so in every sample that we want to generate that randomly chooses events we've got an option we'll need to set (in general we'll want to randomly grab events every time, but the original default was to read the first X lines, so in order to maintain backwards compatibility we've got to set this every time we want randomness).  For this example, we're looking at router and switch events, which actually is the opposite of the normal business flow.  We expect to see more events overnight for a few hours during maintenance windows and calm down during the day, so we'll need to override the default rating which looks like a standard business cycle.  Let's take a look at how that would look:

    count = 20
    hourOfDayRate = { "0": 0.8, "1": 1.0, "2": 0.9, "3": 0.7, "4": 0.5, "5": 0.4, "6": 0.4, "7": 0.4, "8": 0.4, "9": 0.4, "10": 0.4, "11": 0.4, "12": 0.4, "13": 0.4, "14": 0.4, "15": 0.4, "16": 0.4, "17": 0.4, "18": 0.4, "19": 0.4, "20": 0.4, "21": 0.4, "22": 0.5, "23": 0.6 }
    dayOfWeekRate = { "0": 1.0, "1": 0.7, "2": 0.5, "3": 0.5, "4": 0.5, "5": 0.5, "6": 1.0 }
    randomizeCount = 0.2
    randomizeEvents = true
    
hourOfDayRate is a JSON formatted hash, with a string identifier for the current hour and a float representing the multiplier we want to use for that hour.  In general, I've always configured the rate to be from 0 to 1, but nothing limits you from putting it at any valid floating point value.  dayOfWeekRate is similar, but the number is the day of the week, starting with Sunday.  In this example, Saturday and Sunday early mornings should have the greatest number of events, with the events evening out during the week.  randomizeCount says to introduce 20% randomess, which means plus or minus 10% of the rated total, to every rated count just to make sure we don't have a flat rate of events.  randomizeEvents we discussed previously, it makes sure we don't grab the same lines from the file every time.

### Outputting events

We're generating these events in memory, and the event generator needs to be configured to get them somewhere Splunk can read.  Because we've got a lot of different ways we might want to use this data, we've got a number of options we can configure for how to output the data.  The first we'll mention for legacy purposes, and it's the default, is outputMode = spool.  This will by default create a file and write it to $SPLUNK\_HOME/var/spool/splunk, which Splunk will eat and then delete.  This is great because it doesn't leave any artifacts behind you have to deal with, but it has the downside that you need to create props.conf and potentially transforms.conf entries to override index, host, source and sourcetype.  This is supported mainly for legacy purposes.  We also support outputting to a rotating log file, which rotates based on size (by default 10 megabytes) and keeps 5 old files around, or outputting via REST to Splunk or Splunk Storm which is the preferred method of output.  Because this is a simple example, we're going to show outputting to a log file and cover the REST outputs in the more complicated examples.  To output to a log we're going to add the following to the config:

    outputMode = file
    fileName = /tmp/ciscosample.log

### Making it look real, or defining tokens

We've now setup a file to randomly grab events every 15 seconds, rate them based on the time of the day with some randomness, and append them to a file.  By default, that'll replay the file exactly as it was.  However, we know that won't work for a variety of reasons.  First of all, you'll get the same events with the same timestamps every iteration.  At the very least, the event generator needs to substitute the timestamp with something that's close to right now, and most likely there's other things in the file we'd like to substitute.  The eventgen has a robust configuration format for this, allowing us to define tokens in form of a regular expression, and provide a variety of ways of replacing those values with some randomness.  For this example, lets keep it simple though and just replay the file with a new timestamp:

    ## Replace timestamp Feb  4 07:52:53
    token.0.token = \w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}
    token.0.replacementType = timestamp
    token.0.replacement = %b %d %H:%M:%S

Lets look in detail at this configuration format.  token is the configuration statement, 0 is the token number (we'll want a different number for every token we define, although they can be non-contiguous).  The third part defines the three subitems of token configuration.  The first, token, defines a regular expression we're going to look for in the events as they stream through the eventgen.  The second, replacementType, defines what type of replacement we're going to need.  This is a timestamp, but we also offer a variety of other token replacement types such as random for randomly generated values, file for grabbing lines out of files, static for replacing with static strings, etc.  We'll cover those in detail later.  The third subitem, replacement, is specific for the replacementType, and in this case defines a strptime format we're going to use to output the time using strftime.  For a reference on how to configure strptime, check python's documentation on strptime format strings.

This should now replay random events from the file we have configured.  The full file should look like:

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
    
Go ahead and cd to $EVENTGEN\_HOME/bin and run python eventgen.py ../README/eventgen-standalone.conf.tutorial1.  In another shell, tail -f /tmp/ciscosample.log and you should see events replaying from the cisco.sample file!  You can reuse this same example to easily replay a customer log file, of course accounting for the different regular expressions and strptime formats you'll need for their timestamps.  If you want a sine-wave like flow of events for the day, you can omit hourOfDayRate, dayOfWeekRate and randomizeCount and leave them at default.  Remember to customize interval, earliest and count for the number of events you want the generator to build as well.

## Second example, building events from scratch

Replaying random events from a file is an easy way to build an eventgen.  Sometimes, like in the eventgen we're building for VMWare, the events you're modeling are so complicated it's simplest way to do it without investing a lot of time modeling all the tokens you want to subtitute etc.  Also, sometimes so many tokens need to move together, it's easiest just to replay the file with new timestamps.  However, if we're building a new demo from scratch, a lot of times we're going to want to generate events from a basic template with values we're providing from files.  The Operational Intelligence demo uses this method to great success when looking at the business event data.  Let's look at how that was built.  First, let's look quickly at the stuff you already know about:

    ##### Sample Business Event ######
    [sample.businessevent]
    interval = 3
    earliest = -3s
    latest = now
    count = 10
    hourOfDayRate = { "0": 0.30, "1": 0.10, "2": 0.05, "3": 0.10, "4": 0.15, "5": 0.25, "6": 0.35, "7": 0.50, "8": 0.60, "9": 0.65, "10": 0.70, "11": 0.75, "12": 0.77, "13": 0.80, "14": 0.82, "15": 0.85, "16": 0.87, "17": 0.90, "18": 0.95, "19": 1.0, "20": 0.85, "21": 0.70, "22": 0.60, "23": 0.45 }
    dayOfWeekRate = { "0": 0.97, "1": 0.95, "2": 0.90, "3": 0.97, "4": 1.0, "5": 0.99, "6": 0.55 }
    randomizeCount = 0.2
    
### Output modes

All of the above example you should understand by now.  We said earlier we'd look at output modes in detail, which we'll look at in this example.  We include all of the possible output modes, commented out, allowing us to easily change how we're going to output the data.  While I'm testing, I'll generally output to a file, and then switch to splunkstream or stormstream later when I've got the data pretty much complete and ready to get into Splunk.  Let's look at the examples:

    # outputMode = spool
    # spoolDir = $SPLUNK_HOME/var/spool/splunk
    # spoolFile = <SAMPLE>

    # outputMode = file
    # fileName = /tmp/lotsofevents.log

    outputMode = splunkstream
    index=main
    host=splunktelbe-01.splunk.com
    source=eventgen
    sourcetype=business_event

    # Host/User/pass only necessary if running outside of splunk!
    splunkHost = localhost
    splunkUser = admin
    splunkPass = changeme

    # outputMode = stormstream
    # projectID = <projectid>
    # accessToken = <accesstoken>
    # host = localhost
    # source = eventgen
    # sourcetype = business_event
    
The first, spool, we've talked about earlier, and it will output a file into the spool directory on every interval for Splunk to eat in batch mode.  spoolFile = <SAMPLE> means we'll replace the filename with the name of the sample, so when you see the source in splunk it'll look like `$SPLUNK_HOME_/var/spool/Splunk/<samplefilename>`.  Again, this is provided primarily for legacy purposes to provide backwards compatibility with SA-Eventgen.

The next, file, you should already understand, but remember there's some other options defined in the spec file that can be set to override the defaults of a 10 megabyte file and 5 files kept as rollover backups.

Next, we have splunkstream.  This is what we were talking about earlier which allows you to output to Splunk through the receivers/stream REST endpoint.  This gives us a couple of advantages of allowing us to configure what index, host, source and sourcetype we're going to use as we're coming into Splunk.  This is great because it means we don't have to muck up our application configs with props.conf entries etc that we're using for the eventgen.  There are some caveats to how this works.  If we're running in standalone mode, like we're doing for the tutorial, we'll need to tell the eventgen how to get to Splunk by telling it what host it's running on and what username and password we're going to use to authenticate to the management interface.  If we're not running on the default management port of 8089, we'll need to override the default for that as well, and if we're using http instead of https on the management port, we'll need to override that default too.  None of this is necessary to be configured when we're running as a scripted input because we get Splunk auth information from Splunk and then we make REST calls to determine how to talk to Splunk.  __Note, if you're running as a scripted input, but Splunk is running on a different management port or running http instead of https, you'll need to set that up in the eventgen-standalone.conf__.

Finally, we have stormstream, which allows us to output to Storm.  This is obviously only useful in standalone mode, since we won't be running embedded in storm.  No need to define host or anything for storm as it's a publically known service with a known hostname, but you will need to define your project ID and access token that are retrieved from the API tab of Storm.

In this case, we've uncommented the splunkstream option, so make sure you open the tutorial2 file and customize it for your installation.

### Defining tokens

If you look at the sample.businessevent file, you'll see that we took just one sample event and placed it in the file.  The eventgen will look at this one event, continue to replay it a number of times defined by our rating parameters, and then substitute in tokens we're going to define.  First, lets get the one token we understand out of the way, the timestamp:

    token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}
    token.0.replacementType = timestamp
    token.0.replacement = %Y-%m-%d %H:%M:%S

Now, lets look at some new token substitutions we haven't seen:

    token.1.token = timestamp=(\d+)
    token.1.replacementType = random
    token.1.replacement = integer[1337000000:1339000000]

    token.2.token = JMSMessageID=ID:ESP-PD.([0-9A-F]{13}):
    token.2.replacementType = random
    token.2.replacement = hex(13)

    token.3.token = JMSMessageID=ID:ESP-PD.[0-9A-F]{13}:([0-9A-F]{8})
    token.3.replacementType = random
    token.3.replacement = hex(8)

There are two types of random substitutions here.  Random supports integer, float, hex digits, ipv4, ipv6, mac, and string types.  These will just randomly generate digits.  In the case of integer, we also have a unix timestamp in this event we don't use, so we're telling it just to generate a random integer that looks like a timestamp.  For the two hex tokens, we're saying just generate some hex digits.  Note that where we have more complicated strings, we create a RegEx capture group with parenthesis to indicate the portion of the string we want the eventgen to replace.

Next, lets look at the file substitution:

    token.4.token = orderType=(\w+)
    token.4.replacementType = file
    token.4.replacement = ../samples/orderType.sample

If you look in the sample file, you'll see various text values which are Order types for our application.  You'll also notice them repeated multiple times, which may seem curious.  The file based substitution will grab one line from a file, and then replace the RegEx capture group with the text it grabbed from the file.  This is very powerful, and we include many different types of common data with the eventgen, like internal and external IP addresses, usernames, etc, which may be useful for common applications.  Back to why in orderType.sample we see repeated values, because the selection is random, in this case we want the data to appear less than random.  We want a certain percentage of orders to be of type NewActivation, ChangeESN, etc, so we repeat the entries in the file multiple times to have some randomness, but according to the guidelines that a business would normally see!

We'll cover one more substitution type, mvfile:

    token.14.token = marketCity="(\w+)"
    token.14.replacementType = mvfile
    token.14.replacement = ../samples/markets.sample:2

    token.15.token = marketState=(\w+)
    token.15.replacementType = mvfile
    token.15.replacement = ../samples/markets.sample:3

    token.16.token = marketZip=(\d+)
    token.16.replacementType = mvfile
    token.16.replacement = ../samples/markets.sample:1
    
Mvfile is a multi-value file.  Because sometimes we need to substitute more than one token based on the same random choice, I implemented the mvfile replacement type.  Mvfile will make a selection per event, and then re-use the same selection for all tokens in the event.  This allows, in the above example as you can see, us to replace City, State and Zip code together.  It can also be used to substitute the same choice into multiple tokens in the same event if that's required, as you can reuse the same file:column notation multiple times if you so choose.

Go take a look at the full file now.  You'll see we've built a very complicated model of 30 tokens we're replacing for every event.  We've modeled a very complicated set of business transactions without needing to write a single line of code.  Go ahead and run the tutorial and take a look at the output in Splunk.

## Third example, Transaction Replay

The last example we'll run through is simpler, from a token perspective, but more complicated to model for a number of reasons.  When I originally shipped the Operational Intelligence demo, I had a second eventgen embedded that was coded by Patrick Ogdin (he built the first use case for the demo before I came onboard).  This eventgen generated the radius and access\_custom logs found in the mobile music portion of the demo.  The difficulty I had as soon as I went to put them into my eventgen was that they were an example of a typical transaction.  Multiple sources and sourcetypes with tokens that needed to match between them.  At the time with the current version of the eventgen, I didn't have time to build in the functionality needed, so I shipped the demo with the second eventgen, but later I added this functionality into the eventgen.

### The first challenge and result: CSV input

The first challenge with modeling transactions is that they often contain multiple hosts, sources and sourcetypes.  In order to work around this, I implemented the sample type directive:

    [sample.mobilemusic.csv]
    sampletype = csv
    
If you look at sample.mobilemusic.csv, you'll see the CSV file has fields for index, host, source and sourcetype.  Just as we can specify those directives with `outputmode = splunkstream`, in `sampletype = csv` we'll pull those values directly from the file.  This allows us to model a transaction with different \_raw events with individual values per event for index, host, source and sourcetype, but define tokens which will work across them.

### The second challenge and result: bundlelines

The second challenge I encountered was that we wanted to rate these transactions by hour of day and day of week like we do any other event type.  Without `sampletype = csv`, we'd create a multi-line event by changing breaker to be something like breaker = `[\r*\n\r*\n]` to say we only want to break the event when there's two newlines.  However, sampletype=csv prevents this because we have one entry per line in the CSV.  So I added a new directive called bundlelines.

    bundlelines = true
    
Bundlelines does exactly what we mentioned in the background by changing breaker for this group of events and creating a multiline event out of the CSV lines.  This allows us to rate by time of day and day of week properly with the whole CSV entry.

### The third challenge and result: replaytimestamp

Of course, when you think you've got the problem licked, and I did, but I ran up against my next challenge.  The data I was modeling contained different timestamp formats for each different sourcetype.  This is of course to be expected, and I'm happy I found it on my first transaction replay.

Because of what we went through earlier, inside the eventgen, this three line CSV file is now essentially inside the eventgen one three line event.  This means we can't really define different timestamp formats in different directives because we want the timestamps to look like they looked in the original transaction.  So I built replaytimestamp.  Replaytimestamp differs from timestamp in that its expecting there to be multiple timestamps in one event.  Replaytimestamp is also smart, in that it will read the timestamps in the event as its been generated and then introduce some randomness, but it will never exceed the length of the original transaction.  This means my generated transactions should look something like my original transactions.  However, I need to add some configuration language to support the multiple timestamp formats, so we end up with:

    token.0.token = ((\w+\s+\d+\s+\d{2}:\d{2}:\d{2}:\d{3})|(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}:\d{3}))
    token.0.replacementType = replaytimestamp
    token.0.replacement = ["%b %d %H:%M:%S:%f", "%Y-%m-%d %H:%M:%S:%f"]
    
The first line shows a really complicated RegEx.  This is essentially using RegEx to match both timestamp formats contained in the file.  If you look at the tutorial, you'll see both of these formats as they exist in other sample types, and in this case we bundled two capture groups together with a `|` to have our RegEx parser match both.

Secondly, in the replacement clause, we have a JSON formatted list.  This allows us to pass a user determined number of strptime formats.  Replaytimestamp will use these formats to parse the timestamps it finds with the RegEx.  It will then figure out differences between the events in the original event and introduce some randomness between them and then output them back in the strptime format it matched with.

### Failure Scenario

Lastly, in eventgen-standalone.conf.tutorial3 you'll notice that there are multiple samples referenced which are nearly identical.  This is to model the failure scenario embedded in the demo.  These contain roughly the same original transaction data along with some extra events we wanted to model, including the user searching for a couple of artists and failing.  It also replaces some original text like the HTTP status to indicate errors.  This is a technique you can use to easily re-use work and simulate a few bad transactions along with the good.

## Wrapping up

I hope the tutorial covers most use cases you would need.  If you have something you're struggling to model, please reach out to me.  I believe we can cover just about anything you'd want to model with this eventgen, but if not, I'm happy to add features to the software so that everyone can benefit!
