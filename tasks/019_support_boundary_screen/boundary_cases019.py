"""Descriptive-only case selection after a failed gate; no new inference."""
from collections import defaultdict
import csv
import json
import common019 as c
import analysis019 as a

def make():
    gate=c.read(c.OUT/'selection_freeze.json')
    c.require(not gate['passed'] and gate['selected_lambda'] is None, 'This diagnostic is for the failed screen')
    out=c.OUT/'boundary_cases_001';out.mkdir(exist_ok=False)
    registration=dict(created_utc=c.now(),post_hoc=True,performance_grid_already_seen=True,
        illustrative_lambda=1.5,not_a_selected_winner=True,no_gate_changes=True,
        reason='Explain both increased correct counts and harm at one intermediate registered grid point',
        selection='One fixed-hash case per author and outcome category R/H/W/unrescued/correct-control; plus one B-correct-NS to U0-nonNS per author',
        no_new_API=True,not_new_medical_gold=True,semantic_read=False)
    c.write_json(out/'registration.json',registration)
    rows=a.read_cohort('selection')
    with (c.OUT/'selection/analysis_001/predictions_r0.csv').open(encoding='utf-8-sig',newline='') as f:
        preds={r['proposition_id']:r for r in csv.DictReader(f)}
    groups=defaultdict(list);arm='U_lambda_1.5'
    for r in rows:
        p=preds[r['proposition_id']];gt=r['human_gt'];u=p['U0'];v=p[arm]
        changed=u!='Supported' and v=='Supported'
        category=('R' if gt=='Supported' else 'H' if gt==u else 'W') if changed else None
        if category is None and gt=='Supported' and p['B']!='Supported' and v!='Supported': category='unrescued'
        if category is None and p['B']==u==v==gt: category='correct_control'
        if category: groups[(r['author_type'],category)].append(r)
        if gt==p['B']=='Not Supported' and u!='Not Supported':
            groups[(r['author_type'],'score_NS_loss')].append(r)
    selection={}
    for key,values in sorted(groups.items()):
        r=min(values,key=lambda z:c.rank('boundary_case/'+z['proposition_id']))
        record=selection.setdefault(r['proposition_id'],dict(row=r,groups=[]))
        record['groups'].append('/'.join(key))
    inputs={r['proposition_id']:r for r in c.jsonlines(c.OUT/'selection/preparation/inputs.jsonl')}
    norm={r['request_id']:r for r in c.jsonlines(c.OUT/'selection/analysis_001/normalized.jsonl')}
    with (c.OUT/'selection/preparation/assignments.csv').open(encoding='utf-8-sig',newline='') as f:
        assignments=list(csv.DictReader(f))
    answers={(r['proposition_id'],r['arm']):norm[r['request_id']] for r in assignments}
    index=[]
    for pid,record in selection.items():
        r=record['row'];p=preds[pid];x=inputs[pid]
        text=['# '+r['case_id'],'','Post-hoc illustration at lambda=1.5; no selected winner; single draw only.',
              'Groups: '+', '.join(record['groups']),json.dumps(p,ensure_ascii=False),'',
              '## Original claim',x['text'],'','## Complete unchanged C48 reference',x['reference']]
        for armname in ('B','S'):
            text+=['','## Complete '+armname+' output',answers[(pid,armname)]['output_text']]
        path=out/(r['case_id']+'.md');path.write_text('\n'.join(text)+'\n',encoding='utf-8')
        index.append(dict(case_id=r['case_id'],proposition_id=pid,author=r['author_type'],
            groups=record['groups'],file=path.relative_to(c.OUT).as_posix(),sha256=c.file_hash(path),semantic_read=False))
    c.write_json(out/'index.json',index)
    print(c.canonical(dict(generated_not_read=len(index),cases=index)),flush=True)

if __name__=='__main__':
    make()
