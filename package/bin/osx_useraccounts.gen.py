'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import random

## sample event
## Mar 08 2010 17:59:27 user=ntp password=* user_id=38 user_group_id=38 home=/etc/ntp shell=/usr/bin/false
## Mar 08 2010 17:59:27 user=sshd password=* user_id=74 user_group_id=74 home=/var/empty/sshd shell=/usr/bin/false
## Mar 08 2010 17:59:27 user=bin password=* user_id=1 user_group_id=1 home=/bin shell=/usr/bin/false
## Mar 08 2010 17:59:27 user=root password=* user_id=0 user_group_id=0 home=/root shell=/bin/sh
## Mar 08 2010 17:59:27 file_hash=fc1079550739ce0b781f58bad556a9816bae7127

count = 0
iterations = 20
## 1440 represents 24 hour offset
offset = 1440

## array of events
events = ['@@date user=ntp password=changeme! user_id=38 user_group_id=38 home=/etc/ntp shell=/bin/sh',
		'@@date user=sshd password=* user_id=74 user_group_id=74 home=/var/empty/sshd shell=/usr/bin/false',
		'@@date user=bin password=* user_id=1 user_group_id=1 home=/bin shell=/usr/bin/false',
		'@@date user=root password=* user_id=0 user_group_id=0 home=/root shell=/bin/sh',
		'@@date file_hash=fc1079550739ce0b781f58bad556a9816bae7127']

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = 0

###### Simulate Random User Accounts
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