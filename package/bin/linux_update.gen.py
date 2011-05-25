'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 07 2010 14:36:38 total_updates=22 base=0 updates=22 addons=0 extras=0
## Mar 07 2010 14:36:38 package="xulrunner.i386" package_type=updates

count = 0
iterations = 20
## 1440 represents 24 hour offset
offset = 1440

## array of "package" values
packages = ['xulrunner.i386','sudo.i386','openssh-server.i386','openssh-clients.i386']

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
	
		event = '@@date package="@@package" package_type=updates'
		
		event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
		event = event.replace('@@package', packages[x])

		print event
		
	event = '@@date total_updates=@@total_updates base=0 updates=@@updates addons=0 extras=0'
		
	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	event = event.replace('@@total_updates', str(len(packages)))
	event = event.replace('@@updates', str(len(packages)))
	
	print event
	
	count += 1
	randDelta += offset / iterations