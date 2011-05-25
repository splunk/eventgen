'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 05 2010 16:49:53 filesystem="/dev/dsk/c8t0d0s2" TotalMegabytes=677 UsedMegabytes=677 FreeMegabytes=0 PercentFreeSpace=0 mount="/media/OpenSolaris"

count = 0
iterations = 100
## 1440 represents 24 hour offset
offset = 1440

## array of "mount" values
filesystems = ['/dev/sda1','devfs','swap']
mounts = ['/','/dev','/tmp']

## get the current date and time
nowTime = datetime.datetime.now()

## generate a number representing minutes offset
## 0->1440 represents up to a 24 hour offset
randDelta = random.randrange(0,offset,1)
	
## create deltaTime
deltaTime = datetime.timedelta(minutes=randDelta)
	
## compute time delta
deltaTime = nowTime - deltaTime

###### Simulate 100 % Disk Utilization ######
event = '@@date filesystem="@@filesystem" TotalMegabytes=@@TotalMegabytes UsedMegabytes=@@UsedMegabytes FreeMegabytes=@@FreeMegabytes PercentFreeSpace=@@PercentFreeSpace mount="@@mount"'

event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
event = event.replace('@@filesystem', 'fd')
event = event.replace('@@TotalMegabytes', str(102400))
event = event.replace('@@UsedMegabytes', str(102400))
event = event.replace('@@FreeMegabytes', str(0))
event = event.replace('@@PercentFreeSpace', str(0))
event = event.replace('@@mount', '/dev/fd')

print event
	
iterations -= 1
randDelta = 0

###### Simulate Random Disk Utilization
while count < iterations:

	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	event = '@@date filesystem="@@filesystem" TotalMegabytes=@@TotalMegabytes UsedMegabytes=@@UsedMegabytes FreeMegabytes=@@FreeMegabytes PercentFreeSpace=@@PercentFreeSpace mount="@@mount"'

	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	
	randMount = random.randint(0,len(mounts)-1)
	event = event.replace('@@filesystem', filesystems[randMount])
	
	totalmegabytes = 102400
	freemegabytes = random.randint(0,102400)
	usedmegabytes = totalmegabytes-freemegabytes
	percentfreespace = 100 * freemegabytes / totalmegabytes	
	event = event.replace('@@TotalMegabytes', str(totalmegabytes))
	event = event.replace('@@UsedMegabytes', str(usedmegabytes))
	event = event.replace('@@FreeMegabytes', str(freemegabytes))
	event = event.replace('@@PercentFreeSpace', str(percentfreespace))
	
	event = event.replace('@@mount', mounts[randMount])

	print event
	
	count += 1
	randDelta += offset / iterations
