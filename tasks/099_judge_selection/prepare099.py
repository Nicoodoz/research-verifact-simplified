"""One outcome-blind scale choice and immutable exact-input jobs for all candidates."""
from collections import Counter, defaultdict
import copy
import sys
import duckdb
import pandas as pd
import common099 as c
sys.path.insert(0,str(c.ROOT/'tasks/097_native_judge_source_dependence'))
from prepare_a import original_style_prompt,SYSTEM

def proportional(rows,n,seed):
    groups=defaultdict(list)
    for r in rows:groups[r['GT'],r['author']].append(r)
    exact={k:n*len(v)/len(rows) for k,v in groups.items()};quota={k:int(v) for k,v in exact.items()}
    for k in sorted(groups,key=lambda k:(-(exact[k]-quota[k]),k))[:n-sum(quota.values())]:quota[k]+=1
    chosen=[r for k,v in groups.items() for r in sorted(v,key=lambda r:c.digest(seed+r['id']))[:quota[k]]]
    return sorted(chosen,key=lambda r:c.digest('099/order/v1/'+r['id']))

def body(model,claim,reference):
    return dict(model=model,messages=[dict(role='system',content=SYSTEM),dict(role='user',content=original_style_prompt(claim,reference))],
                temperature=0,top_p=1,n=1,stream=False,enable_thinking=True,thinking_budget=c.THINKING,max_tokens=c.ANSWER)

def main():
    assert (c.OUT/'model_metadata.json').exists()
    prior_dir=c.PRIVATE/'attempts'
    assert not prior_dir.exists() or not list(prior_dir.glob('*/request.json')), 'Existing099 calls: preserve freeze and ledger, do not replan'
    base=c.lines(c.ROOT/'outputs/097_native_judge_source_dependence/a_execution_panel.jsonl')
    source097=c.lines(c.ROOT/'outputs/097_native_judge_source_dependence/a_same_id.jsonl')
    native097={r['id']:r for r in source097}
    p96=c.lines(c.ROOT/'outputs/096_r1_native_priorg/main_panel.jsonl')
    cohort={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')}
    rawinputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')}
    pool={r['id']:r for r in base}
    for r in p96:
        if r['eligible']:pool.setdefault(r['id'],r)
    ids=list(pool)
    with duckdb.connect() as db:
        db.register('wanted',pd.DataFrame({'proposition_id':ids}))
        vv=db.execute('SELECT v.proposition_id,v.reference_id,v.verdict FROM read_parquet(?) v JOIN wanted USING(proposition_id) WHERE rater_alias=?',
            [str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet'),'v1.1.0-rater-121']).fetchall()
        assert len(vv)==len(ids)==len({x[0] for x in vv})
        db.register('refids',pd.DataFrame({'reference_id':list({x[1] for x in vv})}))
        refs=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN refids USING(reference_id)',
            [str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/reference_payloads.parquet')]).fetchall())
    vals={pid:(rid,label) for pid,rid,label in vv};rows={}
    for pid,r in pool.items():
        x=cohort[pid];inp=rawinputs[pid];rid,orig=vals[pid]
        assert r['GT']==x['GT'] and str(r['sid'])==str(x['sid']) and orig==x['original'] and c.digest(refs[rid])==rid
        if pid in native097:
            assert c.digest(inp['reference'])==native097[pid]['C48_sha256'] and rid==native097[pid]['published_reference_id']
        rows[pid]=dict(id=pid,sid=str(x['sid']),author=x['author'],GT=x['GT'],Original=orig,historical_role=x['historical_role'],
                      claim=inp['text'],O=refs[rid],C=inp['reference'],reference_id=rid,
                      V4_097_O=native097.get(pid,{}).get('predictions',{}).get('published_native'),V4_097_C=native097.get(pid,{}).get('predictions',{}).get('C48_native'))
    natural_pool=[rows[r['id']] for r in base]
    diag_pool=[rows[r['id']] for r in p96 if r['eligible']]
    forecasts=[]
    for n,cn,dp in [(160,64,24),(144,56,20),(128,48,20),(112,48,20),(96,40,20),(80,32,16),(64,24,16)]:
        natural=proportional(natural_pool,n,'099/natural/v1/')
        natural_ids={r['id'] for r in natural}
        diag=[]
        for lab in ['Not Supported','Not Addressed']:
            pp=[r for r in diag_pool if r['GT']==lab and r['id'] not in natural_ids]
            diag.extend(proportional(pp,dp,'099/diagnostic/'+lab+'/v1/'))
        cids={r['id'] for r in sorted(natural,key=lambda r:c.digest('099/C/v1/'+r['id']))[:cn]}
        repeat_ids={r['id'] for r in sorted(natural,key=lambda r:c.digest('099/repeat/v1/'+r['id']))[:8]}
        sample=[dict(r,panel='natural',C_subset=r['id'] in cids,repeat_subset=r['id'] in repeat_ids) for r in natural]+[dict(r,panel='diagnostic',C_subset=False,repeat_subset=False) for r in diag]
        jobs=[]
        for index,row in enumerate(sample):
            contexts=['O','C'] if row['C_subset'] else ['O']
            models=list(c.MODELS);models=models[index%4:]+models[:index%4]
            for context in contexts:
                for model in models:
                    b=body(model,row['claim'],row[context]);checksum=c.digest(c.canonical(b))
                    rid=c.digest(c.canonical(['099/v1',row['id'],context,model,0,checksum]))[:28]
                    jobs.append(dict(id=row['id'],sid=row['sid'],panel=row['panel'],context=context,model=model,repeat=0,request_id=rid,body=b,body_sha256=checksum,bound_cny=c.bound(b)))
        for index,row in enumerate(r for r in sample if r['repeat_subset']):
            models=list(c.MODELS);models=models[index%4:]+models[:index%4]
            for model in models:
                b=body(model,row['claim'],row['O']);checksum=c.digest(c.canonical(b));rid=c.digest(c.canonical(['099/v1',row['id'],'O',model,1,checksum]))[:28]
                jobs.append(dict(id=row['id'],sid=row['sid'],panel=row['panel'],context='O',model=model,repeat=1,request_id=rid,body=b,body_sha256=checksum,bound_cny=c.bound(b)))
        estimates={m:0. for m in c.MODELS}
        for j in jobs:
            # Conservatively above097 observed token/character ratio; all max thinking+answer.
            inp=sum(len(x['content']) for x in j['body']['messages'])*.4+256
            ip,op,_=c.PRICES[j['model']]
            estimates[j['model']]+=(inp*ip+(c.THINKING+c.ANSWER+32)*op)/1e6
        forecast=sum(estimates.values());forecasts.append(dict(natural=n,C_subset=cn,diagnostic_each=dp,repeat_cases=8,jobs=len(jobs),by_model=estimates,total_no_cache_upper_output_forecast_cny=forecast))
        if forecast<=17.5:break
    else:raise RuntimeError('No representative full-candidate design fits budget; no calls')
    c.putl(c.PRIVATE/'sample.jsonl',sample);c.putl(c.PRIVATE/'jobs.jsonl',jobs)
    public=[{k:v for k,v in r.items() if k not in ['claim','O','C']}|dict(claim_sha256=c.digest(r['claim']),O_sha256=c.digest(r['O']),C_sha256=c.digest(r['C']),O_chars=len(r['O']),C_chars=len(r['C'])) for r in sample]
    c.putl(c.OUT/'cohort.jsonl',public)
    c.put(c.OUT/'budget_plan.json',dict(utc=c.utc(),hard_cap_cny=20,prior099_cost_cny=0,operating_cap_cny=19,forecasts=forecasts,chosen=forecasts[-1],
          remaining_to_hard_cap_cny=20-forecast,input_tokens_per_character_envelope=.4,framing_tokens=256,maximum_thinking=c.THINKING,maximum_answer=c.ANSWER,
          usage_source='097 concise native mean O7482/C2975 input; mean output460/441, prediction-free usage only',
          per_attempt_hard_reservation='UTF8 bytes+2048, conservative tier, thinking+answer+32',
          prices=c.PRICES,source='https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices',no_peak_wait=True))
    # Balanced fixed subsequent bridge panel, selected now without model outputs.
    bridge=[]
    for lab in c.LABELS:
        pp=sorted([r for r in sample if r['GT']==lab],key=lambda r:c.digest('099/A800bridge/v1/'+r['id']))
        seen=set()
        for r in pp:
            if r['sid'] in seen:continue
            bridge.append(dict(id=r['id'],sid=r['sid'],GT=r['GT'],context='O',input_sha256=c.digest(r['O']),claim_sha256=c.digest(r['claim'])));seen.add(r['sid'])
            if sum(x['GT']==lab for x in bridge)==8:break
        assert sum(x['GT']==lab for x in bridge)==8
    c.putl(c.OUT/'future_A800_bridge24.jsonl',bridge)
    paths=[c.TASK/x for x in ['common099.py','protocol.md','prepare099.py','runtime099.py']]
    paths += [c.PRIVATE/'jobs.jsonl',c.PRIVATE/'sample.jsonl',c.OUT/'cohort.jsonl',c.OUT/'model_metadata.json',c.OUT/'official_source_manifest.json',c.OUT/'budget_plan.json',c.OUT/'future_A800_bridge24.jsonl',c.ROOT/'tasks/097_native_judge_source_dependence/prepare_a.py']
    c.put(c.OUT/'execution_freeze.json',dict(utc=c.utc(),start_main='742f05ed4c3bb801ce37856ba36a038c3b4269d7',files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},
          chosen=forecasts[-1],natural_GT=dict(Counter(r['GT'] for r in natural)),natural_author=dict(Counter(r['author'] for r in natural)),
          patients=len({r['sid'] for r in sample}),natural_patients=len({r['sid'] for r in natural}),all_patients_previously_exposed=True,
          first_four_request_ids=[j['request_id'] for j in jobs[:4]],no_target_answers_before_freeze=True,
          unchanged_098_fingerprints={str(p.relative_to(c.ROOT)):c.sha(p) for p in [c.ROOT/'outputs/098_p90_native_confirmation/execution_freeze.json',c.ROOT/'.local_models/098_p90_native_confirmation/jobs.jsonl',c.ROOT/'.local_models/098_p90_native_confirmation/sample.jsonl',c.ROOT/'tasks/098_p90_native_confirmation/runtime098.py',c.ROOT/'tasks/098_p90_native_confirmation/protocol.md']},
          unchanged_default_files={str(p.relative_to(c.ROOT)):c.sha(p) for p in [c.ROOT/'src/verifact_research/inference/aliyun.py',c.ROOT/'.env.aliyun']},
          original_source_files={str(p.relative_to(c.ROOT)):c.sha(p) for p in [c.ROOT/'outputs/097_native_judge_source_dependence/a_execution_panel.jsonl',c.ROOT/'outputs/097_native_judge_source_dependence/a_same_id.jsonl',c.ROOT/'outputs/096_r1_native_priorg/main_panel.jsonl',c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl',c.ROOT/'.local_models/092/inputs.jsonl']}))
    print(c.canonical(dict(chosen=forecasts[-1],GT=dict(Counter(r['GT'] for r in natural)),patients=len({r['sid'] for r in sample}))))

if __name__=='__main__':main()
