'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 05 2010 20:24:59 TotalMBytes=768 UsedBytes=778043392 AvailableMBytes=26 TotalSwapMBytes=512 UsedSwapBytes=29360128 AvailableSwapMBytes=484

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
event = '@@date TotalMBytes=@@TotalMBytes UsedBytes=@@UsedBytes AvailableMBytes=@@AvailableMBytes TotalSwapMBytes=@@TotalSwapMBytes UsedSwapBytes=@@UsedSwapBytes AvailableSwapMBytes=@@AvailableSwapMBytes'

event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
event = event.replace('@@TotalMBytes', str(8192))
event = event.replace('@@UsedBytes', str(8589934592))
event = event.replace('@@AvailableMBytes', str(0))
event = event.replace('@@TotalSwapMBytes', str(4096))
event = event.replace('@@UsedSwapBytes', str(4096))
event = event.replace('@@AvailableSwapMBytes', str(0))

print event
	
iterations -= 1
randDelta = 0

###### Simulate Random Memory Utilization
while count < iterations:

	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime

	event = '@@date TotalMBytes=@@TotalMBytes UsedBytes=@@UsedBytes AvailableMBytes=@@AvailableMBytes TotalSwapMBytes=@@TotalSwapMBytes UsedSwapBytes=@@UsedSwapBytes AvailableSwapMBytes=@@AvailableSwapMBytes'
	
	totalbytes = 8589934592
	committedbytes = totalbytes * random.randint(0,100) / 100
	availablembytes = (totalbytes - committedbytes) / 1048576

	totalswapbytes = 4294967296
	committedswapbytes = totalswapbytes * random.randint(0,100) / 100
	availableswapmbytes = (totalswapbytes - committedswapbytes) / 1048576

	event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
	event = event.replace('@@TotalMBytes', str(totalbytes/1048576))
	event = event.replace('@@UsedBytes', str(committedbytes))
	event = event.replace('@@AvailableMBytes', str(availablembytes))
	event = event.replace('@@TotalSwapMBytes', str(totalswapbytes/1048576))
	event = event.replace('@@UsedSwapBytes', str(committedswapbytes))
	event = event.replace('@@AvailableSwapMBytes', str(availableswapmbytes))

	print event
	
	count += 1
	randDelta += offset / iterations
