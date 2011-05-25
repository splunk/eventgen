'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 05 2010 23:01:30 user=root pid=84902 PercentProcessorTime=0.0 PercentMemory=0.1 vsz=600996 rss=1072 tty=s000 stat=Ss start=16Feb10 time=0:00.24 app="login -pf markmorow" UsedBytes=2146435

count = 0
iterations = 20
## 1440 represents 24 hour offset
offset = 1440

## array of "app" values
apps = ['crond','kjournald','console-kit-daemon','/usr/bin/sshd','xenbus']

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = 0

###### Simulate Random process data
while count < iterations:

	randStart = random.randrange(0,offset,1)
	
	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	deltaStart = datetime.timedelta(minutes=randStart)
	
	## compute time delta
	deltaTime = nowTime - deltaTime
	deltaStart = deltaTime - deltaStart

	for x in range(0,len(apps)):
	
		event = '@@date user=root pid=@@pid PercentProcessorTime=@@PercentProcessorTime PercentMemory=@@PercentMemory vsz=@@vsz rss=@@rss tty=? stat=Ss start=@@start time=@@time app=@@app UsedBytes=@@UsedBytes'
		
		event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
		event = event.replace('@@pid', str(random.randint(0,65535)))
		event = event.replace('@@PercentProcessorTime', str(random.randint(0,100)))

		totalbytes = 8589934592
		percentmemory = random.randint(0,100)
		usedbytes = totalbytes * percentmemory / 100
		
		event = event.replace('@@PercentMemory', str(percentmemory))
		
		event = event.replace('@@vsz', str(random.randint(0,999999)))
		event = event.replace('@@rss', str(random.randint(0,9999)))
		event = event.replace('@@start', deltaTime.strftime('%d%B%y'))
		event = event.replace('@@time', deltaStart.strftime('%H:%M'))
		event = event.replace('@@app', apps[x])
		event = event.replace('@@UsedBytes', str(usedbytes))

		print event
	
	count += 1
	randDelta += offset / iterations