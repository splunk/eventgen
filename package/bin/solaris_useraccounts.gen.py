'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 05 2010 19:35:01 user=hazekamp password=x user_id=101 user_group_id=10 home=/export/home/hazekamp shell=/bin/bash
## Mar 05 2010 19:35:01 user=nobody4 password=x user_id=65534 user_group_id=65534 home=/ shell=
## Mar 05 2010 19:35:01 user=noaccess password=x user_id=60002 user_group_id=60002 home=/ shell=
## Mar 05 2010 19:35:01 user=nobody password=x user_id=60001 user_group_id=60001 home=/ shell=
## Mar 08 2010 17:59:27 file_hash=cc1b0148b7ab9021b7f94b7041e9646efcb60884

count = 0
iterations = 20
## 1440 represents 24 hour offset
offset = 1440

## array of events
events = ['@@date user=hazekamp password=x user_id=101 user_group_id=10 home=/export/home/hazekamp shell=/bin/bash',
		'@@date user=nobody4 password=x user_id=65534 user_group_id=65534 home=/ shell=',
		'@@date user=noaccess password=x user_id=60002 user_group_id=60002 home=/ shell=',
		'@@date user=nobody password=x user_id=60001 user_group_id=60001 home=/ shell=',
		'@@date file_hash=cc1b0148b7ab9021b7f94b7041e9646efcb60884']

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = 0

###### Simulate Random Users
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
