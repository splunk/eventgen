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
spoolDir = $SPLUNK_HOME/var/spool/splunk
spoolFile = <SAMPLE>
interval = 60
## 0 means all lines in sample
count = 0
## earliest/latest = now means timestamp replacements default to current time
earliest = now
latest = now


[<sample file name>]
    * This stanza defines a given sample file contained within the samples directory.
    * This stanza can be specified as a PCRE.
    * Hardcoded to $SPLUNK_HOME/etc/apps/<app>/samples/<sample file name>.
    * This stanza is only valid for the following replacementType -> replacement values:
        * static -> <string>
        * timestamp -> <strptime>
        * random -> ipv4
        * random -> ipv6
        * random -> mac
        * random -> integer[<start>:<end>]
        * random -> string(<integer>)
        * random -> hex([integer])
        * file -> <replacment file name>
        * mvfile -> <replacement file name, expects CSV file>:<column number>
        
disabled = true | false
    * Like what it looks like.  Will disable event generation for this sample.
        
outputMode = spool | file | splunkstream
    * Specifies how to output log data.  Spool is default (for legacy reasons).
    * If setting spool, should set spoolDir
    * If setting file, should set logFile
    * If setting splunkstream, should set splunkHost, splunkPort, splunkMethod, splunkUser
      and splunkPassword if not Splunk embedded

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
    
index = <index>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Splunk index to write events to.  Defaults to main if none specified.
    
source = <source>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Set event source in Splunk to <source>.  Defaults to 'eventgen' if none specified.
    
sourcetype = <sourcetype>
    * ONLY VALID WITH outputMode SPLUNKSTREAM
    * Set event sourcetype in Splunk to <source> Defaults to 'eventgen' if none specified.
    
interval = <integer>
   * How often to generate sample (in seconds).
   * 0 means disabled.
   * Defaults to 60 seconds.  
    
count = <integer>
    * Maximum number of events to generate per sample file
    * 0 means sample length.
    * Defaults to 0.
    
hourOfDayRate = <json>
    * Takes a JSON hash of 24 hours with float values to rate limit how many events we should see
      in a given hour.
    * Sample JSON:
      { "0": 0.05, "1": 0.05: "2": 0.07... }
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate

dayOfWeekRate = <json>
    * Takes a JSON hash of 7 days of the week in Splunk format (0 is Sunday)
    * Sample JSON:
      { "0": 0.97, "1": 0.95, "2": 0.90, "3": 0.97, "4": 1.0, "5": 0.99, "6": 0.55 }
    * If a match is not found, will default to count events
    * Also multiplied times dayOfWeekRate
    
randomizeCount = <float>
    * Will randomize the number of events generated by percentage passed
    * Example values: 0.2, 0.5
    * Recommend passing 0.2 to give 20% randomization either way (plus or minus)
    
randomizeEvents = <boolean>
    * Will randomize the events found in the sample file before choosing the events.
    
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
    
token.<n>.token = <regular expression>
    * 'n' is a number starting at 0, and increasing by 1.
    * PCRE expression used to identify segment for replacement.
    * If one or more capture groups are present the replacement will be performed on group 1.
    * Defaults to None.
    
token.<n>.replacementType = static | timestamp | random | file | mvfile
    * 'n' is a number starting at 0, and increasing by 1. Stop looking at the filter when 'n' breaks.
    * For static, the token will be replaced with the value specified in the replacement setting.
    * For timestamp, the token will be replaced with the strptime specified in the replacement setting
    * For random, the token will be replaced with a type aware value (i.e. valid IPv4 Address).
    * For file, the token will be replaced with a random value retrieved from a file specified in the replacement setting.
    * For mvfile, the token will be replaced with a random value of a column retrieved from a file specified in the replacement setting.  Multiple files can reference the same source file and receive different columns from the same random line.
    * Defaults to None.
    
token.<n>.replacement = <string> | <strptime> | ipv4 | ipv6 | mac | integer[<start>:<end>] | string(<i>) | hex(<i>) | <replacement file name> | <replacement file name>:<column number>
    * 'n' is a number starting at 0, and increasing by 1. Stop looking at the filter when 'n' breaks.
    * For <string>, the token will be replaced with the value specified.
    * For ipv4, the token will be replaced with a random valid IPv4 Address (i.e. 10.10.200.1).
    * For ipv6, the token will be replaced with a random valid IPv6 Address (i.e. c436:4a57:5dea:1035:7194:eebb:a210:6361).
    * For mac, the token will be replaced with a random valid MAC Address (i.e. 6e:0c:51:c6:c6:3a).
    * For integer[<start>:<end>], the token will be replaced with a random integer between 
      start and end values where <start> is a number greater than 0 
      and <end> is a number greater than 0 and greater than or equal to <start>
    * For string(<i>), the token will be replaced with i number(s) of ASCII characters where 'i' is a number greater than 0.
    * For hex(<i>), the token will be replaced with i number of Hexadecimal characters [0-9A-F] where 'i' is a number greater than 0.
    * For <replacement file name>, the token will be replaced with a random line in the replacement file.
      * Replacement file name should be a fully qualified path (i.e. $SPLUNK_HOME/etc/apps/windows/samples/users.list).
      * Windows separators should contain double forward slashes '\\' (i.e. $SPLUNK_HOME\\etc\\apps\\windows\\samples\\users.list).
      * Unix separators will work on Windows and vice-versa.
    * Column numbers in mvfile references are indexed at 1, meaning the first column is column 1, not 0.
    * Defaults to None.