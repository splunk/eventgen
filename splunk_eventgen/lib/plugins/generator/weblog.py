from __future__ import division
from generatorplugin import GeneratorPlugin
import time
import random


class WeblogGenerator(GeneratorPlugin):
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

        f = open('tests/perf/weblog/external_ips.sample')
        self.external_ips = [x.strip() for x in f.readlines()]
        self.external_ips_len = len(self.external_ips)
        f.close()

        f = open('tests/perf/weblog/webhosts.sample')
        self.webhosts = [x.strip() for x in f.readlines()]
        f.close()
        self.webhosts_len = len(self.webhosts)

        f = open('tests/perf/weblog/useragents.sample')
        self.useragents = [x.strip() for x in f.readlines()]
        f.close()
        self.useragents_len = len(self.useragents)

        f = open('tests/perf/weblog/webserverstatus.sample')
        self.webserverstatus = [x.strip() for x in f.readlines()]
        f.close()
        self.webserverstatus_len = len(self.webserverstatus)

    def gen(self, count, earliest, latest, **kwargs):
        # logger.debug("weblog: external_ips_len: %s webhosts_len: %s useragents_len: %s webserverstatus_len: %s" % \
                    # (self.external_ips_len, self.webhosts_len, self.useragents_len, self.webserverstatus_len))
        l = [ { '_raw': ('%s %s - - [%s] ' \
                + '"GET /product.screen?product_id=HolyGouda&JSESSIONID=SD3SL1FF7ADFF8 HTTP 1.1" '\
                + '%s %s "http://shop.buttercupgames.com/cart.do?action=view&itemId=HolyGouda" '\
                + '"%s" %s') % \
                (self.external_ips[random.randint(0, self.external_ips_len-1)], \
                self.webhosts[random.randint(0, self.webhosts_len-1)], \
                latest.strftime('%d/%b/%Y %H:%M:%S:%f'), \
                self.webserverstatus[random.randint(0, self.webserverstatus_len-1)], \
                random.randint(100, 1000), \
                self.useragents[random.randint(0, self.useragents_len-1)], \
                random.randint(200, 2000)),
                'index': 'main',
                'sourcetype': 'access_combined',
                'host': 'log.buttercupgames.com',
                'source': '/opt/access_combined.log',
                '_time': int(time.mktime(latest.timetuple())) } for i in xrange(count) ]


        self._out.bulksend(l)
        return 0


def load():
    return WeblogGenerator
