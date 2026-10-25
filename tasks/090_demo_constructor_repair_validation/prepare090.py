"""Freeze complete contemporaneous panels without performance-based sampling."""
import collections,statistics,subprocess
from common090 import *
import api090 as api
sys.path.insert(0,str(ROOT/'tasks/087_f4_evidence_intervention'))
from analyze087 import load_gt

def main():
    method=OUT/'final';df=read(method/'demonstration_freeze.json')
    for rel,d in df['files'].items():assert sha(method/rel)==d
    t=read(method/'templates.json');systems=t['systems'];arms=t['active_arms'];sources={}
    def source(rel):sources[rel]=sha(ROOT/rel);return lines(ROOT/rel)
    evalp=set(read(ROOT/'outputs/079_f4_priorg_adaptation/freeze.json')['eval_patients']);priorp=set(read(ROOT/'outputs/051_thinking_mode_validation/freeze.json')['patient_pool'])
    demo=source('outputs/071_judge_icl_feasibility/examples.jsonl');D=source('outputs/086_global_demonstration_selection/candidate_pool.jsonl')
    assert not evalp&(priorp|{x['sid'] for x in demo}|{x['sid'] for x in D})
    teach=set(read(ROOT/'outputs/071_judge_icl_feasibility/freeze.json')['training_patients'])
    broad=[x for x in source('outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl') if x['subject_id'] in evalp];assert len(broad)==2034
    clean={x['id'] for x in source('outputs/084_f4_coverage_validation/eligible_blind.jsonl')};exposed=collections.defaultdict(list)
    paths=['outputs/084_f4_coverage_validation/sample_blind.jsonl','outputs/086_global_demonstration_selection/E_cases_blind.jsonl',
        'outputs/087_f4_evidence_intervention/sample_blind.jsonl','outputs/089_source_audited_demo_compression/sample_blind.jsonl',
        'outputs/066_oracle_headroom/error_cases.jsonl','outputs/067_conservative_evidence_packing/cases_blind.jsonl',
        'outputs/067_conservative_evidence_packing/cases_blind_v2.jsonl','outputs/068_final_pack_utility_diagnosis/diagnostic_cases.jsonl',
        'outputs/068_final_pack_utility_diagnosis/diagnostic_v2_cases.jsonl','outputs/069_final_pack_controlled_repair/stage1_final_cases.jsonl',
        'outputs/070_fixed_evidence_reasoning_diagnosis/all_cases.jsonl','outputs/081_gt_blind_evidence_selection/sample_blind.jsonl']
    for rel in paths:
        if (ROOT/rel).exists():
            for x in source(rel):
                pid=x.get('id',x.get('proposition_id'))
                if pid:exposed[pid].append(rel)
    reserved085={x['id'] for x in source('outputs/085_r1_70b_model_swap/frozen_cohort_manifest.jsonl')}
    rows=[]
    for x in broad:
        pid=x['proposition_id'];sid=x['subject_id'];tier=3 if pid in reserved085 else 2 if exposed[pid] else 0 if pid in clean else 1
        rows.append(dict(id=pid,sid=sid,author=x['author_type'],claim=x['text'],reference=x['reference'],reference_sha256=h(x['reference']),fallback_U2=LABELS[x['u2']],
            selection_tier=tier,prior_target_exposure=exposed[pid],in_frozen085=pid in reserved085,teaching_candidate_patient_overlap=sid in teach))
    orders={s:sorted([x for x in rows if x['sid']==s],key=lambda x:(x['selection_tier'],h('090/natural/'+x['id']))) for s in sorted(evalp)}
    put(PUB/'natural_order_blind.json',dict(created_utc=now(),GT_used=False,orders={s:[x['id'] for x in z] for s,z in orders.items()}))
    template=next(x['body'] for x in source('outputs/087_f4_evidence_intervention/jobs.jsonl') if x['arm']=='F4')
    assert template['model']==MODEL and template['max_tokens']==8192 and template['temperature']==0
    oldcost=read(ROOT/'outputs/087_f4_evidence_intervention/cost_ledger.json')['arms'];oldjobs=lines(ROOT/'outputs/087_f4_evidence_intervention/jobs.jsonl')
    ratios={a:oldcost[a]['prompt_distribution']['mean']/statistics.mean(len(canonical(x['body']).encode()) for x in oldjobs if x['arm']==a) for a in ('B','F4')}
    output_mean=max(z['completion_distribution']['mean'] for z in oldcost.values());used=sum(x['cost_or_unknown_cny'] for x in api.state()[0]);assert used<=4
    physical=[]
    for a in arms:
        if systems[a] not in [systems[b] for b in physical]:physical.append(a)
    forecasts=[];chosen=None
    for per,pressure_n in ((8,66),(6,66),(6,44)):
        natural=[{**x,'panel':'natural'} for s in sorted(evalp) for x in orders[s][:per]]
        estimates=[]
        for a in physical:
            ratio=ratios['B' if a=='B' else 'F4']
            def estimate(x):return (3*ratio*len(canonical(make_body(template,systems[a],x['claim'],x['reference'])).encode())+9*output_mean)/1e6
            nat=sum(estimate(x) for x in natural);pressure=pressure_n*max(estimate(x) for x in rows)
            estimates.append(dict(arm=a,natural_estimate=nat,pressure_upper_target_length_estimate=pressure))
        total=used+sum(v['natural_estimate']+v['pressure_upper_target_length_estimate'] for v in estimates)
        forecasts.append(dict(natural_n=per*22,pressure_n=pressure_n,total=total,arms=estimates))
        if total<=36:chosen=(natural,per,pressure_n,total);break
    assert chosen,'Cannot afford minimum complete panels within planned envelope; preserve preparation and diagnose'
    natural,per,pressure_n,total=chosen;putl(OUT/'natural_blind.jsonl',natural)
    # This is the first090 target-label read: only pressure sampling follows frozen natural selection.
    gt,original,gtsha=load_gt({x['id'] for x in rows});selected={x['id'] for x in natural};pressure=[];counts=collections.Counter()
    pats=sorted(evalp,key=lambda s:h('090/pressure/patient/'+s));target=pressure_n//2
    for lab in ('Not Supported','Not Addressed'):
        pool={s:sorted([x for x in rows if x['sid']==s and x['id'] not in selected and gt[x['id']]['human_gt']==lab],key=lambda x:(x['selection_tier'],h('090/pressure/'+x['id']))) for s in pats}
        for turn in range(3):
            for s in pats:
                if counts[lab]>=target:break
                if len(pool[s])>turn:
                    x=pool[s][turn];pressure.append({**x,'panel':'pressure'});counts[lab]+=1;selected.add(x['id'])
    sample=natural+pressure;assert len(sample)==len(selected)
    putl(OUT/'sample_blind.jsonl',sample)
    putl(PUB/'cohort_manifest.jsonl',[{k:v for k,v in x.items() if k not in ('claim','reference')}|dict(claim_sha256=h(x['claim'])) for x in sample])
    audit=dict(natural_n=len(natural),natural_per_patient=per,pressure_n=len(pressure),pressure_label_counts=dict(counts),pressure_max_per_class_patient=3,
        natural_GT_used=False,pressure_selection='labels/patient/ID only',GT_source_sha256=gtsha,panels_disjoint=True,
        eval_patients=sorted(evalp),PriorG_source_patients=sorted(priorp),D_patients=sorted({x['sid'] for x in D}),
        exposure_by_panel={panel:dict(tiers=dict(collections.Counter(x['selection_tier'] for x in sample if x['panel']==panel)),frozen085_overlap=sum(x['in_frozen085'] for x in sample if x['panel']==panel)) for panel in ('natural','pressure')},
        warning='All development patients exposed. Tier0 means not in specified oldcall/case lists, not independent unseen patients.')
    put(PUB/'sampling_audit.json',audit)
    jobs=[];aliases=[]
    # Round-robin patients and within-patient hashed IDs; rotate arm order across cases.
    bysid={s:sorted([x for x in sample if x['sid']==s],key=lambda x:h('090/job/'+x['id'])) for s in pats}
    ordered=[bysid[s][i] for i in range(max(map(len,bysid.values()))) for s in pats if i<len(bysid[s])]
    for i,x in enumerate(ordered):
        bybody={};order=arms[i%len(arms):]+arms[:i%len(arms)]
        for a in order:
            b=make_body(template,systems[a],x['claim'],x['reference']);d=h(canonical(b))
            if d not in bybody:
                j=api.freeze_job('main',a,x['id'],x['sid'],b);bybody[d]=j;jobs.append(j)
            aliases.append(dict(id=x['id'],arm=a,request_id=bybody[d]['request_id'],body_sha256=d))
    putl(OUT/'main_jobs.jsonl',jobs);putl(OUT/'logical_aliases.jsonl',aliases);putl(PUB/'logical_aliases.jsonl',aliases)
    budget=dict(cap=40,construction_cap=4,construction_actual=used,forecasts=forecasts,chosen_total_forecast=total,recovery_and_output_reserve=40-total,
        historical_output_mean=output_mean,input_ratios=ratios,prices=PRICES,price_source=['https://help.aliyun.com/zh/model-studio/deepseek-v4-flash','https://help.aliyun.com/zh/model-studio/qwen3-5-flash'],
        original_prices_last_verified_date='2026-09-26',discounts_ignored=True,max_workers=8,max_attempts=3)
    put(PUB/'budget.json',budget)
    sources.update({p.relative_to(ROOT).as_posix():sha(p) for p in (TASK/'prepare090.py',TASK/'protocol.md',TASK/'api090.py',TASK/'common090.py',TASK/'analyze090.py')})
    sources.update({(PUB/n).relative_to(ROOT).as_posix():sha(PUB/n) for n in ('final_branch.json','sampling_audit.json','budget.json')})
    put(OUT/'main_freeze.json',dict(cap=40,created_utc=now(),physical_jobs=len(jobs),logical_jobs=len(aliases),sources=sources,files={n:sha(OUT/n) for n in ('main_jobs.jsonl','sample_blind.jsonl','natural_blind.jsonl','logical_aliases.jsonl','final/templates.json','final/demonstration_freeze.json')}))
    put(PUB/'main_freeze_summary.json',dict(created_utc=now(),private_freeze_sha256=sha(OUT/'main_freeze.json'),physical_jobs=len(jobs),logical_jobs=len(aliases),
        inputs_stored_privately=OUT.relative_to(ROOT).as_posix(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sources=sources))
    print(canonical(dict(natural=len(natural),pressure=len(pressure),physical_jobs=len(jobs),logical_jobs=len(aliases),forecast=total,reserve=40-total,active_arms=arms)))
if __name__=='__main__':main()
