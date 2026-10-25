"""Create full, traceable post-hoc case packets; generation is not semantic review."""
from collections import defaultdict
import argparse,csv,json
import common019 as c
import analysis019 as a

def packets(stage):
    rows=a.read_cohort(stage);folder=c.OUT/stage/'analysis_001';tables={}
    for rep in (range(2) if stage=='validation' else range(1)):
        with (folder/f'predictions_r{rep}.csv').open(encoding='utf-8-sig',newline='') as f:tables[rep]={r['proposition_id']:r for r in csv.DictReader(f)}
    gate=c.read(c.OUT/'selection_freeze.json');lam=gate['selected_lambda'] if gate['selected_lambda'] is not None else 0
    candidate=a.name(lam);samples=[]
    for sid in sorted({r['subject_id'] for r in rows}):
        groups=defaultdict(list)
        for r in rows:
            if r['subject_id']!=sid:continue
            pid=r['proposition_id'];gt=r['human_gt'];bb=[t[pid]['B'] for t in tables.values()];uu=[t[pid][candidate] for t in tables.values()]
            rescue=gt=='Supported' and len(set(bb))==1 and bb[0]!='Supported' and all(x=='Supported' for x in uu)
            new_false=gt!='Supported' and any(b!='Supported' and u=='Supported' for b,u in zip(bb,uu))
            missed=gt=='Supported' and all(b!='Supported' and u!='Supported' for b,u in zip(bb,uu))
            correct=all(b==u==gt for b,u in zip(bb,uu))
            group='rescue' if rescue else 'new_falseS' if new_false else 'unrescued' if missed else 'correct_control' if correct else None
            if group:groups[group].append(r)
        for group,rs in groups.items():
            r=min(rs,key=lambda r:c.rank('case/'+r['proposition_id']));samples.append(dict(group=group,**r))
    inputs={r['proposition_id']:r for r in c.jsonlines(c.OUT/stage/'preparation/inputs.jsonl')}
    native={r['request_id']:r for r in c.jsonlines(folder/'normalized.jsonl')}
    with (c.OUT/stage/'preparation/assignments.csv').open(encoding='utf-8-sig',newline='') as f:assignments=list(csv.DictReader(f))
    results={(r['proposition_id'],r['arm'],int(r['repeat'])):native[r['request_id']] for r in assignments}
    out=c.OUT/'case_packets';out.mkdir(exist_ok=False);index=[]
    for r in samples:
        pid=r['proposition_id']
        text=['# '+r['case_id'],'',f"Sampling group: {r['group']}. GT visible; post-hoc diagnosis, not medical adjudication.",
            'Packet generation is NOT semantic reading. Selection-stage cases have one call per arm, not a stability result.',
            'Postprocessing does not generate a new explanation. The raw reason may disagree with the adjusted label.','',
            '## Claim',inputs[pid]['text'],'','## Complete C48 reference',inputs[pid]['reference']]
        for rep in tables:
            for arm in ('B','S'):
                text+=['',f'## Complete response: round {rep}, arm {arm}',results[(pid,arm,rep)]['output_text']]
        text+=['','## Label comparison',json.dumps(dict(GT=r['human_gt'],lambda_value=lam,selected_lambda_exists=gate['selected_lambda'] is not None,
            rounds={rep:{k:tables[rep][pid][k] for k in ('B','V_raw','U0',candidate)} for rep in tables}),ensure_ascii=False)]
        filename=r['case_id']+'.md';(out/filename).write_text('\n'.join(text)+'\n',encoding='utf-8')
        index.append(dict(case_id=r['case_id'],proposition_id=pid,group=r['group'],file='case_packets/'+filename,rounds=list(tables),semantic_read=False))
    c.write_json(out/'index.json',index);print('GENERATED_PACKETS_NOT_YET_READ',len(index))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['selection','validation']);args=p.parse_args();packets(args.stage)
