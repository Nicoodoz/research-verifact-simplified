"""Meaningful boundary/ledger/alias checks; no network or clinical quality."""
import copy,json
import common100 as c
import gates100 as g
import runtime100 as rt
from prepare100 import job

def table(mcc=.5,pa=.8,fs=.1,count=3,ns=.5,na=.5):return dict(mcc=mcc,percent_agreement=pa,false_S_rate=fs,false_S=count,per_class={'Not Supported':dict(recall=ns),'Not Addressed':dict(recall=na)})
def main():
 natural=dict(O=table(),S24=table(.49,.79),L24=table(.52,.79),**{'EHR-all':table(.4,.74)})
 pressure=dict(O=table(fs=.25),S24=table(fs=.2,count=2),L24=table(fs=.25,count=3),**{'EHR-all':table(fs=.1,count=1)})
 cov={a:1. for a in g.ORDER};cost={a:.01 for a in g.ORDER}
 out=g.development_select(natural,pressure,cov,cost);assert out['winner']=='S24' and not out['checks']['EHR-all']['eligible']
 cov['S24']=.94;assert g.development_select(natural,pressure,cov,cost)['winner']=='L24'
 comparison=dict(paired=dict(metrics=dict(mcc=dict(ci95=[.001,.1]))),false_S_rate_delta_CI95=[-.1,.03])
 a=table(.5,.8,.1);b=table(.53,.78,.12);test=g.practical(a,b,comparison);assert test['MCC_route_point'] and test['uncertainty_pass']
 guard=g.pressure_guard(a,a);assert g.confirmation_status(test,guard,{})=='确认通过'
 assert g.confirmation_status(test,guard,dict(MCC_reversed=True))=='点值改善但未确认'
 assert not g.pressure_guard(a,table(fs=.151))['pass_all']
 row=dict(id='synthetic',sid='synthetic',stage='development',panel='natural');body=dict(model='deepseek-v4-flash-0731',max_tokens=8192,messages=[dict(role='user',content='synthetic')])
 x=job(row,'S24',body);y=job(row,'L24',copy.deepcopy(body));z=job(row,'S24',body,1);assert x['request_id']==y['request_id']!=z['request_id']
 reservation=rt.reserve(x);tr=dict(http_status=200,started_utc='2026-10-26T16:00:00+00:00',ended_utc='2026-10-26T16:00:01+00:00',body_text=json.dumps(dict(model=body['model'],usage=dict(prompt_tokens=2000,completion_tokens=1000,prompt_tokens_details=dict(cached_tokens=1000)))))
 value,basis=rt.account(x,tr,reservation);assert abs(value-.00615)<1e-10 and basis=='usage_idle'
 assert rt.account(x,dict(http_status=0),reservation)[0]==reservation
 tr['body_text']=json.dumps(dict(model='wrong',usage=dict(prompt_tokens=1,completion_tokens=1)));assert rt.account(x,tr,reservation)[0]==reservation
 c.put(c.OUT/'execution_fixture_checks.json',dict(utc=c.utc(),status='PASS',paid_API_calls=0,synthetic_only=True,checks=['development nearby and pressure-risk precedence','coverage veto','practical exact boundaries with CIs','repeat reversal and pressure failure','same-body aliases separate from repeats','thinking-inclusive original prices','unknown and wrong-model reserves retained']))
 print('PASS: seven execution/decision fixture groups')
if __name__=='__main__':main()
