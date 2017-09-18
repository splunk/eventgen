import requests
import unittest
import eventgenapi_common
import eventgenapi_client

class TestEventgenClient(unittest.TestCase):
   def setUp(self):
      self.url = "http://127.0.0.1:9021/"
      self.session = requests.Session()
      self.client = eventgenapi_client.EventgenApiClient(self.url)
  
   def test_getIndex(self):
       res = self.session.get(self.url)
       self.assertEqual(res.status_code, 200)

   def test_command(self):
       res = self.client.start()
       status = self.client.getStatus()
       self.assertEqual(status[eventgenapi_common.EVENTGEN_STATUS_TAG], eventgenapi_common.EVENTGEN_STATUS_RUNNING)
       self.assertEqual(res[eventgenapi_common.EVENTGEN_PID_TAG], status[eventgenapi_common.EVENTGEN_PID_TAG])
       res = self.client.reload()
       #we realoaded, pid should be different
       self.assertEqual(res[eventgenapi_common.EVENTGEN_STATUS_TAG], eventgenapi_common.EVENTGEN_STATUS_RUNNING)
       self.assertNotEqual(res[eventgenapi_common.EVENTGEN_PID_TAG], status[eventgenapi_common.EVENTGEN_PID_TAG])
       res = self.client.stop()
       status = self.client.getStatus()
       self.assertEqual(status[eventgenapi_common.EVENTGEN_STATUS_TAG], eventgenapi_common.EVENTGEN_STATUS_STOPPED)

   def test_updateConf(self):
       confdata = 'testconfdata'
       res = self.client.updateConf(confdata)
       res = self.client.getConf()
       self.assertEqual(res, confdata)

if __name__ == '__main__':
    unittest.main()
