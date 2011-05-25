'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 05 2010 15:49:28 PercentUserTime=8.4 PercentSystemTime=0.2 PercentIdleTime=88.0

count = 0
iterations = 100
## 1440 represents 24 hour offset
offset = 1440

## get the current date and time
nowTime = datetime.datetime.now()

## generate a number representing minutes offset
randDelta = random.randrange(0,offset,1)
	
## create deltaTime
deltaTime = datetime.timedelta(minutes=randDelta)
	
## compute time delta
deltaTime = nowTime - deltaTime

###### Simulate 100 % CPU Utilization ######
event = '@@date PercentUserTime=@@PercentUserTime PercentSystemTime=@@PercentSystemTime PercentIdleTime=@@PercentIdleTime'

event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
event = event.replace('@@PercentUserTime', str(1))
event = event.replace('@@PercentSystemTime', str(99))
event = event.replace('@@PercentIdleTime', str(0))

print event
	
iterations -= 1
randDelta = 0

###### Simulate Random CPU Utilization
while count < iterations:
	
	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	event = '@@date PercentUserTime=@@PercentUserTime PercentSystemTime=@@PercentSystemTime PercentIdleTime=@@PercentIdleTime'

	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	event = event.replace('@@PercentUserTime', str(random.randint(0, 100)))
	event = event.replace('@@PercentSystemTime', str(random.randint(0, 100)))
	event = event.replace('@@PercentIdleTime', str(random.randint(0, 100)))

	print event
	
	count += 1
	randDelta += offset / iterations