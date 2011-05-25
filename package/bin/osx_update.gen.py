'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 07 2010 14:36:38 total_updates=2
## Mar 07 2010 14:51:42 package="iLifeSupport902-9.0.4" is_recommended=true
## Mar 15 2010 19:29:36 package="Safari405SnowLeopard-4.0.5" is_recommended=true restart_required=true

count = 0
iterations = 50
## 1440 represents 24 hour offset
offset = 1440

## array of "package" values
packages = ['iLifeSupport902-9.0.4']

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = 0

###### Simulate Random CPU Utilization
while count < iterations:
	
	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	for x in range(0,len(packages)):
	
		event = '@@date package="@@package" is_recommended=true'
		
		event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
		event = event.replace('@@package', packages[x])

		print event
		
	event = '@@date total_updates=@@total_updates'
		
	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	event = event.replace('@@total_updates', str(len(packages)))
	
	print event
	
	count += 1
	randDelta += offset / iterations