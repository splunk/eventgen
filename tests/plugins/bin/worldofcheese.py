from __future__ import division
from generatorplugin import GeneratorPlugin
import os
import logging
import datetime, time
import itertools
from collections import deque
from eventgenoutput import Output
import csv
import pprint
import json
import random


class WindbagGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        # Logger already setup by config, just get an instance
        logger = logging.getLogger('eventgen')
        from eventgenconfig import EventgenAdapter
        adapter = EventgenAdapter(logger, {'module': 'WindbagGenerator', 'sample': sample.name})
        globals()['logger'] = adapter

        from eventgenconfig import Config
        globals()['c'] = Config()

        # Pull customers into a dictionary
        fh = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'samples', 'customer_master.sample'), 'r')
        # fh = open('../samples/customer_master.sample', 'r')
        self.customers = [ ]
        csvReader = csv.DictReader(fh)
        for line in csvReader:
            newline = dict((k, line[k]) for k in ('Address', 'Age', 'Sex', 'accountNumber', 'customerCity', 'customerMDN', 'customerState', 'customerZip', 'firstName', 'lastName'))
            newline['address'] = newline['Address']
            del newline['Address']
            newline['age'] = newline['Age']
            del newline['Age']
            newline['sex'] = newline['Sex']
            del newline['Sex']
            newline['city'] = newline['customerCity']
            del newline['customerCity']
            newline['phone'] = newline['customerMDN']
            del newline['customerMDN']
            newline['state'] = newline['customerState']
            del newline['customerState']
            newline['zip'] = newline['customerZip']
            del newline['customerZip']
            self.customers.append(newline)

        # Bring items into a dictionary
        fh = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'samples', 'items.sample'), 'r')
        self.items = [ ]
        csvReader = csv.reader(fh)
        for line in csvReader:
            self.items.append({ 'category': line[0], 'itemid': line[1], 'description': line[2], 'price': float(line[3]) })

        self.transType = [ 'purchase', 'purchase', 'purchase', 'purchase', 'purchase', 'purchase', 'sale' ]
        self.characterType = [ 'Milk Maid', 'Masked Mouse', 'Curd Cobbler', 'Whey Warrior', 'Fermented Friar' ]
        self.regions = ['Gorgonzolia', 'Camemberalot', 'Jarlsberg', 'Swiss Alps', 'Limburgerland' ]
        self.servers = [ ]
        for a in ['ace', 'bubbles', 'cupcake', 'dash']:
            for b in xrange(0, random.randint(1, 12)):
                self.servers.append('%s.%s.woc.com' % (a, b))

        self.typeRate = { 'purchase': 1.0, 'sale': 0.2 }
        self.maxItems = 12
        self.tps = 5.0


        self.customerslen = len(self.customers)
        self.itemslen = len(self.items)
        self.transtypelen = len(self.transType)
        self.charactertypelen = len(self.characterType)
        self.serverslen = len(self.servers)
        self.regionslen = len(self.regions)

    def gen(self, count, earliest, latest, samplename=None):
        rows = [ ]
        for i in xrange(count):
            order = { }
            order['timestamp'] = datetime.datetime.strftime(latest, "%Y-%m-%dT%H:%M:%S")
            order['customer'] = self.customers[random.randint(0, self.customerslen-1)]
            order['charactertype'] = self.characterType[random.randint(0, self.charactertypelen-1)]
            order['type'] = self.transType[random.randint(0, self.transtypelen-1)]
            numitems = random.randint(0, self.maxItems)
            order['items'] = [ ]
            for x in xrange(0, numitems):
                order['items'].append(dict((k, v if k != 'price' else v * self.typeRate[order['type']]) for k,v in self.items[random.randint(0, self.itemslen-1)].items()))
            total = 0
            for item in order['items']:
                total += item['price']
            order['total'] = total
            order['servername'] = self.servers[random.randint(0, self.serverslen-1)]
            order['region'] = self.regions[random.randint(0, self.regionslen-1)]
            rows.append({ '_raw': json.dumps(order),
                            'index': 'main',
                            'host': order['servername'],
                            'source': 'order',
                            'sourcetype': 'order',
                            '_time': time.mktime(latest.timetuple()) })

        self._out.bulksend(rows)
        return 0


def load():
    return WindbagGenerator