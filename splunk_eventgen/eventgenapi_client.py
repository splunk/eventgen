import requests
import urlparse
import json
import eventgenapi_common

class EventgenApiClient:
    def __init__(self, url):    
        self.session = requests.Session()
        self.url = url

    def start(self):
       url = urlparse.urljoin(self.url, "ctrl")
       res = self.session.put(url, params={'command': 'start'})
       if (res.status_code !=  200):
          raise Exception("HTTP error", res.status_code)
       return json.loads(res.text)
    
    def stop(self):
       url = urlparse.urljoin(self.url, "ctrl")
       res = self.session.put(url, params={'command': 'stop'})
       if (res.status_code !=  200):
          raise Exception("HTTP error", res.status_code)
       return json.loads(res.text)

    def reload(self):
       url = urlparse.urljoin(self.url, "ctrl")
       res = self.session.put(url, params={'command': 'reload'})

       if (res.status_code !=  200):
          raise Exception("HTTP error", res.status_code)
       return json.loads(res.text)
    
    def updateConf(self, confdata):
       url = urlparse.urljoin(self.url, "updateconf")
       res = self.session.put(url, params={'eventgenconf': confdata})
       if (res.status_code !=  200):
          raise Exception("HTTP error", res.status_code)
       return
    
    def getStatus(self):
       url = urlparse.urljoin(self.url, "status")
       res = self.session.get(url)
       if (res.status_code !=  200):
          raise Exception("HTTP error", res.status_code)
       return json.loads(res.text)
   
    def getConf(self):
       url = urlparse.urljoin(self.url, "getconf")
       res = self.session.get(url)
       if (res.status_code !=  200):
          raise Exception("HTTP error", res.status_code)
       return res.text
