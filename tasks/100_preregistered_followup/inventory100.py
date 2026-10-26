"""Outcome-blind source inventory and tokenizer/usage alignment on existing receipts."""
import json,statistics,sqlite3
import common100 as c
import evidence100 as e

def main():
 a,notes,pp,exc,summary=e.source_corpus();t=e.Tokens()
 try:
  registry=c.read(c.OUT/'source_registry.json');freeze=c.read(c.ROOT/'outputs/098_p90_native_confirmation/execution_freeze.json')
  excluded=set(freeze['evaluation_patients'])|set(freeze['example_development_patients']);confirmation=set(a)-excluded;assert len(confirmation)==32
  inventory=[]
  for sid in sorted(notes):
   E=e.render(a[sid],notes[sid],{nid:[(0,len(n['TEXT']))] for nid,n in notes[sid].items()})
   inventory.append(dict(sid=sid,role='confirmation' if sid in confirmation else 'development',notes=len(notes[sid]),passages=len(pp.get(sid,[])),chars=len(E),tokens=t.count(E),EHR_all_sha256=c.digest(E),admission_sha256=c.digest(c.canonical(a[sid])),notes_with_other_recorded_HADM=sum(n['hadm_id']!=a[sid]['HADM_ID'] for n in notes[sid].values())))
  con=sqlite3.connect(f'file:{(c.ROOT/".local_models/098_p90_native_confirmation/budget.sqlite").as_posix()}?mode=ro',uri=True)
  paths=con.execute('SELECT folder FROM attempts WHERE status=200 ORDER BY rowid LIMIT 120').fetchall();con.close();offsets=[]
  for (folder,) in paths:
   p=c.ROOT/folder;req=c.read(p/'request.json');response=json.loads(c.read(p/'receipt.json')['transport']['body_text']);body=req['job']['body']
   # Read usage only: no verdict, reason, GT or correctness inspection.
   local=sum(t.count(m['content']) for m in body['messages']);offsets.append(response['usage']['prompt_tokens']-local)
  c.putl(c.OUT/'patient_length_inventory.jsonl',inventory)
  c.put(c.OUT/'source_inventory.json',dict(utc=c.utc(),**summary,exclusions_by_reason={r:sum(x['reason']==r for x in exc) for r in sorted({x['reason'] for x in exc})},confirmation_patients=sorted(confirmation),development_patients=sorted(excluded),
    tokenizer_alignment=dict(N=len(offsets),API_prompt_minus_sum_local_content_min=min(offsets),max=max(offsets),median=statistics.median(offsets),values_counts={str(v):offsets.count(v) for v in sorted(set(offsets))}),
    raw_sha256={name:c.sha(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr'/name) for name in ['admissions.csv.gz','ehr_noteevents.csv.gz']},no_new_API=True,GT_not_read=True))
  print(c.canonical(dict(**summary,confirmation_patients=len(confirmation),EHR_all_min_tokens=min(x['tokens'] for x in inventory),EHR_all_max_tokens=max(x['tokens'] for x in inventory),tokenizer_offset_range=[min(offsets),max(offsets)])))
 finally:t.close()
if __name__=='__main__':main()
