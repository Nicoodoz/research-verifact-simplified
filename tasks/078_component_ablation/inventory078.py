"""Read-only inventory and GT-blind cohort construction for task 078."""
import json,csv,sys,hashlib,statistics
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/078_component_ablation'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def stable(s):return hashlib.sha256(s.encode()).hexdigest()
def main():
 OUT.mkdir(exist_ok=True);by={}
 for task,folder in [('052','052_first_tier_validation'),('053','053_thinking_prior_validation')]:
  for x in lines(ROOT/'outputs'/folder/'sample_blind.jsonl'):
   assert x['id'] not in by;by[x['id']]=dict(x,source_task=task)
 cal=set(read(ROOT/'outputs/051_thinking_mode_validation/freeze.json')['patient_pool']);primary=[x for x in by.values() if x['sid'] not in cal];assert len(primary)==384
 patient=defaultdict(list)
 for x in primary:patient[x['sid']].append(x)
 bridge=[]
 for sid,rr in sorted(patient.items()):bridge+=sorted(rr,key=lambda x:stable('078/bridge/v1:'+x['id']))[:8]
 e071=lines(ROOT/'outputs/071_judge_icl_feasibility/evaluation_blind.jsonl');f4patients={x['sid'] for x in e071};teacher=set(x['sid'] for x in lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl'));f4=[x for x in primary if x['sid'] in f4patients];assert not {x['sid'] for x in f4}&teacher
 import duckdb,pandas as pd
 con=duckdb.connect();con.register('wanted',pd.DataFrame({'proposition_id':[x['id'] for x in bridge]}));raw=ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact'
 link=con.execute("select v.proposition_id,v.reference_id from read_parquet(?) v join wanted w using(proposition_id) where v.rater_alias='v1.1.0-rater-121'",[str(raw/'verdicts.parquet')]).fetchall();con.register('refs',pd.DataFrame({'reference_id':sorted({x[1] for x in link})}));refs=dict(con.execute('select reference_id,reference from read_parquet(?) join refs using(reference_id)',[str(raw/'reference_payloads.parquet')]).fetchall());con.close();assert len(link)==len(bridge)
 nnew_f4=sum(x['id'] not in {r['id'] for r in e071} for x in f4)
 sources={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'outputs/052_first_tier_validation/sample_blind.jsonl',ROOT/'outputs/053_thinking_prior_validation/sample_blind.jsonl',ROOT/'outputs/051_thinking_mode_validation/freeze.json',ROOT/'outputs/071_judge_icl_feasibility/evaluation_blind.jsonl']}
 inv=dict(primary_n=len(primary),patients=len(patient),source_counts=dict(Counter(x['source_task'] for x in primary)),authors=dict(Counter(x['author'] for x in primary)),calibration_patients_excluded=len(cal),bridge_n=len(bridge),bridge_patients=len({x['sid'] for x in bridge}),bridge_authors=dict(Counter(x['author'] for x in bridge)),reference_chars=dict(author_mean=statistics.mean(len(refs[r]) for _,r in link),author_max=max(len(refs[r]) for _,r in link),c48_mean=statistics.mean(len(x['reference']) for x in bridge)),f4_n=len(f4),f4_patients=len({x['sid'] for x in f4}),f4_new_calls=nnew_f4,ordinary_new_calls=2*sum(x['source_task']=='053' for x in primary),reference_new_calls=2*len(bridge),planned_new_total=nnew_f4+2*sum(x['source_task']=='053' for x in primary)+2*len(bridge),sources=sources,selection_reads_GT=False)
 (OUT/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 for name,rows in [('primary_blind.jsonl',primary),('bridge_blind.jsonl',[dict(x,author_reference_id=dict(link)[x['id']],author_reference=refs[dict(link)[x['id']]]) for x in bridge]),('f4_blind.jsonl',f4)]:
  (OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8',newline='\n')
 print(json.dumps(inv,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
