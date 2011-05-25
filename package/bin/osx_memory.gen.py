'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 06 2010 14:31:26 WiredMBytes=261 ActiveMBytes=552 InactiveMBytes=394 UsedBytes=1265631232 AvailableMBytes=841 TotalMBytes=2048

count = 0
iterations = 100
## 1440 represents 24 hour offset
offset = 1440

## get the current date and time
nowTime = datetime.datetime.now()

## generate a number representing minutes offset
## 0->1440 represents up to a 24 hour offset
randDelta = random.randrange(0,offset,1)
	
## create deltaTime
deltaTime = datetime.timedelta(minutes=randDelta)
	
## compute time delta
deltaTime = nowTime - deltaTime

###### Simulate 100 % Memory Utilization ######
event = '@@date WiredMBytes=@@WiredMBytes ActiveMBytes=@@ActiveMBytes InactiveMBytes=@@InactiveMBytes UsedBytes=@@UsedBytes AvailableMBytes=@@AvailableMBytes TotalMBytes=@@TotalMBytes'

event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
event = event.replace('@@WiredMBytes', str(782))
event = event.replace('@@ActiveMBytes', str(6162))
event = event.replace('@@InactiveMBytes', str(1248))
event = event.replace('@@UsedBytes', str(8589934592))
event = event.replace('@@AvailableMBytes', str(0))
event = event.replace('@@TotalMBytes', str(8192))

print event
	
iterations -= 1
randDelta = 0

###### Simulate Random Memory Utilization
while count < iterations:

	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	event = '@@date WiredMBytes=@@WiredMBytes ActiveMBytes=@@ActiveMBytes InactiveMBytes=@@InactiveMBytes UsedBytes=@@UsedBytes AvailableMBytes=@@AvailableMBytes TotalMBytes=@@TotalMBytes'
	
	totalbytes = 8589934592
	committedbytes = totalbytes * random.randint(0,100) / 100
	availablembytes = (totalbytes - committedbytes) / 1048576
	wiredmbytes = committedbytes / (1048576 * 3)

	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	event = event.replace('@@WiredMBytes', str(wiredmbytes))
	event = event.replace('@@ActiveMBytes', str(wiredmbytes))
	event = event.replace('@@InactiveMBytes', str(wiredmbytes))
	event = event.replace('@@UsedBytes', str(committedbytes))
	event = event.replace('@@AvailableMBytes', str(availablembytes))
	event = event.replace('@@TotalMBytes', str(totalbytes/1048576))
	print event
	
	count += 1
	randDelta += offset / iterations
