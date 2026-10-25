"""Independent counts and release-material bindings; no018 analysis imports."""
from pathlib import Path
from collections import Counter
import json,csv,hashlib,sys,duckdb,pandas as pd
ROOT=Path.cwd();O=ROOT/'outputs/018_verifact_gap_attribution';RAW=ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact'
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
ledger=jl(O/'preparation_001/ledger.jsonl');mats=jl(O/'preparation_001/materials.jsonl')
assert len(ledger)==len({x['proposition_id'] for x in ledger})==1251
assert {x['row']['proposition_id'] for x in mats}=={x['proposition_id'] for x in ledger}
with duckdb.connect() as db:
 db.register('wanted',pd.DataFrame({'proposition_id':[r['proposition_id'] for r in ledger]}))
 orig=db.execute('SELECT v.proposition_id,v.verdict,v.model,v.reference_id,v.reason,v.reasoning_chain,v.reasoning_final_answer FROM read_parquet(?) v JOIN wanted USING(proposition_id) WHERE rater_alias=?',[str(RAW/'verdicts.parquet'),'v1.1.0-rater-121']).fetchall()
 assert len(orig)==1251
 byid={r[0]:r for r in orig}
 db.register('wanted_refs',pd.DataFrame({'reference_id':sorted({r[3] for r in orig})}))
 refs=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN wanted_refs USING(reference_id)',[str(RAW/'reference_payloads.parquet')]).fetchall())
 for m in mats:
  r=m['row'];v=byid[r['proposition_id']]
  assert r['O']==v[1] and v[2]=='R1-70B' and r['reference_id']==v[3]
  assert m['references']['O']==refs[v[3]]
  assert tuple(m['outputs']['O'][k] for k in ['reason','reasoning_chain','reasoning_final_answer'])==v[4:]
def bucket(a,b,g):return 'both_correct' if a==b==g else 'O_only' if a==g else 'C_only' if b==g else 'both_wrong'
summary={}
for q in ['010','016','pooled']:
 rr=[r for r in ledger if q=='pooled' or r['cohort']==q]
 counter=Counter(bucket(r['O'],r['C'],r['human_gt']) for r in rr)
 assert all(r['bucket']==bucket(r['O'],r['C'],r['human_gt']) for r in rr)
 correct={s:sum(r[s]==r['human_gt'] for r in rr) for s in ['O','C']}
 false={s:sum(r[s]=='Supported' and r['human_gt']!='Supported' for r in rr) for s in ['O','C']}
 net={g:sum((r['O']==g)-(r['C']==g) for r in rr if r['human_gt']==g) for g in ['Supported','Not Supported','Not Addressed']}
 summary[q]=dict(n=len(rr),buckets=counter,correct=correct,false_S=false,net_by_GT=net)
assert summary['pooled']['buckets']==dict(O_only=156,C_only=84,both_wrong=123,both_correct=888)
assert summary['pooled']['false_S']==dict(O=79,C=27)
rr=[r for r in ledger if r['cohort']=='010']
ovc={s:sum(r[s]==r['human_gt'] for r in rr) for s in ['O','V','C']}
bridge=dict(correct=ovc,O_minus_C=ovc['O']-ovc['C'],O_minus_V=ovc['O']-ovc['V'],V_minus_C=ovc['V']-ovc['C'],
 reference_rescue=sum(r['V']==r['human_gt'] and r['C']!=r['human_gt'] for r in rr),reference_harm=sum(r['C']==r['human_gt'] and r['V']!=r['human_gt'] for r in rr))
assert ovc==dict(O=555,V=511,C=526)
rr=[r for r in ledger if r['cohort']=='016'];sensitivity=Counter(bucket(r['O'],r['Q'],r['human_gt']) for r in rr)
assert sensitivity==dict(O_only=80,C_only=48,both_wrong=64,both_correct=409)
notes=[n for p in sorted((ROOT/'tasks/018_verifact_gap_attribution').glob('notes_batch*.json')) for n in read(p)]
selected={n['case_id'] for n in notes};assert len(selected)==len(notes)==78
directional=[r for r in ledger if r['bucket'] in ('O_only','C_only')]
coverage=dict(total_directional=len(directional),recorded_deep_read=sum(r['case_id'] in selected for r in directional),unknown=sum(r['case_id'] not in selected for r in directional))
assert coverage==dict(total_directional=240,recorded_deep_read=54,unknown=186)
# Check every clinical block binding against the source parser in a separate replay;
# raw original references and complete output strings above are independent of it.
result=dict(status='PASS',original_raw_predictions_references_and_full_outputs_bound=len(mats),cohort_results=summary,bridge010=bridge,Q_sensitivity016=sensitivity,coverage=coverage,
 no_new_metric_implementation=True,full_case_semantic_auditor_sample=['010_old6_N180','016_recent6_S522','016_recent6_S599'],
 sample_scope='Full claim, both full references and all full saved clinical outputs; no medical relabeling or prevalence inference.',new_API_calls=0)
Path(sys.argv[1]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
