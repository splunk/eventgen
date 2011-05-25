'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
# Mar 08 2010 11:51:37 app="Splunk" StartMode=Auto StartType=startup file_path=/System/Library/StartupItems/Splunk
# Mar 08 2010 11:51:37 app="QuickTimeStreamingServer" StartMode=Auto StartType=startup file_path=/System/Library/StartupItems/QuickTimeStreamingServer
# Mar 08 2010 11:51:37 app="IPFailover" StartMode=Auto StartType=startup file_path=/System/Library/StartupItems/IPFailover

count = 0
iterations = 33
## 1440 represents 24 hour offset
offset = 1440

## array of events
events = ['@@date app="Splunk" StartMode=Disabled StartType=startup file_path=/System/Library/StartupItems/Splunk',
		'@@date app="QuickTimeStreamingServer" StartMode=Auto StartType=startup file_path=/System/Library/StartupItems/QuickTimeStreamingServer',
		'@@date app="IPFailover" StartMode=Auto StartType=login file_path=/System/Library/StartupItems/IPFailover']

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = 0

###### Simulate Random Services
while count < iterations:
	
	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	for event in events:
	
		event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
		print event
	
	count += 1
	randDelta += offset / iterations
