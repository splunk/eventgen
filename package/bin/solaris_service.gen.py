'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 05 2010 19:35:06 app="/system/zones:default" StartMode="Auto" StartName="svc" State="Running"
## Mar 05 2010 19:35:06 app="/milestone/multi-user-server:default" StartMode="Auto" StartName="svc" State="Running"
## Mar 05 2010 19:35:06 app="/application/graphical-login/gdm:default" StartMode="Auto" StartName="svc" State="Running"
## Mar 05 2010 19:35:06 app="/system/filesystem/rmvolmgr:default" StartMode="Auto" StartName="svc" State="Running"
## Mar 05 2010 19:35:06 app="/system/hal:default" StartMode="Auto" StartName="svc" State="Running"

count = 0
iterations = 20
## 1440 represents 24 hour offset
offset = 1440

## array of events
events = ['@@date app="/system/zones:default" StartMode="Disabled" StartName="svc" State="Running"',
	'@@date app="/network/ntp:default" StartMode="Auto" StartName="svc" State="Running"',
	'@@date app="/application/graphical-login/gdm:default" StartMode="Auto" StartName="svc" State="Stopped"',
	'@@date app="/system/filesystem/rmvolmgr:default" StartMode="Auto" StartName="svc" State="Running"',
	'@@date app="/system/hal:default" StartMode="Auto" StartName="svc" State="Running"']

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
