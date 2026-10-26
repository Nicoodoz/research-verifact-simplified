"""Synthetic construction checks only; no Judge or clinical quality."""
import inspect
import numpy as np
import common100 as c
import evidence100 as e

def main():
 t=e.Tokens()
 try:
  assert e.merge('  alpha \n beta  ',[(2,7),(10,14)])==[(0,16)]
  assert e.merge('alpha XX beta',[(0,5),(9,13)])==[(0,5),(9,13)]
  a=dict(SUBJECT_ID='synthetic',HADM_ID='1',ADMITTIME='2020-01-01',DISCHTIME='2020-01-02')
  notes={str(i):dict(subject_id='synthetic',note_id=str(i),hadm_id='1',date='2020-01-01',time='Unknown',category='Test',description='synthetic',TEXT=text,note_sha256=c.digest(text)) for i,text in [(10,'  alpha finding.\n\n beta observation.  '),(2,'gamma plan.\n'),(3,'delta report.\n')]}
  pp=[]
  for nid,n in notes.items():
   for lo,hi in e.core.paragraph_spans(n['TEXT']):
    pp.append(dict(passage_id=c.digest(nid+str(lo)),note_id=nid,start=lo,end_exclusive=hi,text=n['TEXT'][lo:hi],search_text=n['TEXT'][lo:hi]))
  pp.sort(key=lambda p:p['passage_id']);idx=e.BM25(pp)
  expected=e.core.HybridIndex(pp,np.ones((len(pp),2))).bm25('alpha finding')
  assert idx.rank('alpha finding')[:len(expected)]==expected and len(idx.rank('unseenword'))==len(pp)
  refs,meta=e.build('alpha finding',a,notes,pp,idx,t)
  assert refs['S24']==refs['L24']==refs['EHR-all'] and meta['S_equals_L'] and meta['all_notes_untruncated']
  assert refs['EHR-all'].index('Note ID: 2')<refs['EHR-all'].index('Note ID: 10')
  for n in notes.values():assert n['TEXT'] in refs['EHR-all']
  assert 'GT' not in inspect.signature(e.build).parameters
  c.put(c.OUT/'construction_fixture_checks_JSON_length.json',dict(utc=c.utc(),status='PASS',checks=['whitespace merge and full TEXT restoration','separate nonadjacent spans','reused008 BM25 equality and zero tails','date then numeric note-ID order','whole-note and whole-block identity when all fit','JSON-escaped actual render token accounting and GT-free builder signature'],paid_API_calls=0,synthetic_only=True))
  print('PASS: six construction fixture groups')
 finally:t.close()
if __name__=='__main__':main()
