'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 07 2010 18:59:51 machine_hardware_name="x86_64" machine_architecture_name="x86_64" os_release="2.6.21.7-2.ec2.v1.2.fc8xen" os_name="Linux" os_version="#1 SMP Fri Nov 20 17:48:28 EST 2009"

count = 0
iterations = 100
## 1440 represents 24 hour offset
offset = 1440

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = 0

###### Simulate Random CPU Utilization
while count < iterations:
	
	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	event = '@@date machine_hardware_name="i86pc" machine_architecture_name="i386" os_release="5.11" os_name="SunOS" os_version="snv_111b"'
	
	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))

	print event
	
	count += 1
	randDelta += offset / iterations