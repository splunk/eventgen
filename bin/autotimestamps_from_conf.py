"""
Read an eventgen.conf and generate a JSON list of the unique timestamp tuples 
you find in that file for easy adding to the default eventgen.conf file.
"""
from ConfigParser import ConfigParser
import sys
import re
import json

tokenrexes = { }
tokens = [ ]

t = r'[["\\d{1,2}\\/\\w{3}\\/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}:\\d{1,3}", "%d/%b/%Y %H:%M:%S:%f"], ["\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}", "%Y-%m-%dT%H:%M:%S.%f"], ["\\d{1,2}/\\w{3}/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}:\\d{1,3}", "%d/%b/%Y %H:%M:%S:%f"], ["\\d{1,2}/\\d{2}/\\d{2}\\s\\d{1,2}:\\d{2}:\\d{2}", "%m/%d/%y %H:%M:%S"], ["\\d{2}-\\d{2}-\\d{4} \\d{2}:\\d{2}:\\d{2}", "%m-%d-%Y %H:%M:%S"], ["\\w{3} \\w{3} +\\d{1,2} \\d{2}:\\d{2}:\\d{2}", "%a %b %d %H:%M:%S"], ["\\w{3} \\w{3} \\d{2} \\d{4} \\d{2}:\\d{2}:\\d{2}", "%a %b %d %Y %H:%M:%S"], ["^(\\w{3}\\s+\\d{1,2}\\s\\d{2}:\\d{2}:\\d{2})", "%b %d %H:%M:%S"], ["(\\w{3}\\s+\\d{1,2}\\s\\d{1,2}:\\d{1,2}:\\d{1,2})", "%b %d %H:%M:%S"], ["(\\w{3}\\s\\d{1,2}\\s\\d{1,4}\\s\\d{1,2}:\\d{1,2}:\\d{1,2})", "%b %d %Y %H:%M:%S"], ["\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}\\.\\d{3}", "%Y-%m-%d %H:%M:%S.%f"], ["\\,\\d{2}\\/\\d{2}\\/\\d{2,4}\\s+\\d{2}:\\d{2}:\\d{2}\\s+[AaPp][Mm]\\,", ",%m/%d/%Y %I:%M:%S %p,"], ["^\\w{3}\\s+\\d{2}\\s+\\d{2}:\\d{2}:\\d{2}", "%b %d %H:%M:%S"], ["\\d{2}/\\d{2}/\\d{4} \\d{2}:\\d{2}:\\d{2}", "%m/%d/%Y %H:%M:%S"], ["^\\d{2}\\/\\d{2}\\/\\d{2,4}\\s+\\d{2}:\\d{2}:\\d{2}\\s+[AaPp][Mm]", "%m/%d/%Y %I:%M:%S %p"], ["\\d{2}\\/\\d{2}\\/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}", "%m-%d-%Y %H:%M:%S"], ["\\\"timestamp\\\":\\s\\\"(\\d+)", "%s"], ["\\d{2}\\/\\w+\\/\\d{4}\\s\\d{2}:\\d{2}:\\d{2}:\\d{3}", "%d-%b-%Y %H:%M:%S:%f"], ["(\\d{10})", "%s"], ["\\\"created\\\":\\s(\\d+)", "%s"], ["\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}", "%Y-%m-%d %H:%M:%S"], ["\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}", "%Y-%m-%d %H:%M:%S"]]'
_tokens = json.loads(t)
for i in _tokens:
    tokenrexes[i[0]] = True

c = ConfigParser()
c.optionxform = str
c.read([sys.argv[1]])

for s in c.sections():
    group = -1
    for i in c.items(s):
        if i[0].find('token.') > -1:
            results = re.match('token\.(\d+)\.(\w+)', i[0])
            if results != None:
                groups = results.groups()
                newgroup = groups[0]
                if newgroup != group:
                    group = newgroup
                    newtoken = [ None, None ]
                    timestamp = False
                    skipnext = False
                if groups[1] == "token":
                    if i[1] not in tokenrexes:
                        newtoken[0] = i[1]
                        tokenrexes[i[1]] = True
                        skipnext = False
                    else:
                        skipnext = True
                elif groups[1] == "replacementType":
                    if i[1] == "timestamp":
                        timestamp = True
                elif groups[1] == "replacement":
                    newtoken[1] = i[1]

                if newtoken[0] != None and newtoken[1] != None \
                        and not skipnext and timestamp:
                    print "Adding Token: %s" % newtoken
                    tokens.append(newtoken)

print(json.dumps(tokens))