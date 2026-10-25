"""Freeze two separate panels after construction; natural selection never uses GT."""
import collections, statistics
from common089 import *
import api089 as api
sys.path.insert(0,str(ROOT/'tasks/087_f4_evidence_intervention'))
from analyze087 import load_gt

def main():
    df=read(OUT/'demonstration_freeze.json')
    for rel,d in df['files'].items():assert sha(OUT/rel)==d
    systems=read(OUT/'templates.json')['systems'];assert len(set(systems.values()))>1,'all inputs identical: do not simulate experiment'
    evalp=set(read(ROOT/'outputs/079_f4_priorg_adaptation/freeze.json')['eval_patients'])
    priorp=set(read(ROOT/'outputs/051_thinking_mode_validation/freeze.json')['patient_pool'])
    demo=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl');assert not evalp&(priorp|{x['sid'] for x in demo})
    teach=set(read(ROOT/'outputs/071_judge_icl_feasibility/freeze.json')['training_patients'])
    sources={}
    def source(rel):sources[rel]=sha(ROOT/rel);return lines(ROOT/rel)
    broad=[x for x in source('outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl') if x['subject_id'] in evalp]
    clean={x['id'] for x in source('outputs/084_f4_coverage_validation/eligible_blind.jsonl')}
    exposed=collections.defaultdict(list)
    for rel in ('outputs/084_f4_coverage_validation/sample_blind.jsonl','outputs/086_global_demonstration_selection/E_cases_blind.jsonl','outputs/087_f4_evidence_intervention/sample_blind.jsonl'):
        for x in source(rel):exposed[x.get('id',x.get('proposition_id'))].append(rel)
    rows=[]
    for x in broad:
        pid=x['proposition_id'];sid=x['subject_id']
        rows.append(dict(id=pid,sid=sid,author=x['author_type'],claim=x['text'],reference=x['reference'],reference_sha256=h(x['reference']),fallback_U2=LABELS[x['u2']],
            selection_tier=0 if pid in clean and not exposed[pid] else 1 if not exposed[pid] else 2,prior_recent_exposure=exposed[pid],
            teaching_candidate_patient_overlap=sid in teach))
    # Freeze GT-blind per-patient natural ordering before any label read. Counts chosen only using cost, not label composition.
    order={s:sorted([x for x in rows if x['sid']==s],key=lambda x:(x['selection_tier'],h('089/natural/'+x['id']))) for s in sorted(evalp)}
    put(OUT/'natural_order_blind.json',dict(created_utc=now(),orders={s:[x['id'] for x in z] for s,z in order.items()},GT_used=False))
    template=next(x['body'] for x in lines(ROOT/'outputs/087_f4_evidence_intervention/jobs.jsonl') if x['arm']=='F4')
    oldcost=read(ROOT/'outputs/087_f4_evidence_intervention/cost_ledger.json')['arms']
    oldjobs=lines(ROOT/'outputs/087_f4_evidence_intervention/jobs.jsonl')
    oldbytes=statistics.mean(len(canonical(x['body']).encode()) for x in oldjobs if x['arm']=='F4')
    ratio=oldcost['F4']['prompt_distribution']['mean']/oldbytes
    output_mean=max(oldcost[a]['completion_distribution']['mean'] for a in oldcost)
    used=sum(x['cost_or_unknown_cny'] for x in api.state()[0]);forecasts=[];chosen=None
    unique_arms=[]
    for a in ARMS:
        if systems[a] not in [systems[b] for b in unique_arms]:unique_arms.append(a)
    # Conservative pressure forecast uses maximum target payload size; no labels needed for size decision.
    for n in (5,4):
        natural=[{**x,'panel':'natural'} for s in sorted(evalp) for x in order[s][:n]]
        costs=[]
        for a in unique_arms:
            nat=sum((len(canonical(make_body(template,systems[a],x['claim'],x['reference'])).encode())*ratio*3+output_mean*9)/1e6 for x in natural)
            worst=max((len(canonical(make_body(template,systems[a],x['claim'],x['reference'])).encode())*ratio*3+output_mean*9)/1e6 for x in rows)
            costs.append(dict(arm=a,natural_cny=nat,pressure_44_upper_length_forecast=44*worst))
        total=used+sum(x['natural_cny']+x['pressure_44_upper_length_forecast'] for x in costs)
        forecasts.append(dict(natural_n=22*n,pressure_n=44,total_cny=total,arms=costs))
        if total<=17:chosen=(n,natural,total);break
    assert chosen,'Complete 88+44 cohort forecast exceeds planned envelope; do not silently shrink'
    n,natural,total=chosen;putl(OUT/'natural_blind.jsonl',natural)
    ids={x['id'] for x in rows};gt,original,gtsha=load_gt(ids)
    selected={x['id'] for x in natural};pressure=[];counts=collections.Counter()
    pats=sorted(evalp,key=lambda s:h('089/pressure/patient/'+s))
    for label in ('Not Supported','Not Addressed'):
        bysid={s:sorted([x for x in rows if x['sid']==s and x['id'] not in selected and gt[x['id']]['human_gt']==label],key=lambda x:(x['selection_tier'],h('089/pressure/'+x['id']))) for s in pats}
        for round_no in range(3):
            for s in pats:
                if counts[label]>=22:break
                if len(bysid[s])>round_no:
                    x=bysid[s][round_no];pressure.append({**x,'panel':'pressure'});selected.add(x['id']);counts[label]+=1
    sample=natural+pressure;putl(OUT/'pressure_blind.jsonl',pressure);putl(OUT/'sample_blind.jsonl',sample)
    put(OUT/'sampling_audit.json',dict(natural_n=len(natural),natural_selection_GT_used=False,natural_order_sha256=sha(OUT/'natural_order_blind.json'),
        pressure_n=len(pressure),pressure_label_counts=dict(counts),pressure_GT_source_sha256=gtsha,pressure_per_class_patient_cap=3,panels_disjoint=len(selected)==len(sample),
        eval_patients=sorted(evalp),prior_patients=sorted(priorp),demo_patients=sorted({x['sid'] for x in demo}),
        exposure_definition='084 eligible and recent084/086/087 inventory, not claim of never exposed; all development patients exposed'))
    jobs=[];aliases=[]
    for i,x in enumerate(sorted(sample,key=lambda x:h('089/job/'+x['id']))):
        perbody={}
        orderarms=list(ARMS[i%3:]+ARMS[:i%3])
        for a in orderarms:
            b=make_body(template,systems[a],x['claim'],x['reference']);digest=h(canonical(b))
            if digest not in perbody:
                j=api.freeze_job('main',a,x['id'],x['sid'],b);perbody[digest]=j;jobs.append(j)
            aliases.append(dict(id=x['id'],arm=a,request_id=perbody[digest]['request_id'],body_sha256=digest))
    putl(OUT/'main_jobs.jsonl',jobs);putl(OUT/'logical_aliases.jsonl',aliases)
    put(OUT/'budget.json',dict(cap=20,construction_used=used,forecasts=forecasts,selected_total_forecast=total,reserve=20-total,
        historical_output_mean=output_mean,input_tokens_per_body_UTF8_byte=ratio,price=PRICES,checked_utc=now(),
        sources=['https://help.aliyun.com/zh/model-studio/deepseek-v4-flash','https://help.aliyun.com/zh/model-studio/qwen3-5-flash']))
    sources.update({p.relative_to(ROOT).as_posix():sha(p) for p in (TASK/'prepare089.py',TASK/'protocol.md',TASK/'api089.py',TASK/'common089.py')})
    put(OUT/'main_freeze.json',dict(cap=20,created_utc=now(),physical_jobs=len(jobs),logical_jobs=len(aliases),sources=sources,
        files={name:sha(OUT/name) for name in ('main_jobs.jsonl','logical_aliases.jsonl','sample_blind.jsonl','natural_blind.jsonl','pressure_blind.jsonl','templates.json','demonstration_freeze.json','budget.json','sampling_audit.json')}))
    print(canonical(dict(natural=len(natural),pressure=len(pressure),jobs=len(jobs),forecast=total,reserve=20-total)))
if __name__=='__main__':main()
