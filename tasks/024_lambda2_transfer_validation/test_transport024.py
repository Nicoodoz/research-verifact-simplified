import json,ssl,unittest,urllib.error
from unittest.mock import patch
import core024 as c
from transport024 import DiagnosticClient
from transport_direct024 import DirectClient
class Transport(unittest.TestCase):
    def test_body_endpoint_headers_unchanged(self):
        sent=[]
        class Response:
            status=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return b'{}'
        class Opener:
            def open(self,request,timeout):sent.append((request.full_url,request.data,request.headers,timeout));return Response()
        cfg=c.Config('FAKE_TEST_SECRET',model=c.MODELS['deepseek']);body=c.old.body('x','y');body['model']=cfg.model
        with patch('urllib.request.build_opener',return_value=Opener()):
            DiagnosticClient(cfg).send(body);DirectClient(cfg).send(body)
        self.assertEqual(sent[0],sent[1]);self.assertEqual(json.loads(sent[0][1]),body)
    def test_errors_do_not_echo_secret(self):
        class Opener:
            def open(self,*args,**kwargs):raise urllib.error.URLError(ssl.SSLEOFError(8,'FAKE_TEST_SECRET'))
        cfg=c.Config('FAKE_TEST_SECRET',model=c.MODELS['deepseek']);body=c.old.body('x','y');body['model']=cfg.model
        with patch('urllib.request.build_opener',return_value=Opener()):r=DirectClient(cfg).send(body)
        self.assertEqual(r['http_status'],0);self.assertNotIn(cfg.api_key,json.dumps(r));self.assertEqual(r['transport_diagnostic']['reason_type'],'SSLEOFError')
if __name__=='__main__':unittest.main()
