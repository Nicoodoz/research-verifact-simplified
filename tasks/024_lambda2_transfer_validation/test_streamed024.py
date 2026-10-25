import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run024_streamed as run
c=run.c
class Scheduling(unittest.TestCase):
    def simulate(self,cap=80):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);jobs=[]
            for i in range(6):
                b=c.old.body('claim '+str(i),'reference');b['model']=c.MODELS['deepseek']
                jobs.append(dict(request_id=str(i),model_key='deepseek',arm='B',body=b))
            sent=[]
            class Client:
                def __init__(self,*a,**k):pass
                def validate(self,b):pass
                def send(self,b):
                    sent.append(b)
                    n=dict(model=b['model'],choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(verdict='Supported',reason='x',checks=[]))))],usage=dict(prompt_tokens=100,completion_tokens=10))
                    return dict(http_status=200,body_text=json.dumps(n))
            cfg=c.Config('FAKE_UNIT_TEST_KEY')
            with contextlib.ExitStack() as st:
                st.enter_context(patch.object(c,'OUT',out));st.enter_context(patch.object(c,'CAP',cap))
                st.enter_context(patch.object(c,'verify_inputs',return_value=jobs))
                st.enter_context(patch.object(c,'load_attempts',return_value=([],{})))
                st.enter_context(patch.object(c,'load_config',return_value=cfg))
                st.enter_context(patch.object(c,'read',return_value=dict(endpoint=cfg.endpoint,expected_cny={'deepseek':.001,'qwen':.001})))
                st.enter_context(patch.object(c,'AliyunClient',Client))
                st.enter_context(contextlib.redirect_stdout(io.StringIO()))
                run.run(2,False)
            self.assertFalse((out/'live.lock').exists())
            req=list(out.glob('attempts/*/request.json'));rec=list(out.glob('attempts/*/receipt.json'))
            self.assertEqual(len(sent),len(req));self.assertEqual(len(req),len(rec))
            for p in req:
                r=json.loads(p.read_text(encoding='utf-8'))
                self.assertLessEqual(r['prior_task_used_or_reserved_cny']+r['reservation_cny'],cap)
            return len(sent)
    def test_exactly_once_and_budget_reservations(self):self.assertEqual(self.simulate(),6)
    def test_cap_refuses_before_send(self):self.assertEqual(self.simulate(.0001),0)
if __name__=='__main__':unittest.main()
