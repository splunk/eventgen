from time import gmtime, strftime
import datetime
import os
import random
import re
import sys
import shutil
from gen import *

'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''

datatype = "cisco"
#
if os.environ.has_key("SPLUNK_HOME"):	
	sample_file_name, output_file_name, offset, spool_path_name  = InitDataGen(datatype)

	## sample input
	inFile = open(sample_file_name, 'r')
	## sample output
	outFile = open(output_file_name, 'w')


	## get the current date and time
	nowTime = datetime.datetime.now()

	for lines in inFile:
		## generate a number representing minutes offset
		randDelta = random.randrange(0,offset,1)
		
		## create deltaTime
		deltaTime = datetime.timedelta(seconds=randDelta)
		
		## compute time delta
		deltaTime = nowTime - deltaTime
		
		## substitute static timestamp with generated one
		line = re.sub('\d{4}\-\d{2}\-\d{2}\s+\d{2}\:\d{2}\:\d{2}', deltaTime.strftime('%Y-%m-%d %H:%M:%S'), lines)
		line = re.sub('\w{3}\s+\d{1,2}\s+\d+\s+\d{2}\:\d{2}\:\d{2}', deltaTime.strftime('%b %d %Y %H:%M:%S'), line)
		line = re.sub('\w{3}\s+\d{1,2}\s+\d{2}\:\d{2}\:\d{2}', deltaTime.strftime('%b %d %H:%M:%S'), line)
		
		## write line
		outFile.write(line)

	## close sample output
	outFile.close()
	## close sample input
	inFile.close()

	## move sample output to spool
	shutil.move(output_file_name,spool_path_name)