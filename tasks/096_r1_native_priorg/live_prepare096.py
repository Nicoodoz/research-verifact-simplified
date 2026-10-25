"""Latest user-authorized amendment. No network, immutable live_v1 artifacts."""
import os,sys,copy,collections,math,json
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import common096 as c
O=c.OUT/'live_v1';P=c.PRIVATE/'live_v1'

def sample(pool,n,seed):
    groups=collections.defaultdict(list)
    for r in pool:groups[(r['GT'],r['author'])].append(r)
    exact={k:n*len(v)/len(pool) for k,v in groups.items()};q={k:math.floor(x) for k,x in exact.items()}
    for k in sorted(groups,key=lambda k:(-(exact[k]-q[k]),k))[:n-sum(q.values())]:q[k]+=1
    rr=[dict(r,inclusion_weight=len(v)/q[k]) for k,v in sorted(groups.items()) for r in sorted(v,key=lambda r:c.key(seed,r['id']))[:q[k]]]
    return sorted(rr,key=lambda r:c.key(seed+'order/',r['id']))

def dist(rr):
    return dict(N=len(rr),patients=len({r['sid'] for r in rr}),GT=dict(collections.Counter(r['GT'] for r in rr)),author=dict(collections.Counter(r['author'] for r in rr)),patient_counts=dict(collections.Counter(r['sid'] for r in rr)))

def main():
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(c.TOKENIZER,local_files_only=True,trust_remote_code=False)
    old=c.lines(c.PRIVATE/'jobs.jsonl');cal=[j for j in old if j['stage']=='calibration'];assert len(cal)==143
    patients=set(c.read(c.OUT/'calibration_recipe.json')['patients']);old085={j['id'] for j in c.lines(c.ROOT/'.local_models/085_valdemardi_private/jobs.jsonl')}
    rows=c.lines(c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl');inputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')}
    pool=[];ledger=[]
    for r in rows:
        reason=('calibration_patient' if r['sid'] in patients else '085_ID' if r['id'] in old085 else 'missing_V4_raw' if not r['B_raw_valid'] else 'missing_Original' if r['predictions'].get('Original') not in c.LABELS else 'missing_request' if r['id'] not in inputs or not r['B_present'] else None)
        row={k:r[k] for k in ['id','sid','GT','author','C48_source','B_core_valid','B_raw_valid']};row['exclusion_reason']=reason;ledger.append(row)
        if reason is None:pool.append(row)
    panels={n:sample(pool,n,'096/live/natural/v1/') for n in [400,600,800]}
    assert {r['id'] for r in panels[400]}<={r['id'] for r in panels[600]}<={r['id'] for r in panels[800]}
    used={r['id'] for r in panels[800]};diagnostics={}
    for n in [100,120,200]:
        diagnostics[n]=sum([sample([r for r in pool if r['GT']==label and r['id'] not in used],n//2,'096/live/diagnostic/v1/') for label in c.LABELS[1:]],[])
    assert {r['id'] for r in diagnostics[100]}<={r['id'] for r in diagnostics[120]}<={r['id'] for r in diagnostics[200]}
    jobs=copy.deepcopy(cal);template=c.read(c.PRIVATE/'template.json');idx={r['id']:r for r in rows}
    for stage,rr in [('natural',panels[800]),('diagnostic',diagnostics[200])]:
        for r in rr:
            x=inputs[r['id']];b=idx[r['id']]
            assert c.key('',x['text'])==b['claim_sha256'] and c.key('',x['reference'])==b['reference_sha256']
            body=copy.deepcopy(template);body['messages'][1]['content']=c.encoded(dict(proposition=x['text'],reference=x['reference'])).decode();h=c.digest(body)
            jobs.append(dict(id=r['id'],sid=r['sid'],stage=stage,body=body,body_sha256=h,request_id=c.key('096/live/'+r['id']+'/',h)[:32]))
    lengths=[]
    for j in jobs:
        n=len(tok.apply_chat_template(j['body']['messages'],tokenize=True,add_generation_prompt=True,truncation=False));assert n+8192<=20000
        lengths.append(dict(id=j['id'],request_id=j['request_id'],input_tokens=n,stage=j['stage']))
    li={r['id']:r['input_tokens'] for r in lengths};base=sorted(panels[400],key=lambda r:(li[r['id']],r['id']));p0=base.pop(0)
    bins=[base[:133],base[133:266],base[266:]]
    bins=[sorted(v,key=lambda r:c.key('096/benchmark/v1/',r['id'])) for v in bins]
    bench={'P0':dict(concurrency=1,ids=[p0['id']])}
    for stage,cc,n in [('P1',2,8),('P2',4,12),('P3',8,16),('P4',12,24),('P5',16,24)]:
        ids=[bins[i%3].pop(0)['id'] for i in range(n)];bench[stage]=dict(concurrency=cc,ids=ids,lengths=[li[i] for i in ids])
    c.putl(P/'jobs.jsonl',jobs);c.putl(P/'comparator_cache.jsonl',[idx[r['id']] for r in panels[800]+diagnostics[200]])
    c.putl(O/'candidate_ledger.jsonl',ledger);c.putl(O/'local_token_lengths.jsonl',lengths)
    for n,rr in panels.items():c.putl(O/f'natural{n}.jsonl',rr)
    for n,rr in diagnostics.items():c.putl(O/f'diagnostic{n}.jsonl',rr)
    c.put(O/'benchmark_plan.json',bench)
    c.put(O/'sampling_summary.json',dict(eligible=dist(pool),natural={str(n):dist(rr) for n,rr in panels.items()},diagnostic={str(n):dist(rr) for n,rr in diagnostics.items()},exclusions=dict(collections.Counter(r['exclusion_reason'] for r in ledger))))
    c.putl(O/'request_manifest.jsonl',[{k:j[k] for k in ['id','sid','stage','request_id','body_sha256']} for j in jobs])
    c.put(O/'freeze.json',dict(status='FROZEN_BEFORE_FIRST_INFERENCE',utc=c.now(),HEAD='28daf95e9b12270d8089246176023c66c4cf298e',jobs_sha256=c.sha(P/'jobs.jsonl'),request_manifest_sha256=c.sha(O/'request_manifest.jsonl'),files={p.name:c.sha(p) for p in O.glob('*.json*')},calibration143_unchanged=True,benchmark_all_within_every_tier=True,GT_in_requests=False,evaluation_accuracy_read=False,tiers={'A':[800,200],'B':[600,120],'C':[400,100]},price_unknown=True,authorization='Latest user attachment: benchmark then time-based tiers, existing user-managed instance; no purchases or extra deployment',remote_revision='ModelScope snapshot master; immutable revision not supplied; no claim of HF byte equivalence'))
    print('LIVE_FREEZE_READY',len(jobs),'eligible',len(pool),'max_context',max(r['input_tokens'] for r in lengths)+8192)
if __name__=='__main__':main()
