"""Observable claim/evidence-window operator pairs. No labels, verdicts or LLM calls."""
from collections import Counter
import re,math
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import normalize
import common102 as c

GENERIC=set(ENGLISH_STOP_WORDS)|set('patient patients pt hospital admission medical note notes history given stated documented reports reported continued continue day days status'.split())
OPERATORS={
 'time_before':r'\b(before|prior|previous|earlier|baseline|preoperative)\b',
 'time_after':r'\b(after|following|subsequent|postoperative|postop|pod|hd)\b',
 'time_endpoint':r'\b(discharg\w*|outpatient|follow.?up|home|overnight)\b',
 'time_explicit':r'\b\d{1,4}[-/]\d{1,2}(?:[-/]\d{1,4})?\b|\b\d+(?:st|nd|rd|th)?\s+(?:hours?|days?|weeks?)\b',
 'plan':r'\b(plan\w*|will|would|recommend\w*|scheduled|pending|consider\w*|should|possible|may|can)\b',
 'execution':r'\b(receiv\w*|perform\w*|underwent|given|start\w*|restart\w*|administ\w*|complet\w*|remov\w*|extubat\w*|insert\w*|convert\w*)\b',
 'negation':r'\b(no|not|without|deni\w*|negative|absent|refus\w*|never|none|unable)\b',
 'uncertainty':r'\b(possible|possibly|suspect\w*|likely|unlikely|unclear|unknown|concern|rule out|r/o)\b',
 'quantity':r'\b\d+(?:\.\d+)?\b|\b(dose|rate|peak\w*|volume|amount|level|mg|mcg|units?)\b',
 'degree_change':r'\b(increas\w*|decreas\w*|improv\w*|wors\w*|mild|moderate|severe|minimum|minimal|maximum|significant\w*|stable|resolv\w*)\b',
 'causal':r'\b(due to|secondary to|because|caus\w*|result\w*|attribut\w*|in the setting of)\b',
 'finding_source':r'\b(show\w*|reveal\w*|demonstrat\w*|found|confirm\w*|diagnos\w*|indicat\w*)\b',
 'entity_other':r'\b(wife|husband|mother|father|family|brother|sister|son|daughter)\b',
 'laterality':r'\b(left|right|bilateral|upper|lower|proximal|distal)\b',
}
def words(text):
 text=re.sub(r'\[\*\*.*?\*\*\]',' ',text,flags=re.S)
 return [m.group().lower() for m in re.finditer(r'[A-Za-z]{2,}',text) if m.group().lower() not in GENERIC]
def topic_text(text):return ' '.join(words(text))
def operators(text):
 # Header dates/IDs are excluded by evidence_windows; dates in source TEXT remain.
 text=re.sub(r'\[\*\*(.*?)\*\*\]',lambda m:m[1] if re.fullmatch(r'[\d/\- ]+',m[1]) else ' ',text).lower()
 out={k for k,pattern in OPERATORS.items() if re.search(pattern,text)}
 if 'negation' not in out:out.add('unmarked_polarity')
 return out
def evidence_windows(claim,reference,max_windows=3):
 anchors=set(words(claim));markers=list(re.finditer(r'(?m)^\d+\.\s*Date:',reference));segments=[]
 if markers:
  for i,m in enumerate(markers):
   hi=markers[i+1].start() if i+1<len(markers) else len(reference);lo=m.start();head=reference.find('| Text:',lo,hi)
   if head>=0:lo=head+len('| Text:')
   segments.append((lo,hi))
 else:segments=[(0,len(reference))]
 candidates=[]
 for lo,hi in segments:
  tokens=list(re.finditer(r'[A-Za-z]{2,}',reference[lo:hi]));hits=[i for i,t in enumerate(tokens) if t.group().lower() in anchors]
  for i in hits:
   left=max(0,i-24);right=min(len(tokens),i+25);start=lo+tokens[left].start();end=lo+tokens[right-1].end()
   snippet=reference[start:end];shared=anchors&set(words(snippet));score=sum(1+min(len(w),12)/12 for w in shared)/math.sqrt(max(1,len(words(snippet))))
   candidates.append((score,len(shared),start,end,shared))
 selected=[]
 for score,n,start,end,shared in sorted(candidates,key=lambda z:(-z[0],-z[1],z[2],z[3])):
  if any(max(0,min(end,x['end'])-max(start,x['start']))>.5*min(end-start,x['end']-x['start']) for x in selected):continue
  selected.append(dict(start=start,end=end,sha256=c.digest(reference[start:end]),anchor_count=n,anchor_coverage=n/max(1,len(anchors)),operator_tags=sorted(operators(reference[start:end]))))
  if len(selected)==max_windows:break
 return selected
def relation_features(claim,reference):
 ct=operators(claim);windows=evidence_windows(claim,reference);f={}
 for k in ct:f['claim/'+k]=.3
 if not windows:f['pair/no_anchor_window']=1.
 for rank,w in enumerate(windows):
  weight=(1.,.6,.4)[rank]
  for ck in ct:
   for ek in w['operator_tags']:f['pair/'+ck+'::'+ek]=f.get('pair/'+ck+'::'+ek,0)+weight
  for ek in w['operator_tags']:f['evidence/'+ek]=f.get('evidence/'+ek,0)+weight*.3
 return f,dict(claim_operators=sorted(ct),windows=windows,reference_used=bool(windows))
class Selector:
 def __init__(self,teachers):
  self.teachers=teachers;texts=[topic_text(r['claim']) for r in teachers]
  self.word=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True);self.char=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True)
  self.w=self.word.fit_transform(texts);self.ch=self.char.fit_transform(texts)
  feature_pairs=[relation_features(r['claim'],r['reference']) for r in teachers];self.audit=[x[1] for x in feature_pairs]
  self.encoder=DictVectorizer();matrix=self.encoder.fit_transform([x[0] for x in feature_pairs])
  self.rel=normalize(matrix);self.keys=self.encoder.get_feature_names_out().tolist()
 def scores(self,claim,reference,claim_only=False):
  text=topic_text(claim);topic=.7*(self.word.transform([text])@self.w.T).toarray()[0]+.3*(self.char.transform([text])@self.ch.T).toarray()[0]
  features,audit=relation_features(claim,reference)
  if claim_only:features={k:v for k,v in features.items() if k.startswith('claim/')}
  vector=normalize(self.encoder.transform([features]));relation=(vector@self.rel.T).toarray()[0]
  return topic,.7*relation+.3*topic,audit

def choose(scores,combos,teachers):
 return min(combos,key=lambda ix:(-sum(float(scores[i]) for i in ix),tuple(teachers[i]['id'] for i in ix)))
