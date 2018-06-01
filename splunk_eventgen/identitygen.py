import csv
import os
import random
import time
from string import ascii_uppercase

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))

class identityGenerator(object):
	'''
	Generates csv file with the following values
	'''
	CATEGORIES = ["cardholder","cardholder|pci","officer|pci","intern","default","default","default","default","sox","pci","officer","","","","","","","","","",""]
	LOCATION = [["San Francisco","USA","americas","37.3382N","121.6663W"],["San Jose","USA","americas","37.78N","122.41W"]]
	EMAIL_DOMAIN = "@splunk.com"
	PRIORITIES = ["low","low","low","low","low","low","medium","medium","high","critical"]
	def __init__(self):
		try:
			self.last = [i.split()[0] for i in open("%s/samples/dist.all.last"%BASE_PATH,"rb").readlines()]
		except IOError as e:
			self.last = [(''.join(random.choice(ascii_uppercase) for i in xrange(random.randint(4,12)))) for i in xrange(100)]
		try:
			self.female_first = [i.split()[0] for i in open("%s/samples/dist.female.first"%BASE_PATH,"rb").readlines()]
		except IOError as e:
			self.female_first = [(''.join(random.choice(ascii_uppercase) for i in xrange(random.randint(4,12)))) for i in xrange(100)]
		try:
			self.male_first = [i.split()[0] for i in open("%s/samples/dist.male.first"%BASE_PATH,"rb").readlines()]
		except IOError as e:
			self.male_first = [(''.join(random.choice(ascii_uppercase) for i in xrange(random.randint(4,12)))) for i in xrange(100)]

	def generate(self, count):
		self.identities = []
		usernames = dict()
		len_last = len(self.last)
		len_male_first = len(self.male_first)
		len_female_first = len(self.female_first)
		prev_time = time.time()
		for i in xrange(count):
			gender = random.choice(["m","f"])
			last_name = self.last[int(random.triangular(0,len_last,0))]
			if gender == "m":
				first_name = self.male_first[int(random.triangular(0,len_male_first,0))]
			else:
				first_name = self.female_first[int(random.triangular(0,len_female_first,0))]
			category = random.choice(self.CATEGORIES)
			priority = random.choice(self.PRIORITIES)
			startDate = time.strftime("%m/%d/%Y", time.localtime(time.time()-random.randint(2592000,77760000))) # random start date between 30 days ago to 900 days ago
			(work_city, work_country, bunit, work_lat, work_long)= random.choice(self.LOCATION)
			identity = {"first_name":first_name,"last_name":last_name,"work_city":work_city,"work_country":work_country,"bunit":bunit,"work_lat":work_lat,"work_long":work_long,"priority":priority,"category":category,"startDate":startDate}
			base_username = identity["first_name"] + identity["last_name"]
			t = time.time()
			if base_username in usernames:
				tmp_val = 0
				while username + str(tmp_val) in usernames[base_username]:
					tmp_val += 1
				username = base_username + str(tmp_val)
				usernames[base_username].append(username)
			else:
				username = base_username
				usernames[username] = list()
			identity["username"] = username
			identity["ip"] = self.int2InternalIP(i)
			self.identities.append(identity)
			

	def int2InternalIP(self,i):
		return "10.%s.%s.%s" % (str(int(i/65536)), str(int(i/256)%256), str(i%256))

	def setLocations(self,new_locations):
		for location in new_locations:
			if len(location)!=5:
				raise ValueError
		self.CATEGORIES = new_locations

	def setCategories(self,new_categories):
		self.CATEGORIES = new_categories

	def setEmail(self,new_email):
		if "@" in new_email:
			self.EMAIL_DOMAIN = new_email
		else:
			raise ValueError

	def getFile(self,count=0,filename="../default",fields=["username","first_name","last_name"],fieldnames=["username","first_name","last_name"]): 
		'Returns a rest endpoint to download a csv file'
		if count == 0:
			with open(filename,"wb") as lookupFile:
				file = csv.writer(lookupFile)
				file.writerow(fieldnames)
				for identity in self.identities:
					row = []
					for field in fields:
						try:
							row.append(identity[field])
						except KeyError:
							row.append("")
					file.writerow(row)
		else:
			with open(filename,"wb") as lookupFile:
				file = csv.writer(lookupFile)
				file.writerow(fieldnames)
				for i in xrange(min(count+1,len(identities))): # + 1 to account for the header
					row = []
					identity = identities[i]
					for field in fields:
						try:
							row.append(identity[field])
						except KeyError:
							row.append("")
					file.writerow(row)
		return open(filename,"rb")

if __name__ == "__main__":
	identityGenerator = identityGenerator()
	identityGenerator.generate(300000)
	identityGenerator.getFile(filename="identities.csv",
		fields=["username","prefix","username","first_name","last_name","suffix","email","phone","phone2","managedBy","priority","bunit","category","watchlist","startDate","endDate","work_city","work_country","work_lat","work_long"],
		fieldnames = ["identity","prefix","nick","first","last","suffix","email","phone","phone2","managedBy","priority","bunit","category","watchlist","startDate","endDate","work_city","work_country","work_lat","work_long"])