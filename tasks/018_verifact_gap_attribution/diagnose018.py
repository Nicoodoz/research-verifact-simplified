"""Validate executor observations against exact text and preserve unknown coverage."""
from collections import Counter
from pathlib import Path
import argparse,re
import common018 as c

def load_notes():
    notes=[n for p in sorted(c.TASK.glob('notes_batch*.json')) for n in c.read(p)]
    c.require(len(notes)==len({n['case_id'] for n in notes}),'Duplicate diagnosis')
    mats={m['row']['case_id']:m for m in c.jsonlines(c.OUT/'preparation_001/materials.jsonl')}
    pages=c.read(c.OUT/'review_001/page_index.json');checks=[]
    for n in notes:
        m=mats[n['case_id']]
        expected={p['page'] for p in pages if p['case_id']==n['case_id']}
        c.require(set(n['read_pages'])==expected,'Full case pages not accounted for: '+n['case_id'])
        for a in n['anchors']:
            if a.get('kind')=='output':
                text=m['outputs']['O'][a.get('field','reasoning_final_answer')] if a['arm']=='O' else m['outputs'][a['arm']]['output_text']
                base=0
            else:
                b=next(b for b in c.blocks(m['references'][a['arm']]) if b['number']==a['block']);text=b['raw_block'];base=b['start']
            hits=[(base+x.start(),base+x.end()) for x in re.finditer(re.escape(a['quote']),text)]
            checks.append(dict(case_id=n['case_id'],anchor=a,positions=hits,found=bool(hits)))
    return notes,mats,checks

def build(out):
    notes,mats,checks=load_notes();bad=[a for a in checks if not a['found']]
    c.require(not bad,'Missing literal anchors: '+c.canonical(bad))
    c.require(not out.exists(),'Diagnosis exists')
    bycase={n['case_id']:n for n in notes};ledger=[]
    for m in mats.values():
        r=m['row'];n=bycase.get(r['case_id'])
        ledger.append(dict(r,semantic_status='full_selected_materials_read_executor_not_gold' if n else 'unknown_not_fully_deep_read_018',
            mechanism=n['layer'] if n else 'unknown',mechanisms=n['mechanisms'] if n else [],confidence=n['confidence'] if n else 'unknown',
            diagnosis='cases/'+r['case_id']+'.md' if n else ''))
    out.mkdir(parents=True);(out/'cases').mkdir()
    for n in notes:
        r=mats[n['case_id']]['row'];nn=dict(n,proposition_id=r['proposition_id'],cohort=r['cohort'],subject_id=r['subject_id'],author=r['author_type'],human_gt=r['human_gt'],bucket=r['bucket'])
        anchors=[a for a in checks if a['case_id']==n['case_id']]
        text=f"# {n['case_id']}\n\n{r['text']}\n\nGT={r['human_gt']}；O={r['O']}；C={r['C']}；V={r.get('V','未运行')}；{r['bucket']}。\n\n执行者诊断，不是医学gold。\n\n## 观察\n\n{n['observation']}\n\n## 限制\n\n{n['uncertainty']}\n\n层级：{n['layer']}；机制：{', '.join(n['mechanisms'])}；把握：{n['confidence']}。\n\n## 字面锚点\n\n```json\n{c.canonical(anchors)}\n```\n\n完整材料保留在preparation_001/materials.jsonl；阅读页号{n['read_pages']}，完整reference块按相同患者及原metadata严格去重，依赖映射见review_001/case_index.json。\n"
        (out/'cases'/(n['case_id']+'.md')).write_text(text,encoding='utf-8',newline='\n')
    c.write_lines(out/'ledger.jsonl',ledger);c.write_json(out/'diagnoses.json',notes);c.write_json(out/'anchors.json',checks)
    counts=[]
    for q in ('010','016'):
        for bucket in c.BUCKETS:
            rr=[r for r in ledger if r['cohort']==q and r['bucket']==bucket];seen=[r for r in rr if r['case_id'] in bycase]
            counts.append(dict(cohort=q,bucket=bucket,total=len(rr),full_deep_read=len(seen),unknown_not_fully_read=len(rr)-len(seen),layers=dict(Counter(r['mechanism'] for r in seen))))
    c.write_json(out/'summary.json',dict(cases=len(notes),literal_anchors=len(checks),coverage=counts,purposeful_sample_not_population_causal_fractions=True,not_medical_gold=True))
    c.seal(out,[c.OUT/'preparation_001/manifest.json',c.OUT/'review_001/manifest.json']+sorted(c.TASK.glob('notes_batch*.json')),[Path(__file__)])
    print(c.canonical(c.read(out/'summary.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:
        notes,_,checks=load_notes();print(c.canonical(dict(notes=len(notes),bad=[a for a in checks if not a['found']])))
    else:build(c.OUT/'diagnosis_001')
