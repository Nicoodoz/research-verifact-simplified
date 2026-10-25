"""Local-only incremental selection. No labels, old Judge outputs, or API calls."""
import math,re
from collections import Counter
import common044 as c
BUDGET=1500
FEATURES=['mean_rank','best_rank','mean_score','max_score','pack_size','add_chars','base_chars',
 'claim_coverage','new_claim_coverage','text_novelty','new_number_fraction','same_note_fraction',
 'new_date_fraction','time_span','admission_match','discharge_match','negation_fraction','base_claim_coverage']
def toks(text): return set(c.pc.tokenize(text))
def similarity(a,b): return len(a&b)/max(1,len(a|b))
def duplicate_key(p): return (p['date'],p['time'],p['category'],' '.join(p['text'].split()))
def append_reference(base,pack,ps):
    n=max(c.reference_entries(base),default=0); ref=base
    for i,pid in enumerate(pack,n+1): ref+='\n'+c.pc.display_line(i,ps[pid])
    c.require(ref.startswith(base) and len(ref)-len(base)<=BUDGET,'base/budget invariant')
    return ref

def features(claim,base,base_ids,pack,ps,scores,ranked):
    q=toks(claim); bsets=[toks(ps[i]['text']) for i in base_ids]
    bt=set().union(*bsets) if bsets else set(); sets=[toks(ps[i]['text']) for i in pack]
    pt=set().union(*sets) if sets else set(); dates=sorted(set(ps[i]['date'] for i in ranked))
    dr={d:k/max(1,len(dates)-1) for k,d in enumerate(dates)}
    loc=[dr[ps[i]['date']] for i in pack]; rank={p:i/max(1,len(ranked)-1) for i,p in enumerate(ranked)}
    numbers=lambda t:set(re.findall(r'\d+(?:\.\d+)?',t))
    pn=numbers(' '.join(ps[i]['text'] for i in pack)); bn=numbers(' '.join(ps[i]['text'] for i in base_ids))
    mean=lambda x:sum(x)/len(x) if x else 0.0
    bnotes={ps[i]['note_id'] for i in base_ids}; bdates={ps[i]['date'] for i in base_ids}
    early=bool(re.search(r'\b(on|at) admission\b|\badmitted\b',claim.lower()))
    late=bool(re.search(r'\b(discharge|eventually|ultimately|finally)\b',claim.lower()))
    vals=[mean([rank[i] for i in pack]),min([rank[i] for i in pack],default=0),
      mean([scores[i] for i in pack]),max([scores[i] for i in pack],default=0),len(pack),
      len(append_reference(base,pack,ps))-len(base),len(base),len(q&pt)/max(1,len(q)),
      len((q-bt)&pt)/max(1,len(q)),
      mean([1-max([similarity(a,b) for b in bsets],default=0) for a in sets]),
      len(pn-bn)/max(1,len(pn)),mean([ps[i]['note_id'] in bnotes for i in pack]),
      mean([ps[i]['date'] not in bdates for i in pack]),max(loc,default=0)-min(loc,default=0),
      float(early)*(1-mean(loc)),float(late)*mean(loc),len(pt&{'no','not','without','denies','negative','cancelled'})/max(1,len(pt)),
      len(q&bt)/max(1,len(q))]
    c.require(len(vals)==len(FEATURES) and all(math.isfinite(float(v)) for v in vals),'feature finite')
    return list(map(float,vals))

def propose(claim,base,base_ids,candidates,scores,ps):
    ranked=sorted(candidates,key=lambda x:(-scores[x],x))
    used={duplicate_key(ps[i]) for i in base_ids}
    pool=[]; seen=set(used)
    for pid in ranked:
        key=duplicate_key(ps[pid])
        if key not in seen: pool.append(pid); seen.add(key)
    q=toks(claim); bsets=[toks(ps[i]['text']) for i in base_ids]
    bt=set().union(*bsets) if bsets else set(); dt={i:toks(ps[i]['text']) for i in pool}
    rank={p:k for k,p in enumerate(ranked)}; high=[i for i in pool if rank[i]<24]
    base_dates={ps[i]['date'] for i in base_ids}
    def complementary(pid):
        rel=1-rank[pid]/max(1,len(ranked)-1)
        gain=len((q-bt)&dt[pid])/max(1,len(q))
        novelty=1-max([similarity(dt[pid],s) for s in bsets],default=0)
        return .6*rel+.25*gain+.15*novelty
    if re.search(r'\b(on|at) admission\b',claim.lower()):
        time_order=sorted(high,key=lambda i:(ps[i]['date'],rank[i],i))
    elif re.search(r'\b(discharge|eventually|ultimately|finally)\b',claim.lower()):
        time_order=sorted(high,key=lambda i:(ps[i]['date'],-rank[i],i),reverse=True)
    else:
        time_order=sorted(high,key=lambda i:(ps[i]['date'] in base_dates,rank[i],i))
    orders={'rank':pool,'complement':sorted(high,key=lambda i:(-complementary(i),rank[i],i)),
            'time':time_order}
    result={}
    for name,order in orders.items():
        pack=[]
        for pid in order:
            trial=pack+[pid]
            n=max(c.reference_entries(base),default=0)
            added=sum(1+len(c.pc.display_line(k,ps[p])) for k,p in enumerate(trial,n+1))
            if added<=BUDGET: pack=trial
            if len(pack)>=2: break
        ref=append_reference(base,pack,ps)
        result[name]={'ids':pack,'reference':ref,'added_chars':len(ref)-len(base),
          'features':features(claim,base,base_ids,pack,ps,scores,ranked)}
    return result
