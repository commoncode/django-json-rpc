import os
import sys
import unittest
import subprocess
import time
import json
import urllib
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
TEST_DEFAULTS = {
  'ROOT_URLCONF': 'jsontesturls',
  'DEBUG': True,
  'DEBUG_PROPAGATE_EXCEPTIONS': True,
  'DATETIME_FORMAT': 'N j, Y, P',
  'USE_I18N': False
}
from django.conf import settings
settings.configure(**TEST_DEFAULTS)

from jsonrpc import jsonrpc_method
from jsonrpc.proxy import ServiceProxy
from jsonrpc.site import json


def _call(host, req):
  return json.loads(urllib.urlopen(host, json.dumps(req)).read())


def json_serve_thread():
  from wsgiref.simple_server import make_server
  from django.core.handlers.wsgi import WSGIHandler
  http = make_server('', 8999, WSGIHandler())
  http.serve_forever()

@jsonrpc_method('jsonrpc.test')
def echo(request, string):
  return string

@jsonrpc_method('jsonrpc.notify')
def notify(request, string):
  pass

@jsonrpc_method('jsonrpc.fails')
def fails(request, string):
  raise IndexError

@jsonrpc_method('jsonrpc.strangeEcho')
def strangeEcho(request, string, omg, wtf, nowai, yeswai='Default'):
  return [string, omg, wtf, nowai, yeswai]

@jsonrpc_method('jsonrpc.safeEcho', safe=True)
def safeEcho(self, string):
  return string


class JSONRPCTest(unittest.TestCase):
  def setUp(self):
    self.proc = subprocess.Popen(['python', 
      os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.py')])
    self.host = 'http://127.0.0.1:8999/json/'
    self.proxy10 = ServiceProxy(self.host, version='1.0')
    self.proxy20 = ServiceProxy(self.host, version='2.0')
  
  def tearDown(self):
    self.proc.terminate()
    self.proc.wait()
  
  def test_10(self):
    self.assertEqual(
      self.proxy10.jsonrpc.test('this is a string')[u'result'], 
      u'this is a string')
  
  def test_11(self):
    req = {
      u'version': u'1.1',
      u'method': u'jsonrpc.test',
      u'params': [u'this is a string'],
      u'id': u'holy-mother-of-god'
    }
    resp = _call(self.host, req)
    self.assertEquals(resp[u'id'], req[u'id'])
    self.assertEquals(resp[u'result'], req[u'params'][0])
  
  def test_10_notify(self):
    pass
  
  def test_11_positional_mixed_args(self):
    req = {
      u'version': u'1.1',
      u'method': u'jsonrpc.strangeEcho',
      u'params': {u'1': u'this is a string', u'2': u'this is omg', 
                  u'wtf': u'pants', u'nowai': 'nopants'},
      u'id': u'toostrange'
    }
    resp = _call(self.host, req)
    self.assertEquals(resp[u'result'][-1], u'Default')
    self.assertEquals(resp[u'result'][1], u'this is omg')
    self.assertEquals(resp[u'result'][0], u'this is a string')
    self.assert_(u'error' not in resp)
  
  def test_11_GET(self):
    pass
  
  def test_11_GET_unsafe(self):
    pass
  
  def test_11_service_description(self):
    pass
  
  def test_20_keyword_args(self):
    self.assertEqual(
      self.proxy20.jsonrpc.test(string='this is a string')[u'result'],
      u'this is a string')
  
  def test_20_positional_args(self):
    self.assertEqual(
      self.proxy20.jsonrpc.test('this is a string')[u'result'],
      u'this is a string')
  
  def test_20_notify(self):
    req = {
      u'jsonrpc': u'2.0', 
      u'method': u'jsonrpc.notify', 
      u'params': [u'this is a string'], 
      u'id': None
    }
    resp = None
    try:
      resp = json.loads(urllib.urlopen(self.host, json.dumps(req)).read())
    except ValueError:
      pass
    self.assert_(resp is None)
  
  def test_20_batch(self):
    req = [{
      u'jsonrpc': u'2.0',
      u'method': u'jsonrpc.test',
      u'params': [u'this is a string'],
      u'id': u'id-'+unicode(i)
    } for i in range(5)]
    resp = json.loads(urllib.urlopen(self.host, json.dumps(req)).read())
    self.assertEquals(len(resp), len(req))
    for i, D in enumerate(resp):
      self.assertEquals(D[u'result'], req[i][u'params'][0])
      self.assertEquals(D[u'id'], req[i][u'id'])
  
  def test_20_batch_with_errors(self):
    req = [{
      u'jsonrpc': u'2.0',
      u'method': u'jsonrpc.test' if not i % 2 else u'jsonrpc.fails',
      u'params': [u'this is a string'],
      u'id': u'id-'+unicode(i)
    } for i in range(10)]
    resp = json.loads(urllib.urlopen(self.host, json.dumps(req)).read())
    self.assertEquals(len(resp), len(req))
    for i, D in enumerate(resp):
      if not i % 2:
        self.assertEquals(D[u'result'], req[i][u'params'][0])
        self.assertEquals(D[u'id'], req[i][u'id'])
      else:
        self.assertEquals(D[u'result'], None)
        self.assert_(u'error' in D)
        self.assertEquals(D[u'error'][u'code'], 500)


if __name__ == '__main__':
  json_serve_thread()