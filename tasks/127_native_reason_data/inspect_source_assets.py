from collections import Counter
from pathlib import Path
import csv,gzip,json
import duckdb

R=Path(__file__).resolve().parents[2]
P=R/'.local_models/127_native_reason_data'
D=R/'data/00_raw/verifact-bhc/1.1.0'
def csvrows(name):
    with gzip.open(D/'propositions'/name,'rt',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def rows(path):return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines()]
def put(name,value):
    (P/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def nonempty(x):return bool(x and x.strip() and x.strip().lower() not in ('nan','none','null'))

props=csvrows('propositions.csv.gz');doctors=csvrows('human_verdicts.csv.gz')
pool=rows(R/'.local_models/106_label_preparation/training_pool.jsonl');ids={r['id'] for r in pool}
comments=[f'comment{i}' for i in range(1,6)]+['adjudicated_comment']
def counts(values):
    return dict(N=len(values),by_column={k:sum(nonempty(r[k]) for r in values) for k in comments},
        any_comment_N=sum(any(nonempty(r[k]) for k in comments) for r in values),
        total_nonempty_comments=sum(nonempty(r[k]) for r in values for k in comments),
        comments_at_least20_chars=sum(len(r[k].strip())>=20 for r in values for k in comments),
        comments_at_least60_chars=sum(len(r[k].strip())>=60 for r in values for k in comments))
train_doctors=[r for r in doctors if r['proposition_id'] in ids]
assert len(train_doctors)==3675
provenance=dict(local_version='1.1.0',human_columns=list(doctors[0]),proposition_columns=list(props[0]),
    all_propositions=counts(doctors),train40_valid_atomic=counts(train_doctors),
    natural_text=dict(propositions_N=len(props),by_author=dict(Counter(r['author_type'] for r in props)),
        source_BHC_present=sum(nonempty(r['brief_hospital_course']) for r in props),
        unique_BHC_by_author={a:len({r['brief_hospital_course'] for r in props if r['author_type']==a})
            for a in sorted({r['author_type'] for r in props})}),
    no_clinical_body_published=True)
pilot=rows(P/'pilot24_inputs.jsonl');review={r['id']:r for r in rows(P/'pilot24_reviewed.jsonl')}
doctor_by={r['proposition_id']:r for r in train_doctors}
with duckdb.connect() as db:
    db.execute('create table wanted(id varchar)')
    db.executemany('insert into wanted values (?)',[(r['id'],) for r in pilot])
    query=db.execute('select v.proposition_id,v.model,v.rater_alias,v.verdict,v.reason,v.reference_id,length(v.reasoning_chain),length(v.reasoning_final_answer) from read_parquet(?) v join wanted w on w.id=v.proposition_id where v.rater_alias=?',
        [str(D/'verifact/verdicts.parquet'),'v1.1.0-rater-121'])
    names=['id','model','rater_alias','verdict','reason','reference_id','reasoning_chain_chars','reasoning_final_answer_chars']
    original={v[0]:dict(zip(names,v)) for v in query.fetchall()}
assert len(original)==24
samples=[]
for p in pilot:
    src=original[p['id']];d=doctor_by[p['id']]
    assert src['reference_id']==p['reference_sha256']
    samples.append(dict(id=p['id'],GT=p['GT'],fit_role=p['fit_role'],claim=p['claim'],
        original_AI=src,doctor_comments={k:d[k] for k in comments if nonempty(d[k])},
        doctor_votes={k:d[k] for k in ['verdict1','verdict2','verdict3','verdict4','verdict5','human_gt']},
        newly_reviewed_reason_status=review[p['id']]['review']['status']))
(P/'original_reason_probe24.jsonl').write_bytes(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in samples).encode())
examples=sorted([r for r in train_doctors if any(nonempty(r[k]) for k in comments)],key=lambda r:(-max(len(r[k]) for k in comments),r['proposition_id']))[:12]
(P/'doctor_comment_examples12.jsonl').write_bytes(''.join(json.dumps(dict(id=r['proposition_id'],GT=r['human_gt'],comments={k:r[k] for k in comments if nonempty(r[k])}),ensure_ascii=False)+'\n' for r in examples).encode())
provenance['pilot24_original_R1']=dict(N=24,same_reference_N=24,reason_present=sum(nonempty(x['reason']) for x in original.values()),
    verdict_matches_GT=sum(original[p['id']]['verdict']==p['GT'] for p in pilot),
    mismatch_not_automatically_bad_reason=True,pilot_is_boundary_enriched_not_representative=True)
comment_rows=[r for r in train_doctors if any(nonempty(r[k]) for k in comments)]
source_by_id={r['id']:r for r in pool}
split=json.loads((R/'.local_models/116_research_cycle/data_split.json').read_text(encoding='utf-8-sig'))
gradient=set(map(str,split['gradient_patients']))
comment_index=[dict(id=r['proposition_id'],GT=r['human_gt'],sid=source_by_id[r['proposition_id']]['sid'],
    fit_role='train' if str(source_by_id[r['proposition_id']]['sid']) in gradient else 'validation',
    doctor_comments={k:r[k] for k in comments if nonempty(r[k])},
    original_reference_id=source_by_id[r['proposition_id']]['reference_id'],
    comments_are_not_automatically_grounded_in_this_reference=True) for r in comment_rows]
(P/'doctor_comment_index111.jsonl').write_bytes(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in comment_index).encode())
provenance['train_doctor_comment_index']=dict(N=len(comment_index),
    by_GT=dict(Counter(r['GT'] for r in comment_index)),
    by_role_GT=dict(Counter(r['fit_role']+'/'+r['GT'] for r in comment_index)),
    pilot24_with_any_comment=sum(bool(r['doctor_comments']) for r in samples),
    private_index='.local_models/127_native_reason_data/doctor_comment_index111.jsonl')
put('original_asset_inventory.json',provenance)
print(json.dumps(provenance,ensure_ascii=False))
