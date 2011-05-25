'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 07 2010 14:36:41 SystemUpTime=301740

count = 0
iterations = 100
## 1440 represents 24 hour offset
offset = 1440

## default system uptime (10 seconds)
SystemUpTime = 10

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = offset

###### Simulate Random CPU Utilization
while count < iterations:
	
	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	event = '@@date SystemUpTime=@@SystemUpTime'
	
	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	event = event.replace('@@SystemUpTime', str(SystemUpTime))

	print event
	
	count += 1
	
	## SystemUptime must make sense, so random generation not possible
	randDelta -= offset / iterations
	SystemUpTime += offset * 60 / iterations
