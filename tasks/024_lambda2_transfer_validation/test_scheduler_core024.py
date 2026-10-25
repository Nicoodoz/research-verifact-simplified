import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run024_core as run
c=run.c
class Scheduler(unittest.TestCase):
    def test_isolated_core_invalid_continues_without_retry(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);jobs=[];sent=[]
            for i in range(6):
                b=c.old.body(str(i),'ref');b['model']=c.MODELS['deepseek'];jobs.append(dict(request_id=str(i),model_key='deepseek',arm='B',body=b))
            class Client:
                def __init__(self,*a,**k):pass
                def validate(self,b):pass
                def send(self,b):
                    number=json.loads(b['messages'][1]['content'])['proposition'];sent.append(number)
                    answer=dict(verdict='illegal' if number=='0' else 'Supported',reason='x',checks=[])
                    native=dict(model=b['model'],choices=[dict(finish_reason='stop',message=dict(content=json.dumps(answer)))],usage=dict(prompt_tokens=100,completion_tokens=10))
                    return dict(http_status=200,body_text=json.dumps(native))
            cfg=c.Config('FAKE_UNIT_TEST_KEY')
            with contextlib.ExitStack() as st:
                for name,value in [('OUT',out),('verify_inputs',lambda:jobs),('load_attempts',lambda js:([],{})),('load_config',lambda p:cfg),('read',lambda p:dict(endpoint=cfg.endpoint,expected_cny={'deepseek':.001,'qwen':.001})),('AliyunClient',Client)]:st.enter_context(patch.object(c,name,value))
                st.enter_context(contextlib.redirect_stdout(io.StringIO()));run.run(2,False)
            self.assertEqual(sorted(sent),[str(i) for i in range(6)]);self.assertEqual(len(list(out.glob('attempts/*/receipt.json'))),6)
            self.assertFalse((out/'live.lock').exists())
if __name__=='__main__':unittest.main()
