'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import hashlib
import random
import string

## sample event
## Feb 23 2010 14:03:33 app=selinux file_hash=a7ce7b65ed0fb221478e905fa1fc12cbe8614e8b selinux=disabled selinuxtype=targeted setlocaldefs=0

count = 0
iterations = 100
## 1440 represents 24 hour offset
offset = 1440

## get the current date and time
nowTime = datetime.datetime.now()

###### Simulate Disabled SELinux

randDelta = offset

## create deltaTime
deltaTime = datetime.timedelta(minutes=randDelta)
	
## compute time delta
deltaTime = nowTime - deltaTime

event = '@@date app=selinux file_hash=a7ce7b65ed0fb221478e905fa1fc12cbe8614e8b selinux=disabled selinuxtype=targeted setlocaldefs=0'
	
event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	
print event

iterations -= 1
randDelta = 0

###### Simulate Random Disk Utilization
while count < iterations:

	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime
	
	event = '@@date app=selinux file_hash=4e14506bc5073c3743c09d454407ecdd27974005  selinux=enforcing selinuxtype=targeted setlocaldefs=0'
	
	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))

	print event
		
	count += 1
	randDelta += offset / iterations