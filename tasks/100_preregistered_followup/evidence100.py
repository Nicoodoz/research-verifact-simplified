"""GT-blind full-corpus BM25 and whole-source-unit renderers. No network or Judge."""
from collections import Counter,defaultdict
import csv,gzip,json,os,statistics,subprocess,sys
import numpy as np
import common100 as c
sys.path.insert(0,str(c.ROOT/'tasks/008_retrieval_planning'))
import planning_core as core

class Tokens:
 def __init__(self):
  env=dict(os.environ,TOKENIZERS_PARALLELISM='false')
  self.process=subprocess.Popen([str(c.ROOT/'.local_models/085a_tokenizer_venv/Scripts/python.exe'),str(c.TASK/'token_count_worker100.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,encoding='utf-8',env=env,bufsize=1)
  self.cache={};self.calls=0
 def counts(self,texts):
  keys=[c.digest(t) for t in texts];missing={h:t for h,t in zip(keys,texts) if h not in self.cache}
  if missing:
   self.process.stdin.write(json.dumps(dict(texts=list(missing.values())),ensure_ascii=False)+'\n');self.process.stdin.flush()
   line=self.process.stdout.readline();assert line,'Tokenizer helper exited'
   values=json.loads(line);assert len(values)==len(missing)
   self.cache.update(zip(missing,values));self.calls+=1
  return [self.cache[h] for h in keys]
 def count(self,text):return self.counts([text])[0]
 def refcount(self,text):return self.count(json.dumps(text,ensure_ascii=False)[1:-1])
 def refcounts(self,texts):return self.counts([json.dumps(text,ensure_ascii=False)[1:-1] for text in texts])
 def close(self):
  self.process.stdin.close();self.process.wait(timeout=30);assert self.process.returncode==0

def csvrows(path):
 csv.field_size_limit(100000000)
 with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def source_corpus():
 raw=c.ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr'
 admrows=csvrows(raw/'admissions.csv.gz');admissions={r['SUBJECT_ID']:r for r in admrows};assert len(admissions)==len(admrows)==100
 allnotes=csvrows(raw/'ehr_noteevents.csv.gz');notes=defaultdict(dict);passages=defaultdict(list);excluded=[]
 for n in sorted(allnotes,key=lambda r:int(r['ROW_ID'])):
  sid=n['SUBJECT_ID'];a=admissions[sid];date=n['CHARTDATE'][:10]
  reason='outside_admission_calendar_dates' if not a['ADMITTIME'][:10]<=date<=a['DISCHTIME'][:10] else 'discharge_summary_excluded' if n['CATEGORY'].strip().lower()=='discharge summary' else None
  if reason:excluded.append(dict(sid=sid,note_id=n['ROW_ID'],reason=reason));continue
  item=dict(subject_id=sid,note_id=n['ROW_ID'],hadm_id=n['HADM_ID'],date=date,time=n['CHARTTIME'][11:] or 'Unknown',category=n['CATEGORY'],description=n['DESCRIPTION'],TEXT=n['TEXT'],note_sha256=c.digest(n['TEXT']))
  assert item['note_id'] not in notes[sid];notes[sid][item['note_id']]=item
  spans=list(core.paragraph_spans(n['TEXT'],limit=640))
  covered=set(i for lo,hi in spans for i in range(lo,hi))
  assert all(i in covered or char.isspace() for i,char in enumerate(n['TEXT']))
  for lo,hi in spans:
   p={k:v for k,v in item.items() if k!='TEXT'};p.update(start=lo,end_exclusive=hi,text=n['TEXT'][lo:hi]);p['passage_id']=c.digest(c.canonical(p))
   p['search_text']=f"Date: {p['date']}. {p['category']} {p['description']}. {p['text']}";passages[sid].append(p)
 for sid in passages:passages[sid].sort(key=lambda p:p['passage_id'])
 # Verify the actual 031 index fields, rather than infer them from the old report.
 old=c.lines(c.ROOT/'outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl')
 lookup={(p['subject_id'],str(p['note_id']),p['start'],p['end_exclusive']):p for pp in passages.values() for p in pp}
 for p in old:
  q=lookup[str(p['subject_id']),str(p['note_id']),p['start'],p['end_exclusive']]
  assert p['search_text']==q['search_text'] and p['text']==q['text'] and p['passage_id']==q['passage_id']
 return admissions,dict(notes),dict(passages),excluded,dict(old031_passages_verified=len(old),notes=len(allnotes),eligible_notes=sum(map(len,notes.values())),passages=sum(map(len,passages.values())))

class BM25:
 def __init__(self,passages):
  self.obj=object.__new__(core.HybridIndex);z=self.obj;z.passages=passages
  z.counts=[Counter(core.tokenize(p['search_text'])) for p in passages];z.lengths=np.array([sum(x.values()) for x in z.counts]);z.average=float(z.lengths.mean()) if len(z.lengths) else 0.;z.postings={}
  for i,counts in enumerate(z.counts):
   for token,n in counts.items():z.postings.setdefault(token,[]).append((i,n))
 def rank(self,claim):
  positive=core.HybridIndex.bm25(self.obj,claim);used={p for p,s in positive}
  return positive+[(p['passage_id'],0.) for p in self.obj.passages if p['passage_id'] not in used]

def merge(text,intervals):
 out=[]
 for lo,hi in sorted(intervals):
  assert 0<=lo<=hi<=len(text)
  if out and (lo<=out[-1][1] or not text[out[-1][1]:lo].strip()):out[-1]=(out[-1][0],max(out[-1][1],hi))
  else:out.append((lo,hi))
 if len(out)==1 and not text[:out[0][0]].strip() and not text[out[0][1]:].strip():return [(0,len(text))]
 return out

def preamble(admission):
 return f"Patient ID: {admission['SUBJECT_ID']} | Target admission: {admission['HADM_ID']} | Eligible CHARTDATE calendar range: {admission['ADMITTIME'][:10]} to {admission['DISCHTIME'][:10]} inclusive | Discharge summaries excluded.\n\n"

def note_part(note,intervals):
 intervals=merge(note['TEXT'],intervals)
 header=f"### Note ID: {note['note_id']} | Date: {note['date']} | Time: {note['time']} | Category: {note['category']} | Description: {note['description']} | Recorded HADM ID: {note['hadm_id']}\n"
 return header+''.join(f"#### Raw characters: [{lo},{hi})\n"+note['TEXT'][lo:hi]+'\n\n' for lo,hi in intervals)

def ordered(notes,chosen):return sorted(chosen,key=lambda nid:(notes[nid]['date'],int(nid)))
def render(admission,notes,chosen):return preamble(admission)+''.join(note_part(notes[nid],chosen[nid]) for nid in ordered(notes,chosen))
def total_tokens(admission,notes,chosen,tok):return tok.refcount(preamble(admission))+sum(tok.refcount(note_part(notes[nid],chosen[nid])) for nid in chosen)

def build(claim,admission,notes,passages,index,tok,limit=24000):
 ranking=index.rank(claim);lookup={p['passage_id']:p for p in passages};scores={nid:0. for nid in notes}
 for pid,score in ranking:scores[lookup[pid]['note_id']]=max(scores[lookup[pid]['note_id']],score)
 noteorder=sorted(notes,key=lambda nid:(-scores[nid],int(nid)))
 L={};cost=tok.refcount(preamble(admission));Lids=[]
 tok.refcounts([note_part(notes[nid],[(0,len(notes[nid]['TEXT']))]) for nid in noteorder])
 for nid in noteorder:
  pp=[(0,len(notes[nid]['TEXT']))];n=tok.refcount(note_part(notes[nid],pp))
  if cost+n<=limit:L[nid]=pp;cost+=n;Lids.append(nid)
 Ltext=render(admission,notes,L);Ltokens=tok.refcount(Ltext)
 assert Ltokens==cost and Ltokens<=limit,('Nonadditive L token boundary',Ltokens,cost)
 S={};cost=tok.refcount(preamble(admission));Sids=[]
 for pid,score in ranking:
  p=lookup[pid];nid=p['note_id'];old=tok.refcount(note_part(notes[nid],S[nid])) if nid in S else 0
  new=merge(notes[nid]['TEXT'],S.get(nid,[])+[(p['start'],p['end_exclusive'])]);newcost=tok.refcount(note_part(notes[nid],new))
  if cost-old+newcost<=Ltokens:S[nid]=new;cost=cost-old+newcost;Sids.append(pid)
 Stext=render(admission,notes,S);Stokens=tok.refcount(Stext)
 assert Stokens==cost and Stokens<=Ltokens,('Nonadditive S token boundary',Stokens,cost)
 E={nid:[(0,len(n['TEXT']))] for nid,n in notes.items()};Etext=render(admission,notes,E);Etokens=tok.refcount(Etext)
 return dict(S24=Stext,L24=Ltext,**{'EHR-all':Etext}),dict(S24_tokens=Stokens,L24_tokens=Ltokens,EHR_all_tokens=Etokens,S_L_token_gap=Ltokens-Stokens,
  S_passage_ids=Sids,L_note_ids=Lids,intervals=dict(S24=S,L24=L,**{'EHR-all':E}),notes_total=len(notes),passages_total=len(passages),
  S_equals_L=Stext==Ltext,L_equals_E=Ltext==Etext,S_equals_E=Stext==Etext,all_notes_untruncated=True,
  length_definition='Official0731 tokenizer on JSON-escaped reference interior, exactly as inserted in Input JSON; no outer quote tokens')
