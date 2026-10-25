import copy,re
from collections import Counter
import common094 as c
import method094 as m
PATTERN=r'\b(before|after|during|following|transferred|removed|resolved|remained|stable|stabiliz\w*|discharged|started|stopped|continued|underwent|because|due to|found|improved|worsened)\b'
def job(pid,stage,arm,body):return dict(request_id=c.h('094/'+pid+'/'+stage+'/'+arm)[:28],id=pid,stage=stage,arm=arm,body=body,body_sha256=c.h(c.canonical(body)),bound_cny=c.bound(body))
def main():
    source=c.ROOT/'.local_models/092/inputs.jsonl';pool=c.lines(source);byid={r['proposition_id']:r for r in pool}
    meta={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')}
    template=next(j['body'] for j in c.lines(c.ROOT/'.local_models/093/main_jobs.jsonl'))
    assert template['model']==c.MODEL and template['max_tokens']==8192 and template['reasoning_effort']=='high'
    ranked=sorted(byid,key=lambda x:c.h('094/natural/'+x));used=set();selected=[]
    for pid in ranked[:20]:selected.append((pid,'natural'));used.add(pid)
    counts=Counter()
    for i in range(12):
        label=['Supported','Not Supported','Not Addressed'][i%3]
        available=[pid for pid,r in byid.items() if pid not in used and meta[pid]['GT']==label and re.search(PATTERN,r['text'],re.I)]
        pid=min(available,key=lambda x:(counts[meta[x]['sid']],c.h('094/mechanism/patient/'+meta[x]['sid']),c.h('094/mechanism/'+x)))
        selected.append((pid,'mechanism'));used.add(pid);counts[meta[pid]['sid']]+=1
    def budget(pid):
        r=byid[pid];q={'question':'x'*1200,'claimed_value':'x'*800};record='x'*4000
        bodies=[m.gen_body(r['text']),m.qa_body(r,q,'V'),m.qa_body(r,q,'Q'),m.judge_body(template,r),m.judge_body(template,r,q,record),m.judge_body(template,r,q,record)]
        return {k:c.bound(b) for k,b in zip(['generate','extract_V','extract_Q','judge_B','judge_V','judge_Q'],bodies)}
    upper=sum(sum(budget(pid).values()) for pid,_ in selected)
    assert upper+2+.2<=20,('reduce sample BEFORE any calls',upper)
    private=[];sample=[];allocations={};jobs=[]
    for pid,panel in selected:
        r=byid[pid];private.append(dict(id=pid,text=r['text'],reference=r['reference']));sample.append(dict(id=pid,panel=panel,**{k:meta[pid][k] for k in ['sid','author','GT','historical_role']}))
        allocations[pid]=budget(pid);jobs.append(job(pid,'generate','shared',m.gen_body(r['text'])))
    synthetic=dict(id='synthetic',text='The synthetic line was removed on day 2.',reference='1. Date: day 2, Time: 09:00, Note Category: Synthetic, Note ID: 0, Raw characters: [0,47) | Text: The line remained in place; removal was planned.')
    q=dict(question='What, if anything, is documented about the line status and timing?',claimed_value='removed on day 2')
    preflight=[job('synthetic','preflight',a,m.qa_body(synthetic,q,a)) for a in ['V','Q']]
    c.putl(c.PRIVATE/'inputs.jsonl',private);c.put(c.PRIVATE/'judge_template.json',template);c.putl(c.PRIVATE/'generate_jobs.jsonl',jobs);c.putl(c.PRIVATE/'preflight_jobs.jsonl',preflight)
    c.putl(c.OUT/'sample.jsonl',sample)
    paths=[c.TASK/p for p in ['protocol.md','common094.py','method094.py','prepare094.py']]+[source,c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl',c.PRIVATE/'inputs.jsonl',c.PRIVATE/'judge_template.json',c.PRIVATE/'generate_jobs.jsonl',c.PRIVATE/'preflight_jobs.jsonl',c.OUT/'sample.jsonl']
    c.put(c.OUT/'design_freeze.json',dict(utc=c.now(),HEAD='03a58bb3ba19317b1d91700209cc5df7eae1b189',cap_cny=20,main_all_stage_upper_cny=upper,preflight_upper_cny=sum(j['bound_cny'] for j in preflight),recovery_reserve_cny=2,allocations=allocations,panels={p:dict(N=sum(r['panel']==p for r in sample),patients=len({r['sid'] for r in sample if r['panel']==p}),GT=dict(Counter(r['GT'] for r in sample if r['panel']==p))) for p in ['natural','mechanism']},sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},price=dict(model=c.MODEL,input=3,output=9,unit='RMB per million tokens; busy undiscounted no-cache ceiling',url='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash'),mechanism_regex=PATTERN))
    print('Frozen',len(selected),'main full upper',upper,'panels',c.read(c.OUT/'design_freeze.json')['panels'])
if __name__=='__main__':main()
