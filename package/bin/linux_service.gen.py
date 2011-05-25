'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''
from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 08 2010 12:59:34 app=yum-updatesd runlevel0=off runlevel1=off runlevel2=off runlevel3=off runlevel4=off runlevel5=off runlevel6=off
## Mar 08 2010 12:59:34 app=sshd runlevel0=off runlevel1=off runlevel2=on runlevel3=on runlevel4=on runlevel5=on runlevel6=off

count = 0
iterations = 20
## 1440 represents 24 hour offset
offset = 1440

## array of events
events = ['@@date app=yum-updatesd runlevel0=off runlevel1=off runlevel2=off runlevel3=off runlevel4=off runlevel5=off runlevel6=off',
		'@@date app=ypbind runlevel0=off runlevel1=off runlevel2=off runlevel3=off runlevel4=off runlevel5=off runlevel6=off',
		'@@date app=ntpd runlevel0=off runlevel1=off runlevel2=off runlevel3=off runlevel4=off runlevel5=off runlevel6=off',
		'@@date app=sshd runlevel0=off runlevel1=off runlevel2=on runlevel3=on runlevel4=on runlevel5=on runlevel6=off',
		'@@date app=smartd runlevel0=on runlevel1=off runlevel2=off runlevel3=off runlevel4=off runlevel5=off runlevel6=off',]

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
