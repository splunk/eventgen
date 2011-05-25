import os
import re
import sys

'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''
	
# This function parses the inputs file and looks for a stanza
## that matches the name of this script. Upon finding the stanza it looks for 
## matching settings
def GetRunInterval(target_name,config_file_name,default_interval):
	interval = default_interval
	in_Stanza = False
	if os.path.exists(config_file_name):
		configfile = open(config_file_name,'r')
		for line in configfile:
			if in_Stanza:
				if line.startswith("["):
					in_Stanza = False
				else:
					if line.lower().find("interval") > -1:
							foo,interval = line.split("=")
							interval = int(interval)
			if line.find(target_name) > -1:
				in_Stanza = True
	return interval
	
def InitDataGen(sourcetype):
	if os.environ.has_key("SPLUNK_HOME"):

		script_name = sys.argv[0].lower()
		
		
		if os.environ["SPLUNK_HOME"].find('\\') == -1:
			default_input_file_name = os.environ["SPLUNK_HOME"] + '/etc/apps/SA-Eventgen/default/inputs.conf'
			local_input_file_name = os.environ["SPLUNK_HOME"] + '/etc/apps/SA-Eventgen/local/inputs.conf'
			sample_file_name = os.environ["SPLUNK_HOME"] + '/etc/apps/SA-Eventgen/samples/' + sourcetype + '/' + sourcetype + '.sample'
			output_file_name = os.environ["SPLUNK_HOME"] + '/etc/apps/SA-Eventgen/samples/' + sourcetype + '/' + 'sample.' + sourcetype
			spool_path_name = os.environ["SPLUNK_HOME"] + '/var/spool/splunk'
		else:
			default_input_file_name = os.environ["SPLUNK_HOME"] + '\\etc\\apps\SA-Eventgen\\default\\inputs.conf'
			local_input_file_name = os.environ["SPLUNK_HOME"] + '\\etc\\apps\\SA-Eventgen\\local\\inputs.conf'
			sample_file_name = os.environ["SPLUNK_HOME"] + '\\etc\\apps\\SA-Eventgen\\samples\\' + sourcetype + '\\' + sourcetype + '.sample'
			output_file_name = os.environ["SPLUNK_HOME"] + '\\etc\\apps\\SA-Eventgen\\samples\\' + sourcetype + '\\' + 'sample.' + sourcetype
			spool_path_name = os.environ["SPLUNK_HOME"] + '\\var\\spool\\splunk'
		
			## 1440 represents 24 hour offset, and is the default
		offset = GetRunInterval(script_name,default_input_file_name,86400)
		## default value should be loaded, now checks for a local
		offset = GetRunInterval(script_name,local_input_file_name,offset)
		
		return sample_file_name, output_file_name, offset, spool_path_name
		
	
