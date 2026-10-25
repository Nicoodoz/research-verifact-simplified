"""Synthetic transport-only tests; never access keys or network."""
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run075 as r
class Fake:
 def __init__(self,statuses):self.statuses=list(statuses);self.calls=[]
 def validate(self,b):pass
 def send(self,b):
  self.calls.append(b);s=self.statuses.pop(0)
  return dict(http_status=s,body_text=json.dumps(dict(usage=dict(prompt_tokens=100,completion_tokens=100))),outcome_unknown=s==0)
def job(n):
 b=dict(model=r.MODEL,enable_thinking=True,max_tokens=8192,messages=[dict(role='user',content='synthetic test '+str(n))])
 return dict(request_id='synthetic_'+str(n),stage='pilot',arm='B',id=str(n),sid='synthetic',body=b,body_sha256=r.digest(b))
class TransportTests(unittest.TestCase):
 def execute(self,statuses,cap=20.,existing=False):
  with tempfile.TemporaryDirectory(prefix='075_transport_',dir=r.ROOT/'outputs/075_annotated_static_examples') as td:
   o=Path(td);fake=Fake(statuses);jobs=[job(1),job(2)] if existing else [job(1)]
   with patch.object(r,'OUT',o),patch.object(r,'CAP',cap),patch.object(r,'client',lambda:fake),patch.object(r,'check_frozen',lambda s:None),patch.object(r,'jobs_for',lambda s:jobs),patch.object(r.c53,'parse_response',lambda *a:dict(status='valid',model_returned=r.MODEL)):
    if existing:
     p=o/'attempts'/'existing';p.mkdir(parents=True)
     r.save(p/'request.json',dict(job=jobs[0],attempt_id='prior',attempt_no=1,reservation_cny=r.bound(jobs[0]['body'])))
     r.save(p/'receipt.json',dict(request_sha256=r.sha(p/'request.json'),transport=dict(http_status=200,body_text=json.dumps(dict(usage=dict(prompt_tokens=100,completion_tokens=100))))))
    with contextlib.redirect_stdout(io.StringIO()):r.run('pilot',workers=1)
    a,ans=r.attempt_state()
    return fake.calls,a,ans
 def test_http0_recovers_and_reserves_original(self):
  calls,a,ans=self.execute([0,200]);self.assertEqual(len(calls),2);self.assertEqual(calls[0],calls[1]);self.assertEqual(len(ans),1);self.assertAlmostEqual(sum(x['cost_cny'] for x in a),r.bound(calls[0])+.0012)
 def test_http503_recovers(self):
  calls,a,ans=self.execute([503,200]);self.assertEqual(len(ans),1);self.assertAlmostEqual(sum(x['cost_cny'] for x in a),.0012)
 def test_budget_stops_before_send(self):
  calls,a,ans=self.execute([],cap=.001);self.assertFalse(calls);self.assertFalse(a)
 def test_resume_never_resends_answer(self):
  calls,a,ans=self.execute([200],existing=True);self.assertEqual(len(calls),1);self.assertEqual(calls[0],job(2)['body']);self.assertEqual(len(ans),2)
if __name__=='__main__':unittest.main()
