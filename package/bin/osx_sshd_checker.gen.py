'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 07 2010 22:59:44 app=ssh sshd_protocol=2 file_hash=0e5c9810698decf5f18714f4690a43a813d19962

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

	event = '@@date app=ssh sshd_protocol=1 file_hash=0e5c9810698decf5f18714f4690a43a813d19962'
	
	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))

	print event
	
	count += 1
	randDelta += offset / iterations