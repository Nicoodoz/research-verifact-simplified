"""Freeze the same train196 and label-stratified selection20 eval500; no calls."""
from collections import Counter,defaultdict
import argparse
import shutil
import common105 as c
from data105 import shared,construct_answer,training_plan

def stratified(pool,n,seed):
    if len(pool)<n:raise ValueError('Insufficient candidates; decide scale before any prediction')
    groups=defaultdict(list)
    for row in pool:groups[(row['GT'],row['author'])].append(row)
    exact={key:n*len(rows)/len(pool) for key,rows in groups.items()}
    quota={key:int(value) for key,value in exact.items()}
    for key in sorted(groups,key=lambda k:(-(exact[k]-quota[k]),k))[:n-sum(quota.values())]:quota[key]+=1
    chosen=[row for key,rows in groups.items() for row in sorted(rows,key=lambda r:c.digest(seed+r['id']))[:quota[key]]]
    return sorted(chosen,key=lambda r:c.digest(seed+'/order/'+r['id']))

def public(row):
    return {k:row[k] for k in ('id','sid','author','GT','panel','reference_id')}|dict(claim_sha256=c.digest(row['claim']),reference_sha256=c.digest(row['reference']),prompt_sha256=c.digest(c.canonical(shared.messages(row['claim'],row['reference']))))

def main():
    if (c.OUT/'preparation_freeze.json').exists():raise RuntimeError('Already frozen; verify instead of selecting again')
    rolepath=c.ROOT/'outputs/103_lora_selection/patient_roles.json';roles=c.read(rolepath)['patients']
    source=c.ROOT/'.local_models/104_supervision_evidence/paired';manifest=c.read(c.ROOT/'outputs/104_supervision_evidence/paired_manifest.json')
    for arm in c.ARMS[1:]:
        path=source/(arm+'.jsonl');assert c.sha(path)==manifest['files'][path.relative_to(c.ROOT).as_posix()]
        c.frozen(c.PRIVATE/'train'/(arm+'.jsonl'),path.read_bytes())
    labels=c.rows(source/'label_only.jsonl');briefs=c.rows(source/'evidence_brief.jsonl')
    shared.validate_pairs(labels,briefs,set(roles['train']),set(roles['selection'])|set(roles['confirmation']))
    assert len(labels)==196 and Counter(r['GT'] for r in labels)==dict(zip(c.LABELS,[83,62,51]))
    fields=[]
    for arm,rows in [('label_only',labels),('evidence_brief',briefs)]:
        for r in rows:
            answer,span=construct_answer(r)
            fields.append(dict(id=r['id'],arm=arm,answer_sha256=c.digest(answer),verdict_value_chars=list(span)))
    c.putl(c.PRIVATE/'answer_fields.jsonl',fields)
    # This pre-existing file contains only train40 + selection20, no confirmation
    # patients. Sampling code never branches on paper_r1 or any 103 prediction.
    eligible=c.rows(c.ROOT/'.local_models/103_lora_selection/eligible.jsonl')
    assert not {r['sid'] for r in eligible}&set(roles['confirmation'])
    pool=[r for r in eligible if r['role']=='selection']
    assert {r['sid'] for r in pool}==set(roles['selection'])
    natural=stratified(pool,400,'105/natural400/v1/')
    used={r['id'] for r in natural};selected=[]
    for r in natural:selected.append(dict(r,panel='natural'))
    for GT in c.LABELS[1:]:
        pressure=stratified([r for r in pool if r['GT']==GT and r['id'] not in used],50,'105/pressure50/v1/'+GT)
        used.update(r['id'] for r in pressure)
        selected.extend(dict(r,panel='pressure') for r in pressure)
    assert len(selected)==len({r['id'] for r in selected})==500
    assert not {r['sid'] for r in selected}&{r['sid'] for r in labels}
    inputs=[{k:r[k] for k in ('id','sid','author','claim','reference','reference_id','panel')} for r in selected]
    c.putl(c.PRIVATE/'eval_inputs.jsonl',inputs)
    keys=[{k:r[k] for k in ('id','sid','author','GT','panel','paper_r1')} for r in selected]
    c.putl(c.OUT/'eval_keys.jsonl',keys)
    c.putl(c.OUT/'eval_manifest.jsonl',[public(r) for r in selected])
    c.putl(c.OUT/'train_manifest.jsonl',[dict(id=r['id'],sid=r['sid'],author=r['author'],GT=r['GT'],claim_sha256=c.digest(r['claim']),reference_sha256=r['reference_sha256'],
                                           label_answer_sha256=c.digest(r['answer']),brief_answer_sha256=c.digest(b['answer']),prompt_sha256=c.digest(c.canonical(shared.messages(r['claim'],r['reference'])))) for r,b in zip(labels,briefs)])
    plan=training_plan([r['id'] for r in labels]);assert len(plan)==50 and plan[-1]['consumed']==392
    c.put(c.OUT/'training_plan.json',dict(seed=103027,order='frozen104_original_order_repeated_each_epoch',epochs=2,steps_per_epoch=25,total_optimizer_steps=len(plan),committed_samples=392,steps=plan))
    old103={r['id'] for r in c.rows(c.ROOT/'outputs/103_lora_selection/cohort240.jsonl') if r['local180']}
    c.put(c.OUT/'sample_summary.json',dict(train=dict(N=196,GT=dict(Counter(r['GT'] for r in labels)),patients=40),
        eval_pool=dict(N=len(pool),GT=dict(Counter(r['GT'] for r in pool)),patients=20),
        panels={p:dict(N=sum(r['panel']==p for r in selected),GT=dict(Counter(r['GT'] for r in selected if r['panel']==p)),author=dict(Counter(r['author'] for r in selected if r['panel']==p)),patients=len({r['sid'] for r in selected if r['panel']==p})) for p in ('natural','pressure')},
        overlaps_103_selection180=sum(r['id'] in old103 for r in selected),
        train_eval_patient_overlap=0,panel_ID_overlap=0,confirmation_clinical_data_read=False,
        all_patients_historically_exposed=True,not_new_holdout=True,selection_not_by_103_correctness_or_104_explainability=True))
    c.put(c.PRIVATE/'source_fingerprints.json',dict(patient_roles=c.sha(rolepath),original104_manifest=c.sha(c.ROOT/'outputs/104_supervision_evidence/paired_manifest.json'),eligible_source=c.sha(c.ROOT/'.local_models/103_lora_selection/eligible.jsonl')))
    print(c.canonical(c.read(c.OUT/'sample_summary.json')))

if __name__=='__main__':main()
