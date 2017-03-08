#!/usr/bin/env python
import csv
import re

# Actuals files generated with searches:
# Guest, instance values:
# index=vmware sourcetype=vmware:perf (moname=qa-centos-amd64-02) | bin _time span=20s | fillnull perfsubtype | dedup _time, meid, perftype, perfsubtype, instance | stats [| inputlookup VMFieldList | dedup perftype, instance, fields | eval fieldssplit=split(fields, "|") | mvexpand fieldssplit | dedup perftype, fieldssplit | table perftype, instance, fieldssplit | sort perftype, instance, fieldsplit | rename fieldssplit as search | fields search | eval search="avg("+$search$+") AS "+search | mvcombine delim=" " search | nomv search] by _time, moname | fields - moname, _time
# 
# Guest, aggregate values:
# index=vmware sourcetype=vmware:perf (moname=qa-centos-amd64-02) | bin _time span=20s | fillnull value="" perfsubtype, instance | search instance="" | dedup _time, meid, perftype, perfsubtype, instance | stats [| inputlookup VMFieldList | dedup perftype, instance, fields | eval fieldssplit=split(fields, "|") | mvexpand fieldssplit | dedup perftype, fieldssplit | table perftype, instance, fieldssplit | sort perftype, instance, fieldsplit | rename fieldssplit as search | fields search | eval search="avg("+$search$+") AS "+search | mvcombine delim=" " search | nomv search] by _time, moname | fields - moname, _time
# 
# Host, instance values:
# index=vmware sourcetype=vmware:perf (moname=esxi4104*) | bin _time span=20s | fillnull perfsubtype | dedup _time, meid, perftype, perfsubtype, instance | stats [| inputlookup VMFieldList | dedup perftype, instance, fields | eval fieldssplit=split(fields, "|") | mvexpand fieldssplit | dedup perftype, fieldssplit | table perftype, instance, fieldssplit | sort perftype, instance, fieldsplit | rename fieldssplit as search | fields search | eval search="avg("+$search$+") AS "+search | mvcombine delim=" " search | nomv search] by _time, moname | fields - moname, _time
# 
# Host, aggregate values:
# index=vmware sourcetype=vmware:perf (moname=esxi4104*) | bin _time span=20s | fillnull value="" perfsubtype, instance | search instance="" | dedup _time, meid, perftype, perfsubtype, instance | stats [| inputlookup VMFieldList | dedup perftype, instance, fields | eval fieldssplit=split(fields, "|") | mvexpand fieldssplit | dedup perftype, fieldssplit | table perftype, instance, fieldssplit | sort perftype, instance, fieldsplit | rename fieldssplit as search | fields search | eval search="avg("+$search$+") AS "+search | mvcombine delim=" " search | nomv search] by _time, moname | fields - moname, _time


# Perf file generated with search:
# index=vmware sourcetype=vmware:perf (moname=ross-datagen0044 OR moname=qasvwin7x64-HK1 OR moname=ANTIVIR01 OR moname=io-qa-splunk OR moname=esxi4103* OR moname=esxi4104*) | fillnull value="" perfsubtype, instance | dedup meid, perftype, perfsubtype, instance | fields _raw, index, host, source, sourcetype


# Make perf files split into 4 chunks
perfFH = open("../samples/vmware-perf.csv", "rU")
perflines = perfFH.readlines()

guestInstancePerfFH = open("../samples/vmware-perf-guest-instance.csv", "w")
guestAggregatePerfFH = open("../samples/vmware-perf-guest-aggregate.csv", "w")
hostInstancePerfFH = open("../samples/vmware-perf-host-instance.csv", "w")
hostAggregatePerfFH = open("../samples/vmware-perf-host-aggregate.csv", "w")

guest = ['ross-datagen0044', 'qasvwin7x64-HK1', 'ANTIVIR01', 'io-qa-splunk']
host = ['esxi4103', 'esxi4104']

[header], perflines = perflines[:1], perflines[1:]
guestInstancePerfFH.write(header)
guestAggregatePerfFH.write(header)
hostInstancePerfFH.write(header)
hostAggregatePerfFH.write(header)


for line in perflines:
    # Guest host
    if re.search('(?:' + '|'.join(guest) + ')', line):
        # Instance metrics
        if re.search('instance', line):
            guestInstancePerfFH.write(line)
        else:
            guestAggregatePerfFH.write(line)
    else:
        # Host metrics
        if re.search('instance', line):
            hostInstancePerfFH.write(line)
        else:
            hostAggregatePerfFH.write(line)
            

# Build config
baseconfig = """sampletype = csv
interval = 20
earliest = now
latest  = now
count = 0
randomizeEvents = false

outputMode = splunkstream
index=main
source=eventgen
sourcetype=eventgen

# Host/User/pass only necessary if running outside of splunk!
splunkHost = localhost
splunkUser = admin
splunkPass = changeme

token.0.token = \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC
token.0.replacementType = timestamp
token.0.replacement = %Y-%m-%d %H:%M:%S

"""

# variability = 0.25

guestInstanceActualsFH = open("../samples/vmware-actuals-guest-instance.csv", "rU")
guestAggregateActualsFH = open("../samples/vmware-actuals-guest-aggregate.csv", "rU")
hostInstanceActualsFH = open("../samples/vmware-actuals-host-instance.csv", "rU")
hostAggregateActualsFH = open("../samples/vmware-actuals-host-aggregate.csv", "rU")

out = ""

for x in ('guest', 'host'):
    
    for x2 in ('instance', 'aggregate'):
        out += '[vmware-perf-%s-%s.csv]\n' % (x, x2)
        out += baseconfig
        
        tokens = ""
        token = 1
        
        filename = '../samples/vmware-actuals-%s-%s.csv' % (x, x2)
        fh = open(filename, "rU")
        
        reader = csv.reader(fh)
        actualslist = [ ]
        for line in reader:
            actualslist.append(line)
        fields = actualslist[0]
        print fields
        actuals = actualslist[1]
        
        # tokens += "# Want to make all instance variables a different match so we can differentiate\n"
        # tokens += "token.1.token = (?:%s)=([0-9\.]+).*instance=\S+\n" % "|".join(fields)
        # tokens += "token.1.replacementType = static\n"
        # tokens += "token.1.replacement = #INSTANCE#\n\n"

        for i in range(0, len(fields)):
            if re.match("\d+\.\d+", actuals[i]):
                # if x2 == 'instance':
                #     tokens += "token.%s.token = %s=(#INSTANCE#)\n" % (token, fields[i])
                # elif x2 == 'aggregate':
                #     # tokens += "token.%s.token = ((?!instance).)*%s=([0-9\.]+)\n" % (token, fields[i])
                #     tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, fields[i])
                tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, fields[i])
                tokens += "token.%s.replacementType = mvfile\n" % (token)
                tokens += "token.%s.replacement = %s:%s\n\n" % (token, filename, (i+1))  
                token += 1
        out += tokens
            
          
outFH = open('../local/eventgen-standalone.conf.append', 'w')  
outFH.write(out)      
            # # Integer
            # match = re.match("(\d+)(\.[0]+|$)", fields[i])
            # if match:
            #     item = int(match.groups(0)[0])
            #     low = int(round(item * (1 - (variability/2)), 0))
            #     high = int(round(item * (1 + (variability/2)), 0))
            #     tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, guestFields[i])
            #     tokens += "token.%s.replacementType = random\n" % (token)
            #     tokens += "token.%s.replacement = integer[%s:%s]\n\n" % (token, low, high)
            #     token += 1
            # # Float
            # elif re.match("\d+\.\d+", guestActuals[i]):
            #     item = float(guestActuals[i])
            #     low = float(round(item * (1 - (variability/2)), 4))
            #     high = float(round(item * (1 + (variability/2)), 4))
            #     tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, guestFields[i])
            #     tokens += "token.%s.replacementType = random\n" % (token)
            #     tokens += "token.%s.replacement = float[%.4f:%.4f]\n\n" % (token, low, high)
            #     token += 1

# guestReader = csv.reader(guestActualsFH)
# guestList = [ ]
# for line in guestReader:
#     guestList.append(line)
# guestFields = guestList[0]
# guestActuals = guestList[1]
# 
# tokens = ""
# token = 1
# 
# for i in range(0, len(guestActuals)):
#     # Integer
#     match = re.match("(\d+)(\.[0]+|$)", guestActuals[i])
#     if match:
#         item = int(match.groups(0)[0])
#         low = int(round(item * (1 - (variability/2)), 0))
#         high = int(round(item * (1 + (variability/2)), 0))
#         tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, guestFields[i])
#         tokens += "token.%s.replacementType = random\n" % (token)
#         tokens += "token.%s.replacement = integer[%s:%s]\n\n" % (token, low, high)
#         token += 1
#     # Float
#     elif re.match("\d+\.\d+", guestActuals[i]):
#         item = float(guestActuals[i])
#         low = float(round(item * (1 - (variability/2)), 4))
#         high = float(round(item * (1 + (variability/2)), 4))
#         tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, guestFields[i])
#         tokens += "token.%s.replacementType = random\n" % (token)
#         tokens += "token.%s.replacement = float[%.4f:%.4f]\n\n" % (token, low, high)
#         token += 1
# 
# print tokens
# 
# hostReader = csv.reader(hostActualsFH)
# hostList = [ ]
# for line in hostReader:
#     hostList.append(line)
# 
# hostFields = hostList[0]
# hostActuals = hostList[1]
# 
# for i in range(0, len(hostActuals)):
#     # Integer
#     match = re.match("(\d+)(\.[0]+|$)", hostActuals[i])
#     if hostFields[i] not in guestFields[i]:
#         if match:
#             item = int(match.groups(0)[0])
#             low = int(round(item * (1 - (variability/2)), 0))
#             high = int(round(item * (1 + (variability/2)), 0))
#             tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, hostFields[i])
#             tokens += "token.%s.replacementType = random\n" % (token)
#             tokens += "token.%s.replacement = integer[%s:%s]\n\n" % (token, low, high)
#             token += 1
#         # Float
#         elif re.match("\d+\.\d+", hostActuals[i]):
#             item = float(hostActuals[i])
#             low = float(round(item * (1 - (variability/2)), 4))
#             high = float(round(item * (1 + (variability/2)), 4))
#             tokens += "token.%s.token = %s=([0-9\.]+)\n" % (token, hostFields[i])
#             tokens += "token.%s.replacementType = random\n" % (token)
#             tokens += "token.%s.replacement = float[%.4f:%.4f]\n\n" % (token, low, high)
#             token += 1
#         
# print tokens