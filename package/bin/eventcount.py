# Assumes events are one per line

from __future__ import division
from collections import deque
import datetime
import sys
import threading
import time


class Stats(threading.Thread):

	SLEEPTIME = 5
	AVERAGESAMPLESIZE = int( round((60*1)/SLEEPTIME, 0) ) # 1 Minutes of Data
	metrics = { 
		'count': 0,
		'bytes': 0,
		'kbsecavg': deque(maxlen=AVERAGESAMPLESIZE),
		'gbdayavg': deque(maxlen=AVERAGESAMPLESIZE)
	}

	def __init__(self):
		threading.Thread.__init__(self)

	def run(self):
		while True:
			kbsec = self.metrics['bytes']/self.SLEEPTIME/1024
			gbday = kbsec * 60 * 60 * 24 /1024 / 1024
			self.metrics['kbsecavg'].append( kbsec )
			self.metrics['gbdayavg'].append( gbday )
			kbsecavg = sum(list(self.metrics['kbsecavg'])) / len(self.metrics['kbsecavg'])
			gbdayavg = sum(list(self.metrics['gbdayavg'])) / len(self.metrics['gbdayavg'])
			print "%s Events/Sec: %s Kilobytes/Sec: %1f GB/Day: %1f" % \
						(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'),
						self.metrics['count'] / self.SLEEPTIME, kbsec, gbday )
			self.metrics['count'] = 0
			self.metrics['bytes'] = 0
			time.sleep(self.SLEEPTIME)




t = Stats()
t.daemon = True
t.start()


while True:
	# Bad Method
	# line = sys.stdin.readline()
	# t.metrics['count'] += 1
	# t.metrics['bytes'] += len(line)

	# Good Method
	stuff = sys.stdin.read(65536)
	t.metrics['count'] += stuff.count('\n')+1
	t.metrics['bytes'] += 65536