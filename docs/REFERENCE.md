## eventgen.conf.spec ##

```
# Copyright (C) 2005-2019 Splunk Inc. All Rights Reserved.
#
# This file contains all possible options for an eventgen.conf file.
# Use this file to configure Splunk's event generation properties.
#
# To generate events place an eventgen.conf in $SPLUNK_HOME/etc/apps/<app>/local/.
# For example, see eventgen.conf.example. You must restart Splunk to enable configurations.
#
# To learn more about configuration files (including precedence) please see the documentation
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#
# CAUTION: You can drastically affect your Splunk installation by changing these settings.
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are
# not sure how to configure this file.

## IMPORTANT! Do not specify any settings under a default stanza
## The layering system will not behave appropriately
## Use [global] instead
[default]

[global]
disabled = false
debug = false
verbosity = false
spoolDir = $SPLUNK_HOME/var/spool/splunk
spoolFile = <SAMPLE>
breaker = [^\r\n\s]+
mode = sample
sampletype = raw
interval = 60
delay = 0
timeMultiple = 1
count = -1
earliest = now
latest = now
randomizeCount = 0.2
randomizeEvents = false
outputMode = spool
fileMaxBytes = 10485760
fileBackupFiles = 5
splunkPort = 8089
splunkMethod = https
index = main
sourcetype = eventgen
host = 127.0.0.1
outputWorkers = 1
generatorWorkers = 1
generator = default
rater = config
timeField = _raw
threading = thread
profiler = false
maxIntervalsBeforeFlush = 3
maxQueueLength = 0
autotimestamps = [ <jsonlist> ]
autotimestamp = false
outputCounter = false
disableLoggingQueue = true


[<sample file name>]
    * This stanza defines a given sample file contained within the samples directory.
    * This stanza can be specified as a PCRE.
    * Hardcoded to $SPLUNK_HOME/etc/apps/<app>/samples/<sample file name>.
    * This stanza is only valid for the following replacementType -> replacement values:
        * static -> <string>
        * timestamp -> <strptime>
        * replaytimestamp -> <strptime>
        * random -> ipv4
        * random -> ipv6
        * random -> mac
        * random -> integer[<start>:<end>]
        * random -> float[<start.numzerosforprecision>:<end.numzerosforprecision>]
        * random -> string(<integer>)
        * random -> hex([integer])
        * rated -> integer[<start>:<end>]
        * rated -> float[<start.numzerosforprecision>:<end.numzerosforprecision>]
        * file -> <replacment file name>
        * mvfile -> <replacement file name, expects CSV file>:<column number>
        * seqfile -> <replacment file name> OR <replacement file name,
          expects CSV file>:<column number>

disabled = true | false
    * Like what it looks like. Will disable event generation for this sample.

sampleDir = <dir>
    * Set a different directory to look for samples in

threading = thread | process
    * Configurable threading model.
    * Process uses multiprocessing. Process in Python to get around issues with the GIL.
    * Defaults to thread

profiler = true | false
    * Run eventgen with python profiler on
    * Defaults to false

useOutputQueue = true | false
    * Disable the use of the output Queue.
    * The output queue functions as a reduce step when you need to maintain
      a single thread or a limited number of threads outputting data,
      for instance if you're outputting to a file or to stdout/modular input.
    * Default value depends on the output plugin being used.

disableLoggingQueue = true | false
    * Disable the logging queue for process mode
    * In process mode, logs in each process will be collected via a logging queue
    * Default is true which will disable the logging queue

#############################
## OUTPUT RELATED SETTINGS ##
#############################

outputWorkers = <number of worker threads>
    * Deprecated. This will be removed in future releases.
    * Specifies how many threads or processes to stand up to handle output
    * Generally if using TCP based outputs like splunkstream, more could be required
    * Defaults to 1

outputMode = scsout | modinput | s2s | file | splunkstream | stdout | devnull | spool | httpevent | syslogout | tcpout | udpout | metric_httpevent
    * Specifies how to output log data. Modinput is default.
    * If setting scsout, should set scsEndPoint and scsAccessToken. scsClientId, scsClientSecret, and scsRetryNum are optional.
    * If setting spool, should set spoolDir
    * If setting file, should set fileName
    * If setting splunkstream, should set splunkHost, splunkPort, splunkMethod,
      splunkUser and splunkPassword if not Splunk embedded
    * If setting s2s, should set splunkHost and splunkPort
    * If setting syslogout, should set syslogDestinationHost and syslogDestinationPort. A UDP port listening on Splunk needs to be configured. https://docs.splunk.com/Documentation/Splunk/latest/Data/HowSplunkEnterprisehandlessyslogdata
    * If setting httpevent, should set httpeventServers
    * If setting metric_httpevent, should set httpeventServers and make sure your index is a splunk metric index

scsEndPoint = <host>
    * Should be a full url to the scs endpoint

scsAccessToken = <token>
    * Should be a scs access token. Do not include "Bearer".

scsClientId = <id>
    * Optional
    * SCS client id that is used to renew the access token if it expires during the data generation
    * If not supplied, will not renew the access token and data transmission might fail

scsClientSecret = <secret>
    * Optional
    * SCS client secret that is used to renew the access token if it expires during the data generation
    * If not supplied, will not renew the access token and data transmission might fail

scsRetryNum = <int>
    * Optional and defaults to 0
    * Retry a failing data transmission batch

syslogDestinationHost = <host>
    * Defaults to 127.0.0.1

syslogDestinationPort = <port>
    * Defaults to port 1514
    * Only supports UDP ports

syslogAddHeader = true | false
    * Defaults to false

tcpDestinationHost = <host>
    * Defaults to 127.0.0.1

tcpDestinationPort = <port>
    * Defaults to port 3333

udpDestinationHost = <host>
    * Defaults to 127.0.0.1

udpDestinationPort = <port>
    * Defaults to port 3333

httpeventServers = <valid json>
    * valid json that contains a list of server objects
    * valid server objects contain a protocol, a address, a port and a session key
    * {"servers":[{ "protocol":"https", "address":"127.0.0.1", "port":"8088", "key":"12345-12345-123123123123123123"}]}

httpeventOutputMode = roundrobin | mirror
    * in roundrobin mode, the HEC/Battlecat plugin will output to
      a random server out of the server pool
    * in mirror moded, HEC/Battlecat plugin will mirror the event to
      every server specified in the server pool

httpeventMaxPayloadSize = <int>
    * the max payload size that is currently configured for HTTP event

httpeventWaitResponse = <bool>
    * wait for all responses on a generator output before returning the outputter.
    * Defaults to true.

httpeventAllowFailureCount = <int>
    * Number of transmission failure allowed for a certain httpserver before we remove that server from the pool. For example, 100 means that we will no longer include a specific httpserver after 100 failures. Even after some failures, if we see a success for the server, we will reset the count and continue the transmission.

spoolDir = <spool directory>
    * Spool directory is the generated files destination directory.
    * Only valid in spool outputMode.
    * Windows separators should contain double forward slashes '\\'.
      (i.e. $SPLUNK_HOME\\var\\spool\\splunk)
    * Unix separators will work on Windows and vice-versa.
    * Defaults to $SPLUNK_HOME/var/spool/splunk

spoolFile = <spool file name>
    * Spool file is the generated files name.
    * Not valid if stanza is a pattern.
    * Defaults to <SAMPLE> (sample file name).

fileName = </path/to/file>
    * Should set the full path
    * Uses a rotating file handler which will rotate the file at a certain size,
      by default 10 megs and will by default only save 5 files.
      See fileMaxBytes and fileBackupFiles

fileMaxBytes = <size in bytes>
    * Will rotate a file output at this given size
    * Defaults to 10 Megabytes (10485760 bytes)

fileBackupFiles = <number of files>
    * Will keep this number of files (.1, .2, etc) after rotation
    * Defaults to 5

splunkHost = <host> | <json list of hosts>
    * If you specify just one host, will only POST to that host.
      If you specify a JSON list, it will POST to multiple hosts in a random distribution.
      This allows us from one eventgen to feed an entire cluster of Splunk indexers without
      needing forwarders.
    * JSON list should look like [ "host.name", "host2.name" ]

splunkPort = <port>
    * Defaults to the default Splunk management port 8089

splunkMethod = http | https
    * Defaults to https

splunkUser = <user>
    * User with rights to post to REST endpoint receivers/stream

splunkPass = <pass>
    * Password for SplunkUser

projectID = <id>
    * Project ID for Splunk Storm

accessToken = <accesstoken>
    * Access Token for Splunk Storm

index = <index>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Splunk index to write events to. Defaults to main if none specified.

extendIndexes = <index_prefix>:<weight>,<index2>,<index3>
    * Sample level setting.
      Use this setting enable eventgen to generate multi indexes for one sample.
    * If you set the value with pattern like "<index_prefix>:<weight>",
      it will treat <index_prefix> as a prefix of an actual index,
    * <weight> is an integer that indicates the count of index you want to extend
      for this sample. eg: events from a sample with "extendIndexes = test_:5, main, web"
      setting will be added with indexes "test_0, test_1, test_2, test_3, test_4, main, web"
      randomly.

source = <source>
    * Valid with the following outputMode:
      outputMode=modinput (default) & outputMode=splunkstream & outputMode=httpevent
    * Set event source in Splunk to <source>. Defaults to sample file name if none specified.

sourcetype = <sourcetype>
    * Valid with the following outputMode:
      outputMode=modinput (default) & outputMode=splunkstream & outputMode=httpevent
    * Set event sourcetype in Splunk to <source>. Defaults to 'eventgen' if none specified.

host = <host>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Set event host in Splunk to <host>. Defaults to 127.0.0.1 if none specified.

hostRegex = <hostRegex>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Allows setting the event host via a regex from the actual event itself.
    * Only used if host not set.

maxIntervalsBeforeFlush = <intervals before flushing queue>
    * Number of intervals before flushing the queue if the queue hasn't
      filled to maxQueueLength
    * Defaults to 3

maxQueueLength = <maximum items before flushing the queue>
    * Number of items before flushing the output queue
    * Default is per outputMode specific

outputCounter = true | false
    * Default is false.
    * Use outputCounter to record your output rate so that you can get the total volume,
      total count and real-time throughput of outputer from "status" api.
    * This setting may cause 1.8% performance down. Only work on thread mode.

###############################
## EVENT GENERATION SETTINGS ##
###############################

generator = default | <plugin>
    * Specifies the generator plugin to use. Default generator will give behavior
      of eventgen pre-3.0 which exclusively uses settings in eventgen.conf
      to control behavior. Generators in 3.0 are now pluggable python modules
      which can be custom code.

generatorWorkers = <number of worker threads>
    * Specifies how many threads or processes to stand up to handle generation
    * Defaults to 1

rater = config | <plugin>
    * Specifies which rater plugin to use.
      Default rater uses hourOfDayRate, etc, settings to specify how to affect
      the count of events being generated. Raters in 3.0 are now pluggable python modules.

mode = sample | replay
    * Default is sample, which will generate count (+/- rating) events
      every configured interval
    * Replay will instead read the file and leak out events, replacing timestamps

sampletype = raw | csv
    * Raw are raw events (default)
    * CSV are from an outputcsv or export from Splunk.
      CSV allows you to override output fields for the sample like
      host, index, source and sourcetype from the CSV file. Will read the raw events
      from a field called _raw. Assumes the CSV file has a header row which
      defines field names.
      OVERRIDES FOR DEFAULT FIELDS WILL ONLY WORK WITH outputMode SPLUNKSTREAM.

interval = <integer>
    * Delay between exections.  This number in replay mode occurs after the replay has finished.
    * How often to generate sample (in seconds).
    * 0 means disabled.
    * Defaults to 60 seconds.

delay = <integer>
    * Specifies how long to wait until we begin generating events for this sample
    * Primarily this is used so we can stagger sets of samples which similar
      but slightly different data
    * Defaults to 0 which is disabled.

sequentialTimestamp = <boolean>
    * Only valid on count mode. (perDayVolume mode is not work)
    * Timestamp will be set from your "earliest" time to "latest" time sequentiallly.
      For example, if "earliest=-1d", "latest=now" and "count=86400",
      then you can see all events have different timestamp.

autotimestamp = <boolean>
    * Will enable autotimestamp feature which detects most common forms of timestamps
      in your samples with no configuration.

timeMultiple = <float>
    * Only valid in mode = replay
    * Will slow down the replay of events by <float> factor.
      This is achieved by calculating the interval between events and adjusting
      the interval by the timeMultiple factor. For example, allows a 10 minute sample
      to play out over 20 minutes with a timeMultiple of 2, or 60 minutes with a
      timeMultiple of 6. By the converse, make timeMultiple 0.5 will make the events
      run twice as fast. NOTE that the interval timeMultiple is adjusting is actual
      time interval between events in your sample file. "timeMultiple" option should not
      affect your "interval" option.

timeField = <field name>
    * Only valid in mode = replay
    * Will select the field to find the timestamp in. In many cases, time will come
      from a different field in the CSV.

timezone = local | <integer>
    * If set to 'local', will output local time, if set to '0000' will output UTC time
    * Otherwise it must be a timezone offset like +hhmm or -hhmm, for example:
      US Eastern Standard (EST) would be: timezone = -0500
      US Pacific Daylight (PDT) would be: timezone = -0700
      Indian Standard would be timezone = +0530
    * Valid range +2359 to -2359
      (The last two digits are MINUTES, so they should be within 0-59)

backfill = <time-str>
    * Specified in Splunk's relative time language, used to set a time to backfill events

end = <time-str> | <integer>
    * Will end execution on a specific time or a number of events
    * Can be used to execute only a specified number of intervals or with
      backfill to generate events over a specific time window.

backfillSearch = <splunk search>
    * If outputMode = splunkstream, this will run this search,
      appending '| head 1', and narrow the backfill range specified with
      backfill to when the search has last seen events.

backfillSearchUrl = <url>
    * Defaults to splunkMethod://splunkHost:splunkPort/, can override in case
      you're running in a cluster.

count = <integer>
    * Maximum number of events to generate per sample file (only used with sample mode).
    * -1 means replay the entire sample.
    * Defaults to -1.
    * When count is -1 and the default generator is used,
      count depends on the size of the sample.

perDayVolume = <float>
    * This is used in place of count. The perDayVolume is a size supplied in GB per Day.
      This value will allow eventgen to supply a target datavolume instead of
      a count for event generation.
    * Defaults to Null

bundlelines = true | false
    * For outside use cases where you need to take all the lines in a sample file
      and pretend they are one event. Also, please note you can also use
      breaker=\r*\n\r*\n to break the sample file into multi-line transactions
      that would work better than this as well. This is also useful where you
      want to bring in sampletype = csv and bundle that multiple times.
    * If bundlelines = true and the token replacementType is replaytimestamp,
      we will introduce some randomness into the times between items in the
      transaction in microseconds.
    * Will override any breaker setting.

hourOfDayRate = <json>
    * Takes a JSON hash of 24 hours with float values to rate limit how many
      events we should see in a given hour.
    * Sample JSON:
      { "0": 0.05, "1": 0.05: "2": 0.07... }
    * If a match is not found, will default to count events.
    * Also multiplied times dayOfWeekRate, minuteOfHourRate, dayOfMonthRate,
      monthOfYearRate.

dayOfWeekRate = <json>
    * Takes a JSON hash of 7 days of the week in Splunk format (0 is Sunday)
    * Sample JSON:
      { "0": 0.55, "1": 0.97, "2": 0.95, "3": 0.90, "4": 0.97, "5": 1.0, "6": 0.99 }
    * If a match is not found, will default to count events.
    * Also multiplied times hourOfDayRate, minuteOfHourRate, dayOfMonthRate,
      monthOfYearRate.

minuteOfHourRate = <json>
    * Takes a JSON hash of 60 minutes of an hour, starting with 0
    * Sample JSON:
      { "0": 1, "1": 1...}
    * If a match is not found, will default to count events.
    * Also multiplied times dayOfWeekRate, hourOfDateRate, dayOfMonthRate,
      monthOfYearRate.

dayOfMonthRate = <json>
    * Takes a JSON hash of 31 days of the month, starting with 1
    * Sample JSON:
      { "1": 1, "1": 1...}
    * If a match is not found, will default to count events.
    * Also multiplied times dayOfWeekRate, hourOfDateRate, minuteOfHourRate,
      monthOfYearRate.

monthOfYearRate = <json>
    * Takes a JSON hash of 12 months of a year, starting with 1
    * Sample JSON:
      { "1": 1, "2": 1...}
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate, hourOfDateRate, minuteOfHourRate,
      dayOfMonthRate.

randomizeCount = <float>
    * Will randomize the number of events generated by percentage passed
    * Example values: 0.2, 0.5
    * Recommend passing 0.2 to give 20% randomization either way (plus or minus)

randomizeEvents = <boolean>
    * Will randomize the events found in the sample file before choosing the events.
    * NOT SUPPORTED WITH sampletype csv
    * NOT SUPPORTED WITH mode = replay OR custom generators like generator = replay

breaker = <regular expression>
    * NOT to be confused with props.conf LINE_BREAKER.
    * PCRE used for flow control.
    * If count > 0; data will be generated until number of discovered breakers <= "count".
    * If breaker does not match in sample, one iteration of sample will be generated.
    * Defaults to [^\r\n\s]+

earliest = <time-str>
    * Specifies the earliest random time for generated events.
    * If this value is an absolute time, use the dispatch.time_format to format the value.
    * Defaults to now.

latest = <time-str>
    * Specifies the latest random time for generated events.
    * If this value is an absolute time, use the dispatch.time_format to format the value.
    * Defaults to now.

#############################
## JINJA TEMPLATE SETTINGS ##
#############################

jinja_template_dir = <str>
    * directory name inside the current eventgen.conf dir where
      jinja templates can be located.
    * default template directory is <bundle>/samples/templates if not defined.
jinja_target_template = <str>
    * root template to load for all sample generation.
jinja_variables = <json>
    * json value that contains a dict of kv pairs to pass as options to
      load inside of the jinja templating engine.

################################
## TOKEN REPLACEMENT SETTINGS ##
################################

token.<n>.token = <regular expression>
    * 'n' is a number starting at 0, and increasing by 1.
    * PCRE expression used to identify segment for replacement.
    * If one or more capture groups are present the replacement
      will be performed on group 1.
    * Defaults to None.

token.<n>.replacementType = static | timestamp | replaytimestamp | random | rated | file | mvfile | integerid
    * 'n' is a number starting at 0, and increasing by 1.
      Stop looking at the filter when 'n' breaks.
    * For static, the token will be replaced with the value specified
      in the replacement setting.
    * For timestamp, the token will be replaced with the strptime specified
      in the replacement setting. Strptime directive:
      https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
      Note `%z` only matches against GMT, UTC and `time.tzname`:
      https://bugs.python.org/issue22377.
    * For replaytimestamp, the token will be replaced with the strptime specified
      in the replacement setting but the time will not be based on earliest and latest,
      but will instead be replaced by looking at the offset of the timestamp in the
      current event versus the first event, and then adding that time difference
      to the timestamp when we started processing the sample.
      This allows for replaying events with a new timestamp but to look much like
      the original transaction. Assumes replacement value is the same strptime format
      as the original token we're replacing, otherwise it will fail. First timestamp will
      be the value of earliest. NOT TO BE CONFUSED WITH REPLAY MODE.
      Replay mode replays a whole file with timing to look like the original file.
      This will allow a single transaction to be replayed with some randomness.
    * For random, the token will be replaced with a type aware value
      (i.e. valid IPv4 Address).
    * For rated, the token will be replaced with a subset of random types
      (float, integer), which are rated by hourOfDayRate and dayOfWeekRate.
    * For file, the token will be replaced with a random value retrieved from a
      file specified in the replacement setting.
    * For mvfile, the token will be replaced with a random value of a column
      retrieved from a file specified in the replacement setting.
      Multiple files can reference the same source file and receive different
      columns from the same random line.
    * For integerid, will use an incrementing integer as the replacement.
    * Defaults to None.

token.<n>.replacement = <string> | <strptime> | ["list","of","strptime"] | guid | ipv4 | ipv6 | mac | integer[<start>:<end>] | float[<start>:<end>] | string(<i>) | hex(<i>) | list["list", "of", "values"] | <replacement file name> | <replacement file name>:<column number> | <integer>
    * 'n' is a number starting at 0, and increasing by 1.
      Stop looking at the filter when 'n' breaks.
    * For <string>, the token will be replaced with the value specified.
    * For <strptime>, a strptime formatted string to replace the timestamp with
    * For ["list","of","strptime"], only used with replaytimestamp,
      a JSON formatted list of strptime formats to try.
      Will find the replace with the same format which matches the replayed timestamp.
    * For guid, the token will be replaced with a random GUID value.
    * For ipv4, the token will be replaced with a random valid IPv4 Address
      (i.e. 10.10.200.1).
    * For ipv6, the token will be replaced with a random valid IPv6 Address
      (i.e. c436:4a57:5dea:1035:7194:eebb:a210:6361).
    * For mac, the token will be replaced with a random valid MAC Address
      (i.e. 6e:0c:51:c6:c6:3a).
    * For integer[<start>:<end>], the token will be replaced with a random integer
      between start and end values where <start> is a number greater than 0
      and <end> is a number greater than 0 and greater than or equal to <start>.
      If rated, will be multiplied times hourOfDayRate and dayOfWeekRate.
    * For float[<start>:<end>], the token will be replaced with a random float between
      start and end values where <end> is a number greater than or equal to <start>.
      For floating point numbers, precision will be based off the precision specified
      in <start>. For example, if we specify 1.0, precision will be one digit,
      if we specify 1.0000, precision will be four digits. If rated,
      will be multiplied times hourOfDayRate and dayOfWeekRate.
    * For string(<i>), the token will be replaced with i number(s) of
      ASCII characters where 'i' is a number greater than 0.
    * For hex(<i>), the token will be replaced with i number of
      Hexadecimal characters [0-9A-F] where 'i' is a number greater than 0.
    * For list, the token will be replaced with a random member of the JSON list provided.
    * For <replacement file name>, the token will be replaced with a
      random line in the replacement file.
      * Replacement file name should be a fully qualified path
        (i.e. $SPLUNK_HOME/etc/apps/windows/samples/users.list).
      * Windows separators should contain double forward slashes '\\'
        (i.e. $SPLUNK_HOME\\etc\\apps\\windows\\samples\\users.list).
      * Unix separators will work on Windows and vice-versa.
    * Column numbers in mvfile references are indexed at 1,
      meaning the first column is column 1, not 0.
    * <integer> used as the seed for integerid.
    * Defaults to None.

################################
## HOST REPLACEMENT SETTINGS  ##
################################

host.token = <regular expression>
    * PCRE expression used to identify the host name (or partial name)
      for replacement.
    * If one or more capture groups are present the replacement will
      be performed on group 1.
    * Defaults to None.

host.replacement = <replacement file name> | <replacement file name>:<column number>
    * For <replacement file name>, the token will be replaced with
      a random line in the replacement file.
      * Replacement file name should be a fully qualified path
        (i.e. $SPLUNK_HOME/etc/apps/windows/samples/users.list).
      * Windows separators should contain double forward slashes '\\'
        (i.e. $SPLUNK_HOME\\etc\\apps\\windows\\samples\\users.list).
      * Unix separators will work on Windows and vice-versa.
    * Column numbers in mvfile references are indexed at 1,
      meaning the first column is column 1, not 0.
    * Defaults to None.
```

## REST API Reference ##

API endpoints for Eventgen Controller

Note, "TARGET_NAME" is a variable that should be replaced by the hostname of Eventgen instance

* ```GET /index```
    * Returns an index page for a Eventgen controller
* ```GET /status```
    * Returns status of all Eventgen instances in JSON
* ```GET /status/<TARGET_NAME>```
    * Returns status of target Eventgen instance in JSON
* ```POST /start```
    * Starts all Eventgen instances' data generation
* ```POST /start/<TARGET_NAME>```
    * Starts target Eventgen instance's data generation
* ```POST /stop```
    * Stops all Eventgen instances' data generation
    * body is optional; default is false. Setting force to true will destroy current Queues and trying to hard stop a running Eventgen object by causing errors.
        * Format: ```{"force": true}``` or ```{"force": false}```
* ```POST /stop/<TARGET_NAME>```
    * Stops target Eventgen instance's data generation
    * body is optional; default is false. Setting force to true will destroy current Queues and trying to hard stop a running Eventgen object by causing errors.
        * Format: ```{"force": true}``` or ```{"force": false}```
* ```POST /restart```
    * Restarts all Eventgen instances' data generation
* ```POST /restart/<TARGET_NAME>```
    * Restarts target Eventgen instance's data generation
* ```GET /conf```
    * Returns a config object of all Eventgen instances in JSON
* ```GET /conf/<TARGET_NAME>```
    * Returns a config object of target Eventgen instance in JSON
* ```POST /conf```
    * Overwrites a config object of all Eventgen instances with a given parameter
    * body={JSON_REPRESENTATION_OF_CONFIG_FILE}, it will overwrite the existing config file with the content.
        * Format: ```{"{SAMPLE}": {"{CONF_KEY}": "{CONF_VALUE}"}}```
            * For example, ```{"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}```
* ```POST /conf/<TARGET_NAME>```
    * Overwrites a config object of target Eventgen instance with a given parameter
    * body={JSON_REPRESENTATION_OF_CONFIG_FILE}, it will overwrite the existing config file with the content.
        * Format: ```{"{SAMPLE}": {"{CONF_KEY}": "{CONF_VALUE}"}}```
            * For example, ```{"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}```
* ```PUT /conf```
    * With a given parameter, only overwrites a matching config item of all Eventgen instances.
    * body={JSON_REPRESENTATION_OF_CONFIG_FILE}, it will only replace matching values in existing configfile.
        * Format: ```{"{SAMPLE}": {"{CONF_KEY}": "{CONF_VALUE}"}}```
            * For example, ```{"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}```
* ```PUT /conf/<TARGET_NAME>```
    * With a given parameter, only overwrites a matching config item of target Eventgen instance.
    * body={JSON_REPRESENTATION_OF_CONFIG_FILE}, it will only replace matching values in existing configfile.
        * Format: ```{"{SAMPLE}": {"{CONF_KEY}": "{CONF_VALUE}"}}```
            * For example, ```{"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}```
* ```POST /bundle```
    * body={"url": "{BUNDLE_URL}"}
        * Pass in a URL to an app/bundle of Eventgen files to seed configurations and sample files.
        * Format: ```{"url": "{BUNDLE_URL}"}```
    * Example: ```curl http://localhost:9500/bundle -X POST -d '{"url": "http://artifact.server.com/eventgen-bundle.tgz "}'```
* ```POST /bundle/<TARGET_NAME>```
    * body={"url": "{BUNDLE_URL}"}
        * Pass in a URL to an app/bundle of Eventgen files to seed configurations and sample files.
        * Format: ```{"url": "{BUNDLE_URL}"}```
    * Example: ```curl http://localhost:9500/bundle -X POST -d '{"url": "http://artifact.server.com/eventgen-bundle.tgz "}'```
* ```POST /setup```
    * body={ARGUMENTS}
        * Format: ```{"mode": "", "hostname_template": "", "protocol": "", "key": "", "key_name": "", "password": "", "hec_port": "", "mgmt_port": "", "new_key": ""}```
            * Default values
                * mode: "roundrobin"
                * hostname_template: "idx{0}"
                * hosts: [] # list of host addresses
                * protocol: "https"
                * key: "00000000-0000-0000-0000-000000000000"
                * key_name: "eventgen"
                * password: "Chang3d!"
                * hec_port: 8088
                * mgmt_port: 8089
                * new_key: True
* ```POST /setup/<TARGET_NAME>```
    * body={ARGUMENTS}
        * Format: ```{"mode": "", "hostname_template": "", "protocol": "", "key": "", "key_name": "", "password": "", "hec_port": "", "mgmt_port": "", "new_key": ""}```
            * Default values
                * mode: "roundrobin"
                * hostname_template: "idx{0}"
                * hosts: [] # list of host addresses
                * protocol: "https"
                * key: "00000000-0000-0000-0000-000000000000"
                * key_name: "eventgen"
                * password: "Chang3d!"
                * hec_port: 8088
                * mgmt_port: 8089
                * new_key: True
* ```GET /volume```
    Returns the cumulative perDayVolume for the current configuration of Eventgen.
    If you have multiple samples with varying perDayVolume specifications, this will return the sum of all your samples.
    * Example:
        ```
        $ curl http://localhost:9500/volume
        ```
* ```GET /volume/<TARGET_NAME>```
    Returns the cumulative perDayVolume for the current configuration of Eventgen for that particular node.
    If you have multiple samples with varying perDayVolume specifications, this will return the sum of all your samples.
    * Example:
        ```
        $ curl http://localhost:9500/volume/egx1
        ```
* ```POST /volume```
    * body
        * perDayVolume={NUMBER}
            * Pass in the desired cumulative perDayVolume you want to scale each Eventgen server's configuraton to.
            * If you have multiple samples with varying perDayVolume specifications, the perDayVolume will scale each sample identically to meet this desired number.
    * Example:
        ```
        $ curl http://localhost:9500/volume -X POST -d '{"perDayVolume": 200}'
        ```
* ```POST /volume/<TARGET_NAME>```
    * body
        * perDayVolume={NUMBER}
            * Pass in the desired cumulative perDayVolume you want to scale each Eventgen server's configuraton to.
            * If you have multiple samples with varying perDayVolume specifications, the perDayVolume will scale each sample identically to meet this desired number.
    * Example:
        ```
        $ curl http://localhost:9500/volume/egx1 -X POST -d '{"perDayVolume": 200}'
        ```
* ```POST /reset```
    * Stops a running Eventgen run, reset the Eventgen Core Object, and reconfigure the server.
    * Example:
        ```
        $ curl http://localhost:9500/reset -X POST
        ```

* ```POST /reset/<TARGET_NAME>```
    * Stops a running Eventgen run, reset the Eventgen Core Object, and reconfigure the server.
    * Example:
        ```
        $ curl http://localhost:9500/reset/egx1 -X POST
        ```

