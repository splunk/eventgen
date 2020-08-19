
## Configure

After you have installed Eventgen by the method of your choosing, you may be asking some of the following questions:
* How much data should Eventgen send?
* Where should Eventgen send data?
* How does Eventgen send data?
* What type of data should Eventgen to send?
It's now time to configure Eventgen to your liking.
There are two key concepts behind the configuration process of Eventgen:

* `eventgen.conf`: This is a ini-style configuration file that Eventgen parses to set global, default, and even sample-specific settings.
  These settings include which plugin to use, how much data to send, and where to send it to. Due to the complexity of the configuration file,
  it's strongly recommended you follow the [tutorial sections](TUTORIAL.md).  Below you'll find every possible setting for configuration.
* `sample files`: This is a collection of text files that Eventgen will read on initiation. Samples act as templates for the raw data that Eventgen pumps out.
  As such, these templates can include tokens or specific replacement strings that will get modified during processing-time (ex. timestamps updated in real-time).
  For more information, see [this section](TUTORIAL.md#the-sample-file).

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


### Configuration File Settings
Configuration files are based on Splunk / Python configuration files. This style is made up from a simple configuration style, where a stanza defines a 
sample you wish to create, followed by key = value tuning options for that sample. 
```
[<sample file name>]
* This stanza defines a given sample file contained within the samples directory.
* This stanza can be specified as a PCRE.
<configuration key> = <configuration value>
    
[windbag]
count=100
```
Stanza names are one of the most important early configurations because they are used to find your sample file. Stanza names will perform a
search for the stanza name as a file, located in the current directory, the default samples directory, or a sample directory specified by the user. If no matching sample is found, Eventgen
finally searches for a generator plugin with the same name. Once a match is found, the stanza settings will be applied to all matched samples.
**Please note, "default" is a reserved name, and should not be used in any stanza title.** If you wish to apply a setting to all samples, please use the
stanza name "global".

#### Global Configuration Settings
There are some configuration settings that are meant to only be set on the global configuration. These settings will control and override settings that are core
eventgen settings. Below is a list of those options with their descriptions:

    threading = thread | process
    * Configurable threading model. Process uses multiprocessing.Process in Python to get around issues with the GIL.
    * Defaults to thread

    profiler = true | false
    * Run eventgen with python profiler on
    * Defaults to false

    useOutputQueue = true | false
    * Disable the use of the output Queue.
    * The output queue functions as a reduce step when you need to maintain a single thread or a limited number of threads outputting data, for instance if you're outputtingto a file or to stdout/modular input.
    * If you can multithread output, for example with splunkstream or s2s type outputs, setting this to false will give an order of magnitude or better performance improvement.
    * Defaults to true

    outputWorkers = <number of worker threads>
    * Deprecated. This will be removed in future releases.
    * Specifies how many threads or processes to stand up for handling output
    * Defaults to 1

    generatorWorkers = <number of generator threads>
    * Specifies how many threads/processes to use to generate events. Each stanza you have will occupy 1 thread / process as it processes.
      tuning this number will consume more CPU and can have negatvie effects if overallocated.
    * Defaults to 1

#### Stanza Configuration Settings
The following settings can be used on a per-stanza level. They allow each different generation sample to be massively changed and tuned.

##### Generic Settings        
Generic settings work on all stanzas and all stanza types.

    disabled = true | false
    * Like what it looks like. Will disable event generation for this sample.

    sampleDir = <dir>
    * Set a different directory to look for samples in

Eventgen is built of a simple connection of plugins. These plugins will control how fast events are generated, how they are generated, and where they are sent.
As sample is processed, Eventgen will look at those plugins in the following in order:

Timer > Rater > Generator > Outputer > Marker

Timer plugins are not configurable at this time, as most of the logic is pretty static for every followup plugin. They will run at a set frequency, and keep track of the time
between runs, as well as the amount of intervals that have been called. Every sample will create a timer, and those timers are placed in a timing queue. Right now there is a hardcoded limit
of 100 samples that are able to be processed at any given time. Adding more samples than this number, will cause previous samples to be pruned after a single
run. As each sample runs, it will then instantly call the rater to decide how many, if any, events should be created based on the specified configuration.
If there is supposed to be an event created, it will then create the generator, place it into the generator queue, and inform the generator how many events to create.
The generator will then run as fast as it can to finish generating ALL of those required events. As events are produced, they are placed in an output queue.
If the Eventgen is set to run in multiprocess mode, this outputqueue can be in 1 of two places. It will either be on the main eventgen process, or it'll be located
in the generator process. The generator will then check, "Can this outputter handle multi-thread?" If the answer is yes, the generator will place those events
on the generator output queue, if the answer is no, those events will be placed on the main Eventgen process' outputqueue. As soon as the maxout or max flush is hit for the outputter,
the generator will pause to send all of the currently queued events through the outputter. During the outputter process, if a marker plugin is specified, the marker
plugin will be called after processing the desired number of events. Once all of the required events have been generated, the timer will then check if the sample should be ran again,
if so, it places it at the end of the timing queue.

The remainder of this document will follow the above structure on tuning the respective items for each plugin type.

##### Timer Settings
Timer settings will influence how frequently a generator is added into the generator queue. These settings will directly control the amount
of time and the frequency between each sample run. Example, a sample that has an interval of 10, will be checked every 10s for the amount of events
to create, and processed. Replay mode however, will only run 1 time. If you wish to have replay run multiple times, use the "end" attribute.

    interval = <integer>
    * How often to generate sample (in seconds).
    * Defaults to 60.

    rater = default | <plugin>
    * Specifies which rater plugin to use. Default rater uses hourOfDayRate, etc, settings to specify
      how to affect the count of events being generated. Raters in 3.0 are now pluggable python modules.

    delay = <integer>
    * Specifies how long to wait until we begin generating events for this sample from startup.
    * Primarily this is used so we can stagger sets of samples which similar but slightly different data
    * Defaults to 0 which is disabled.

    end = <time-str> | <integer>
    * Will end execution on a specific time or a number of intervals
    * Can be used to execute only a specified number of intervals or with backfill to generate events over a specific time window.
    * Disabled by default
    
##### Rater Settings
Rater settings will control "how many events" are generated. These plugins have the ability to dynamically adjust the flow of events to
create complex eventgeneration schemes. Rater plugins can create "noise" or "rampup/rampdown" examples or control datavolume based on a desired
amount of volume perday. These plugins can be set either in the cwd, or in lib/plugins/rater.

    count = <integer>
    * Not valid with "replay" mode.
    * Maximum number of events to generate per sample file
    * -1 means replay the entire sample.
    * Defaults to -1.

    perDayVolume = <float>
    * This is used in place of count. The perDayVolume is a size supplied in GB per Day. This value will allow
    * eventgen to supply a target datavolume instead of a count for event generation.
    * Defaults to Null

    hourOfDayRate = <json>
    * Takes a JSON hash of 24 hours with float values to rate limit how many events we should see
      in a given hour.
    * Sample JSON:
      { "0": 0.05, "1": 0.05: "2": 0.07... }
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate, minuteOfHourRate, dayOfMonthRate, monthOfYearRate

    dayOfWeekRate = <json>
    * Takes a JSON hash of 7 days of the week in Splunk format (0 is Sunday)
    * Sample JSON:
      { "0": 0.55, "1": 0.97, "2": 0.95, "3": 0.90, "4": 0.97, "5": 1.0, "6": 0.99 }
    * If a match is not found, will default to count events
    * Also multiplied times hourOfDayRate, minuteOfHourRate, dayOfMonthRate, monthOfYearRate

    minuteOfHourRate = <json>
    * Takes a JSON hash of 60 minutes of an hour, starting with 0
    * Sample JSON:
      { "0": 1, "2": 1...}
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate, hourOfDateRate, dayOfMonthRate, monthOfYearRate

    dayOfMonthRate = <json>
    * Takes a JSON hash of 31 days of the month, starting with 1
    * Sample JSON:
      { "1": 1, "2": 1...}
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate, hourOfDateRate, minuteOfHourRate, monthOfYearRate

    monthOfYearRate = <json>
    * Takes a JSON hash of 60 minutes of an hour, starting with 0
    * Sample JSON:
      { "0": 1, "2": 1...}
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate, hourOfDateRate, minuteOfHourRate, dayOfMonthRate

    randomizeCount = <float>
    * Will randomize the number of events generated by percentage passed
    * Example values: 0.2, 0.5
    * Recommend passing 0.2 to give 20% randomization either way (plus or minus)
       
##### Generation Settings
All event generation in Eventgen is controlled by generator plugins. These plugins can either exist in the cwd, or in lib/plugins/generators.
By changing the generator plugin, you will effecitvely change what's required in the stanza to produce events, and how they are produced.
Eventgen ships with a few stock generators: cweblog, default, perdayvolumegenerator, replay, jinja and windbag. Perdayvolume / Replay / sample are automatically
configured based on the "mode" option of the default generator. Generators can also depend on the implementation of its corresponding "rater" plugin. Rater plugins are grouped
into this section, as eventgeneration would not be possible without determining the rate of that generation.

###### Generic Settings
Generic settings are valid for all generators.

    generator = default | <plugin>
    * Specifies the generator plugin to use.
    * The default generator exclusively uses settings in eventgen.conf to control behavior.
    * All other generators are pluggable python modules which can be custom code.

    mode = sample | replay
    * Default is sample, which will generate count (+/- rating) events every configured interval
    * Replay will instead read the file and leak out events, replacing timestamps, 
    * May not be supported by plugins otherthan "default"

    sampletype = raw | csv
    * Raw are raw events (default)
    * CSV are from an outputcsv or export from Splunk.
      CSV allows you to override output fields for the sample like host, index, source and sourcetype
      from the CSV file. Will read the raw events from a field called _raw. Assumes the CSV file has
      a header row which defines field names.

    timezone = local | <integer>
    * If set to 'local', will output local time, if set to '0000' will output UTC time
    * Otherwise it must be a timezone offset like +hhmm or -hhmm, for example:
      US Eastern Standard (EST) would be: timezone = -0500
      US Pacific Daylight (PDT) would be: timezone = -0700
      Indian Standard would be timezone = +0530
    * Valid range +2359 to -2359 (The last two digits are MINUTES, so they should be within 0-59)

    earliest = <time-str>
    * Specifies the earliest random time for generated events.
    * If this value is an absolute time, use the dispatch.time_format to format the value.
    * Defaults to now.

    latest = <time-str>
    * Specifies the latest random time for generated events.
    * If this value is an absolute time, use the dispatch.time_format to format the value.
    * Defaults to now.
    
###### Default Generator
The following options are only valid for the default Eventgen generator plugin.

    timeMultiple = <float>
    * Only valid in mode = replay
    * Will slow down the replay of events by <float> factor. This is achieved by calculating the interval between events and adjusting the interval by the timeMultiple factor. For example, allows a 10 minute sample to play out over 20 minutes with a timeMultiple of 2, or 60 minutes with a timeMultiple of 6. By the converse, make timeMultiple 0.5 will make the events run twice as fast. NOTE that the interval timeMultiple is adjusting is actual time interval between events in your sample file. "timeMultiple" option should not affect your "interval" option.

    timeField = <field name>
    * Only valid in mode = replay
    * Will select the field to find the timestamp in. In many cases, time will come from a different
      field in the CSV.

    backfill = <time-str>
    * Specified in Splunk's relative time language, used to set a time to backfill events

    backfillSearch = <splunk search>
    * If outputMode = splunkstream, this will run this search, appending '| head 1', and narrow the
      backfill range specified with backfill to when the search has last seen events.

    backfillSearchUrl = <url>
    * Defaults to splunkMethod://splunkHost:splunkPort/, can override in case you're running
      in a cluster.

    bundlelines = true | false
    * For outside use cases where you need to take all the lines in a sample file and pretend they are
      one event, but count = 0 will not work because you want to replay all the lines more than once.
      Also, please note you can also use breaker=\r*\n\r*\n to break the sample file into multi-line
      transactions that would work better than this as well. This is also useful where you want to bring
      in sampletype = csv and bundle that multiple times.
    * If bundlelines = true and the token replacementType is replaytimestamp, we will introduce some randomness
      into the times between items in the transaction in microseconds.
    * Will override any breaker setting.

    randomizeEvents = <boolean>
    * Will randomize the events found in the sample file before choosing the events.
    * NOT SUPPORTED WITH sampletype csv
    * NOT SUPPORTED WITH mode = replay OR custom generators like generator = replay

    breaker = <regular expression>
    * NOT to be confused w/ props.conf LINE_BREAKER.
    * PCRE used for flow control.
    * If count > 0; data will be generated until number of discovered breakers <= "count".
    * If breaker does not match in sample, one iteration of sample will be generated.
    * Defaults to [^\r\n\s]+
    
###### Token Settings
Tokens in the default generator can override the sample to allow dynamic content to be generated.

    token.<n>.token = <regular expression>
    * 'n' is a number starting at 0, and increasing by 1.
    * PCRE expression used to identify segment for replacement.
    * If one or more capture groups are present the replacement will be performed on group 1.
    * Defaults to None.

    token.<n>.replacementType = static | timestamp | replaytimestamp | random | rated | file | mvfile | seqfile | integerid
    * 'n' is a number starting at 0, and increasing by 1. Stop looking at the filter when 'n' breaks.
    * For static, the token will be replaced with the value specified in the replacement setting.
    * For timestamp, the token will be replaced with the strptime specified in the replacement setting
    * For replaytimestamp, the token will be replaced with the strptime specified in the replacement setting
      but the time will not be based on earliest and latest, but will instead be replaced by looking at the
      offset of the timestamp in the current event versus the first event, and then adding that time difference
      to the timestamp when we started processing the sample. This allows for replaying events with a
      new timestamp but to look much like the original transaction. Assumes replacement value is the same
      strptime format as the original token we're replacing, otherwise it will fail. First timestamp will
      be the value of earliest. NOT TO BE CONFUSED WITH REPLAY MODE. Replay mode replays a whole file
      with timing to look like the original file. This will allow a single transaction to be replayed with some randomness.
    * For random, the token will be replaced with a type aware value (i.e. valid IPv4 Address).
    * For rated, the token will be replaced with a subset of random types (float, integer), which are
      rated by hourOfDayRate and dayOfWeekRate.
    * For file, the token will be replaced with a random value retrieved from a file specified in the replacement setting.
    * For mvfile, the token will be replaced with a random value of a column retrieved from a file specified in the replacement setting.
      Multiple files can reference the same source file and receive different columns from the same random line.
    * For seqfile, the token will be replaced with a value that retrieved from (a column of) file sequentially.
    * For integerid, will use an incrementing integer as the replacement.
    * Defaults to None.

    token.<n>.replacement = <string> | <strptime> | ["list","of","strptime"] | guid | ipv4 | ipv6 | mac | integer[<start>:<end>] | float[<start>:<end>] | string(<i>) | hex(<i>) | list["list", "of", "values"] | <replacement file name> | <replacement file name>:<column number> | <integer>
    * 'n' is a number starting at 0, and increasing by 1. Stop looking at the filter when 'n' breaks.
    * For <string>, the token will be replaced with the value specified.
    * For <strptime>, a strptime formatted string to replace the timestamp with
    * For ["list","of","strptime"], only used with replaytimestamp, a JSON formatted list of strptime
      formats to try. Will find the replace with the same format which matches the replayed timestamp.
    * For guid, the token will be replaced with a random GUID value.
    * For ipv4, the token will be replaced with a random valid IPv4 Address (i.e. 10.10.200.1).
    * For ipv6, the token will be replaced with a random valid IPv6 Address (i.e. c436:4a57:5dea:1035:7194:eebb:a210:6361).
    * For mac, the token will be replaced with a random valid MAC Address (i.e. 6e:0c:51:c6:c6:3a).
    * For integer[<start>:<end>], the token will be replaced with a random integer between 
      start and end values where <start> is a number greater than 0 
      and <end> is a number greater than 0 and greater than or equal to <start>. If rated,
      will be multiplied times hourOfDayRate and dayOfWeekRate.
    * For float[<start>:<end>], the token will be replaced with a random float between
      start and end values where <end> is a number greater than or equal to <start>.
      For floating point numbers, precision will be based off the precision specified
      in <start>. For example, if we specify 1.0, precision will be one digit, if we specify
      1.0000, precision will be four digits. If rated, will be multiplied times hourOfDayRate and dayOfWeekRate.
    * For string(<i>), the token will be replaced with i number(s) of ASCII characters where 'i' is a number greater than 0.
    * For hex(<i>), the token will be replaced with i number of Hexadecimal characters [0-9A-F] where 'i' is a number greater than 0.
    * For list, the token will be replaced with a random member of the JSON list provided.
    * For <replacement file name>, the token will be replaced with a random line in the replacement file.
      * Replacement file name should be a fully qualified path (i.e. $SPLUNK_HOME/etc/apps/windows/samples/users.list).
      * Windows separators should contain double forward slashes '\\' (i.e. $SPLUNK_HOME\\etc\\apps\\windows\\samples\\users.list).
      * Unix separators will work on Windows and vice-versa.
    * Column numbers in mvfile or seqfile references are indexed at 1, meaning the first column is column 1, not 0.
    * <integer> used as the seed for integerid.
    * Defaults to None.

###### Jinja
The following options are only valid with the jinja generator.

    jinja_template_dir = <str> example: templates
    * directory name inside the current eventgen.conf dir where jinja templates can be located

    jinja_target_template = <str> example: test_jinja.template
    * root template to load for all sample generation

    jinja_variables = <json> example:{"large_number":50000}
    * json value that contains a dict of kv pairs to pass as options to load inside of the jinja templating engine.
    
##### Output Related Settings
These settings all relate to the currently selected output plugin. outputMode will search for a plugin located in either the cwd or lib>plugins>output.
There must be a loaded plugin that has a name corresponding to this value in order for the sample to be loaded. Below are the main outputplugins that ship with
eventgen today, and their values / settings. Please note while some plugins share options, each pluging will implement it's own configuration options.
Please note, any item that says "Required" must be set in order for that respective plugin to function. Anything with a default value will automatically
be set for you in the event you don't supply the configuration option. **If the required field is NOT supplied and a default is NOT set, your sample will be IGNORED.**

    outputMode = modinput | s2s | file | splunkstream | stdout | devnull | spool | httpevent | syslogout | tcpout | udpout
    * Specifies how to output log data.
    * If setting s2s, should set splunkHost and splunkPort
    * If setting syslogout, should set syslogDestinationHost and syslogDestinationPort
    * Defaults to modinput
    
After you've selected what plugin you'd like to use, please check that respective plugin's configuration.
###### Generic Settings
The following are generic items that can be set for all outputplugins, but may not
specifically be supported by all plugins. Plugins that write to files like spool / file, will use Splunk's props/transforms on ingestion no matter what these items are set to.

    index = <index>
    * Only valid with outputMode 'splunkstream'.
    * Splunk index to write events to. Defaults to main if none specified.

    source = <source>
    * Valid with outputMode=modinput (default) & outputMode=splunkstream & outputMode=httpevent
    * Set event source in Splunk to <source>. Defaults to sample file name if none specified.

    sourcetype = <sourcetype>
    * Valid with outputMode=modinput (default) & outputMode=splunkstream & outputMode=httpevent
    * Set event sourcetype in Splunk to <source> Defaults to 'eventgen' if none specified.

    host = <host>
    * When outputMode is splunkstream, set event host in Splunk to <host>.
    * When outputMode is syslogout and syslogAddHeader is set to true, add initial header with hostname <host>,
      see syslogAddHeader for details.
    * Defaults to 127.0.0.1 if none specified.

    host.token = <regular expression>
    * PCRE expression used to identify the host name (or partial name) for replacement.
    * If one or more capture groups are present the replacement will be performed on group 1.
    * Defaults to None.

    host.replacement = <replacement file name> | <replacement file name>:<column number>
    * For <replacement file name>, the token will be replaced with a random line in the replacement file.
      * Replacement file name should be a fully qualified path (i.e. $SPLUNK_HOME/etc/apps/windows/samples/users.list).
      * Windows separators should contain double forward slashes '\\' (i.e. $SPLUNK_HOME\\etc\\apps\\windows\\samples\\users.list).
      * Unix separators will work on Windows and vice-versa.
    * Column numbers in mvfile or seqfile references are indexed at 1, meaning the first column is column 1, not 0.
    * Defaults to None.

    hostRegex = <hostRegex>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Allows setting the event host via a regex from the actual event itself. Only used if host not set.

    maxIntervalsBeforeFlush = <intervals before flushing queue>
    * Number of intervals before flushing the queue if the queue hasn't filled to maxQueueLength
    * Defaults to 3

    maxQueueLength = <maximum items before flushing the queue>
    * Number of items before flushing the output queue
    * Default is per outputMode specific
    
###### syslog
    syslogDestinationHost = <host>
    * Defaults to 127.0.0.1
    * Required

    syslogDestinationPort = <port>
    * Defaults to port 1514
    * Only supports UDP ports
    * Required

    syslogAddHeader = true | false
    * Controls whether syslog messages should be prefixed with an RFC3164 compliant header
      including the host value defined for the sample.
    * Useful in situations where you want to output generated events to syslog and make it
      possible for the receiving syslog server to use the sample's defined host value instead of
      the hostname of the host that eventgen is running on.
    * Defaults to false

###### tcpout
    tcpDestinationHost = <host>
    * Defaults to 127.0.0.1
    * Required

    tcpDestinationPort = <port>
    * Defaults to port 3333
    * Required

###### udpout
    udpDestinationHost = <host>
    * Defaults to 127.0.0.1
    * Required

    udpDestinationPort = <port>
    * Defaults to port 3333
    * Required

###### httpevent
    httpeventServers = <valid json>
    * valid json that contains a list of server objects
    * valid server objects contain a protocol, a address, a port and a session key. Example:
      {"servers":[{ "protocol":"https", "address":"127.0.0.1", "port":"8088", "key":"12345-12345-123123123123123123"}]}
    * Required

    httpeventOutputMode = roundrobin | mirror
    * in roundrobin mode, the HEC plugin will output to a random server out of the server pool
    * in mirror moded, HEC plugin will mirror the event to every server specified in the server pool
    * Defaults to roundrobin

    httpeventMaxPayloadSize = <int>
    * the max payload size that is currently configured for HTTP event
    * This setting can be tuned to send more events than Splunk is configured for. Please use caution when adjusting this value.

    httpeventWaitResponse = <bool>
    * wait for all responses on a generator output before returning the outputter.
    * Defaults to true.

    httpeventAllowFailureCount = <int>
    * Number of transmission failure allowed for a certain httpserver before we remove that server from the pool. For example, 100 means that we will no longer include a specific httpserver after 100 failures. Even after some failures, if we see a success for the server, we will reset the count and continue the transmission.

###### spool
    spoolDir = <spool directory>
    * Spool directory is the generated files destination directory.
    * Only valid in spool outputMode.
    * Windows separators should contain double forward slashes '\\' (i.e. $SPLUNK_HOME\\var\\spool\\splunk).
    * Unix separators will work on Windows and vice-versa.
    * Defaults to $SPLUNK_HOME/var/spool/splunk
    * Required

    spoolFile = <spool file name>
    * Spool file is the generated files name.
    * Not valid if stanza is a pattern.
    * Defaults to <SAMPLE> (sample file name).
    
###### file
    fileName = </path/to/file>
    * Should set the full path
    * Uses a rotating file handler which will rotate the file at a certain size, by default 10 megs
      and will by default only save 5 files. See fileMaxBytes and fileBackupFiles
    * Required

    fileMaxBytes = <size in bytes>
    * Will rotate a file output at this given size
    * Defaults to 10 Megabytes (10485760 bytes)

    fileBackupFiles = <number of files>
    * Will keep this number of files (.1, .2, etc) after rotation
    * Defaults to 5

###### splunkstream
    splunkHost = <host> | <json list of hosts>
    * If you specify just one host, will only POST to that host, if you specify a JSON list,
      it will POST to multiple hosts in a random distribution. This allows us from one eventgen to
      feed an entire cluster of Splunk indexers without needing forwarders.
    * JSON list should look like [ "host.name", "host2.name" ]
    * Required

    splunkPort = <port>
    * Defaults to the default Splunk management port 8089
    * Required

    splunkMethod = http | https
    * Defaults to https
    * Required

    splunkUser = <user>
    * User with rights to post to REST endpoint receivers/stream
    * Required

    splunkPass = <pass>
    * Password for SplunkUser
    * Required

    projectID = <id>
    * Project ID for Splunk Storm

    accessToken = <accesstoken>
    * Access Token for Splunk Storm
    


    
    
    

