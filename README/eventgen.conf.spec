# Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
#
# This file contains all possible options for an eventgen.conf file.  Use this file to configure 
# Splunk's event generation properties.
#
# To generate events place an eventgen.conf in $SPLUNK_HOME/etc/apps/<app>/local/. 
# For examples, see eventgen.conf.example. You must restart Splunk to enable configurations.
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.  
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how 
# to configure this file.
#

## IMPORTANT! Do not specify any settings under a default stanza
## The layering system will not behave appropriately
## Use [global] instead
[default]

[global]
disabled = false
debug = false
spoolDir = $SPLUNK_HOME/var/spool/splunk
spoolFile = <SAMPLE>
breaker = [^\r\n\s]+
mode = sample
sampletype = raw
interval = 60
delay = 0
timeMultiple = 1
## 0 means all lines in sample
count = 0
## earliest/latest = now means timestamp replacements default to current time
earliest = now
latest = now
# hourOfDayRate = { "0": 0.30, "1": 0.10, "2": 0.05, "3": 0.10, "4": 0.15, "5": 0.25, "6": 0.35, "7": 0.50, "8": 0.60, "9": 0.65, "10": 0.70, "11": 0.75, "12": 0.77, "13": 0.80, "14": 0.82, "15": 0.85, "16": 0.87, "17": 0.90, "18": 0.95, "19": 1.0, "20": 0.85, "21": 0.70, "22": 0.60, "23": 0.45 }
# dayOfWeekRate = { "0": 0.97, "1": 0.95, "2": 0.90, "3": 0.97, "4": 1.0, "5": 0.99, "6": 0.55 }
# minuteOfHourRate = { "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, "10": 1, "11": 1, "12": 1, "13": 1, "14": 1, "15": 1, "16": 1, "17": 1, "18": 1, "19": 1, "20": 1, "21": 1, "22": 1, "23": 1, "24": 1, "25": 1, "26": 1, "27": 1, "28": 1, "29": 1, "30": 1, "31": 1, "32": 1, "33": 1, "34": 1, "35": 1, "36": 1, "37": 1, "38": 1, "39": 1, "40": 1, "41": 1, "42": 1, "43": 1, "44": 1, "45": 1, "46": 1, "47": 1, "48": 1, "49": 1, "50": 1, "51": 1, "52": 1, "53": 1, "54": 1, "55": 1, "56": 1, "57": 1, "58": 1, "59": 1 }
randomizeCount = 0.2
randomizeEvents = false
outputMode = spool
fileMaxBytes = 10485760
fileBackupFiles = 5
splunkPort = 8089
splunkMethod = https
index = main
source = eventgen
sourcetype = eventgen
host = 127.0.0.1


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
        
disabled = true | false
    * Like what it looks like.  Will disable event generation for this sample.
        
#############################
## OUTPUT RELATED SETTINGS ##
#############################

outputMode = spool | file | splunkstream | stormstream
    * Specifies how to output log data.  Spool is default (for legacy reasons).
    * If setting spool, should set spoolDir
    * If setting file, should set logFile
    * If setting splunkstream, should set splunkHost, splunkPort, splunkMethod, splunkUser
      and splunkPassword if not Splunk embedded
    * If setting stormstream, should set projectID and accessToken.

spoolDir = <spool directory>
    * Spool directory is the generated files destination directory.
    * Only valid in spool outputMode.
    * Windows separators should contain double forward slashes '\\' (i.e. $SPLUNK_HOME\\var\\spool\\splunk).
    * Unix separators will work on Windows and vice-versa.
    * Defaults to $SPLUNK_HOME/var/spool/splunk
    
spoolFile = <spool file name>
    * Spool file is the generated files name.
    * Not valid if stanza is a pattern.
    * Defaults to <SAMPLE> (sample file name).
    
fileName = </path/to/file>
    * Should set the full path
    * Uses a rotating file handler which will rotate the file at a certain size, by default 10 megs
      and will by default only save 5 files.  See fileMaxBytes and fileBackupFiles
      
fileMaxBytes = <size in bytes>
    * Will rotate a file output at this given size
    * Defaults to 10 Megabytes (10485760 bytes)
    
fileBackupFiles = <number of files>
    * Will keep this number of files (.1, .2, etc) after rotation
    * Defaults to 5
    
splunkHost = <host> | <json list of hosts>
    * If you specify just one host, will only POST to that host, if you specify a JSON list,
      it will POST to multiple hosts in a random distribution.  This allows us from one eventgen to
      feed an entire cluster of Splunk indexers without needing forwarders.
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
    * Splunk index to write events to.  Defaults to main if none specified.
    
source = <source>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Set event source in Splunk to <source>.  Defaults to 'eventgen' if none specified.
    
sourcetype = <sourcetype>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Set event sourcetype in Splunk to <source> Defaults to 'eventgen' if none specified.
    
host = <host>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Set event host in Splunk to <host>.  Defaults to 127.0.0.1 if none specified.
    
hostRegex = <hostRegex>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Allows setting the event host via a regex from the actual event itself.  Only used if host not set.
    
    
###############################
## EVENT GENERATION SETTINGS ##
###############################

mode = sample | replay
    * Default is sample, which will generate count (+/- rating) events every configured interval
    * Replay will instead read the file and leak out events, replacing timestamps, 

sampletype = raw | csv
    * Raw are raw events (default)
    * CSV are from an outputcsv or export from Splunk.
      CSV allows you to override output fields for the sample like host, index, source and sourcetype
      from the CSV file.  Will read the raw events from a field called _raw.  Assumes the CSV file has
      a header row which defines field names.
      OVERRIDES FOR DEFAULT FIELDS WILL ONLY WITH WITH outputMode SPLUNKSTREAM.

interval = <integer>
    * Only valid in mode = sample
    * How often to generate sample (in seconds).
    * 0 means disabled.
    * Defaults to 60 seconds.
   
delay = <integer>
    * Specifies how long to wait until we begin generating events for this sample
    * Primarily this is used so we can stagger sets of samples which similar but slightly different data
    * Defaults to 0 which is disabled.

timeMultiple = <float>
    * Only valid in mode = replay
    * Will slow down the replay of events by <float> factor.  For example, allows a 10 minute sample
      to play out over 20 minutes with a timeMultiple of 2, or 60 minutes with a timeMultiple of 6.
      By the converse, make timeMultiple 0.5 will make the events run twice as fast.

timezone = local | <integer>
    * If set to 'local', will output local time, if set to '0000' will output UTC time
    * Otherwise it must be a timezone offset like +hhmm or -hhmm, for example:
      US Eastern Standard (EST) would be: timezone = -0500
      US Pacific Daylight (PDT) would be: timezone = -0700
      Indian Standard would be timezone = +0530
    * Valid range +2359 to -2359 (The last two digits are MINUTES, so they should be within 0-59)

backfill = <time-str>
    * Specified in Splunk's relative time language, used to set a time to backfill events

backfillSearch = <splunk search>
    * If outputMode = splunkstream, this will run this search, appending '| head 1', and narrow the
      backfill range specified with backfill to when the search has last seen events.

backfillSearchUrl = <url>
    * Defaults to splunkMethod://splunkHost:splunkPort/, can override in case you're running
      in a cluster.
    
count = <integer>
    * Maximum number of events to generate per sample file
    * 0 means replay the entire sample.
    * Defaults to 0.
    
bundlelines = true | false
    * For outside use cases where you need to take all the lines in a sample file and pretend they are
      one event, but count = 0 will not work because you want to replay all the lines more than once.
      Also, please note you can also use breaker=\r*\n\r*\n to break the sample file into multi-line
      transactions that would work better than this as well.  This is also useful where you want to bring
      in sampletype = csv and bundle that multiple times.
    * If bundlelines = true and the token replacementType is replaytimestamp, we will introduce some randomness
      into the times between items in the transaction in microseconds.
    * Will override any breaker setting.
    
hourOfDayRate = <json>
    * Takes a JSON hash of 24 hours with float values to rate limit how many events we should see
      in a given hour.
    * Sample JSON:
      { "0": 0.05, "1": 0.05: "2": 0.07... }
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate, minuteOfHourRate

dayOfWeekRate = <json>
    * Takes a JSON hash of 7 days of the week in Splunk format (0 is Sunday)
    * Sample JSON:
      { "0": 0.55, "1": 0.97, "2": 0.95, "3": 0.90, "4": 0.97, "5": 1.0, "6": 0.99 }
    * If a match is not found, will default to count events
    * Also multiplied times hourOfDayRate, minuteOfHourRate

minuteOfHourRate = <json>
    * Takes a JSON hash of 60 minutes of an hour, starting with 0
    * Sample JSON:
      { "0": 1, "2": 1...}
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate, hourOfDateRate
    
randomizeCount = <float>
    * Will randomize the number of events generated by percentage passed
    * Example values: 0.2, 0.5
    * Recommend passing 0.2 to give 20% randomization either way (plus or minus)
    
randomizeEvents = <boolean>
    * Will randomize the events found in the sample file before choosing the events.
    * NOT SUPPORTED WITH sampletype csv
    
breaker = <regular expression>
    * NOT to be confused w/ props.conf LINE_BREAKER.
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
    
################################
## TOKEN REPLACEMENT SETTINGS ##
################################
    
token.<n>.token = <regular expression>
    * 'n' is a number starting at 0, and increasing by 1.
    * PCRE expression used to identify segment for replacement.
    * If one or more capture groups are present the replacement will be performed on group 1.
    * Defaults to None.
    
token.<n>.replacementType = static | timestamp | replaytimestamp | random | rated | file | mvfile | integerid
    * 'n' is a number starting at 0, and increasing by 1. Stop looking at the filter when 'n' breaks.
    * For static, the token will be replaced with the value specified in the replacement setting.
    * For timestamp, the token will be replaced with the strptime specified in the replacement setting
    * For replaytimestamp, the token will be replaced with the strptime specified in the replacement setting
      but the time will not be based on earliest and latest, but will instead be replaced by looking at the
      offset of the timestamp in the current event versus the first event, and then adding that time difference
      to the timestamp when we started processing the sample.  This allows for replaying events with a
      new timestamp but to look much like the original transaction.  Assumes replacement value is the same
      strptime format as the original token we're replacing, otherwise it will fail.  First timestamp will
      be the value of earliest.  NOT TO BE CONFUSED WITH REPLAY MODE.  Replay mode replays a whole file
      with timing to look like the original file.  This will allow a single transaction to be replayed with some randomness.
    * For random, the token will be replaced with a type aware value (i.e. valid IPv4 Address).
    * For rated, the token will be replaced with a subset of random types (float, integer), which are
      rated by hourOfDayRate and dayOfWeekRate.
    * For file, the token will be replaced with a random value retrieved from a file specified in the replacement setting.
    * For mvfile, the token will be replaced with a random value of a column retrieved from a file specified in the replacement setting.  Multiple files can reference the same source file and receive different columns from the same random line.
    * For integerid, will use an incrementing integer as the replacement.
    * Defaults to None.
    
token.<n>.replacement = <string> | <strptime> | ["list","of","strptime"] | ipv4 | ipv6 | mac | integer[<start>:<end>] | float[<start>:<end>] | string(<i>) | hex(<i>) | <replacement file name> | <replacement file name>:<column number> | <integer>
    * 'n' is a number starting at 0, and increasing by 1. Stop looking at the filter when 'n' breaks.
    * For <string>, the token will be replaced with the value specified.
    * For <strptime>, a strptime formatted string to replace the timestamp with
    * For ["list","of","strptime"], only used with replaytimestamp, a JSON formatted list of strptime
      formats to try.  Will find the replace with the same format which matches the replayed timestamp.
    * For ipv4, the token will be replaced with a random valid IPv4 Address (i.e. 10.10.200.1).
    * For ipv6, the token will be replaced with a random valid IPv6 Address (i.e. c436:4a57:5dea:1035:7194:eebb:a210:6361).
    * For mac, the token will be replaced with a random valid MAC Address (i.e. 6e:0c:51:c6:c6:3a).
    * For integer[<start>:<end>], the token will be replaced with a random integer between 
      start and end values where <start> is a number greater than 0 
      and <end> is a number greater than 0 and greater than or equal to <start>.  If rated,
      will be multiplied times hourOfDayRate and dayOfWeekRate.
    * For float[<start>:<end>], the token will be replaced with a random float between
      start and end values where <start> is a number greater than 0
      and <end> is a number greater than 0 and greater than or equal to <start>.
      For floating point numbers, precision will be based off the precision specified
      in <start>.  For example, if we specify 1.0, precision will be one digit, if we specify
      1.0000, precision will be four digits. If rated, will be multiplied times hourOfDayRate and dayOfWeekRate.
    * For string(<i>), the token will be replaced with i number(s) of ASCII characters where 'i' is a number greater than 0.
    * For hex(<i>), the token will be replaced with i number of Hexadecimal characters [0-9A-F] where 'i' is a number greater than 0.
    * For <replacement file name>, the token will be replaced with a random line in the replacement file.
      * Replacement file name should be a fully qualified path (i.e. $SPLUNK_HOME/etc/apps/windows/samples/users.list).
      * Windows separators should contain double forward slashes '\\' (i.e. $SPLUNK_HOME\\etc\\apps\\windows\\samples\\users.list).
      * Unix separators will work on Windows and vice-versa.
    * Column numbers in mvfile references are indexed at 1, meaning the first column is column 1, not 0.
    * <integer> used as the seed for integerid.
    * Defaults to None.

################################
## HOST REPLACEMENT SETTINGS  ##
################################

host.token = <regular expression>
    * PCRE expression used to identify the host name (or partial name) for replacement.
    * If one or more capture groups are present the replacement will be performed on group 1.
    * Defaults to None.

host.replacement = <replacement file name> | <replacement file name>:<column number>
    * For <replacement file name>, the token will be replaced with a random line in the replacement file.
      * Replacement file name should be a fully qualified path (i.e. $SPLUNK_HOME/etc/apps/windows/samples/users.list).
      * Windows separators should contain double forward slashes '\\' (i.e. $SPLUNK_HOME\\etc\\apps\\windows\\samples\\users.list).
      * Unix separators will work on Windows and vice-versa.
    * Column numbers in mvfile references are indexed at 1, meaning the first column is column 1, not 0.
    * Defaults to None.