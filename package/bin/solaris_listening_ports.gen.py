'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

from time import gmtime, strftime
import datetime
import hashlib
import random
import string

## sample event
## Mar 05 2010 19:34:56 dest_dns=* dest_port=59641 transport=TCP ip_version=6

count = 0
iterations = 20
## 1440 represents 24 hour offset
offset = 1440

## array of "port" values
protocols = ['TCP','TCP','TCP','UDP']
ports = ['22','443','123','631']

## get the current date and time
nowTime = datetime.datetime.now()

randDelta = 0

###### Simulate Random Disk Utilization
while count < iterations:

	## create deltaTime
	deltaTime = datetime.timedelta(minutes=randDelta)
	
	## compute time delta
	deltaTime = nowTime - deltaTime
	
	tempPorts = []
	
	for x in range(0,len(ports)):
		tempPort = ''
		event = '@@date dest_dns=* dest_port=@@src_port transport=@@transport ip_version=4'

		event = event.replace('@@date', deltaTime.strftime('%b %d %Y %H:%M:%S'))
		tempPort += '*'
		event = event.replace('@@src_port', ports[x])
		tempPort += ports[x]
		event = event.replace('@@transport', protocols[x])
		tempPort += protocols[x]
	
		print event
		tempPorts.append(tempPort)
		
	count += 1
	randDelta += offset / iterations	
		
	if tempPorts:
		netstat = string.join(tempPorts, '')
		netstat_hash = hashlib.sha1(netstat).hexdigest()
	
		print deltaTime.strftime('%b %d %Y %H:%M:%S') + ' file_hash=' + netstat_hash
