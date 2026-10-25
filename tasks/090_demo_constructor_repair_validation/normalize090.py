"""Deterministic structure/source normalization. No model, GT, fuzzy matching or target reads."""
import itertools
from common090 import *
def loads_unique(s):
    def hook(pairs):
        d={}
        for k,v in pairs:
            if k in d and d[k]!=v:raise ValueError('conflicting_duplicate_field:'+k)
            d[k]=v
        return d
    return json.loads(s,object_pairs_hook=hook)
def all_ids(src):return [u['id'] for u in src['units']]
def norm(s):return ' '.join(s.split())
def locate(quote,text):
    if not isinstance(quote,str) or not quote.strip():return dict(valid=False,reason='empty_quote')
    pattern=r'\s+'.join(re.escape(x) for x in quote.split())
    if quote.strip()[0].isalnum():pattern=r'(?<!\w)'+pattern
    if quote.strip()[-1].isalnum():pattern=pattern+r'(?!\w)'
    matches=list(re.finditer(pattern,text))
    if len(matches)!=1:return dict(valid=False,reason='missing_quote' if not matches else 'ambiguous_quote',matches=len(matches))
    m=matches[0];return dict(valid=True,start=m.start(),end=m.end(),original=text[m.start():m.end()],whitespace_normalized=text[m.start():m.end()]!=quote)
def unit_id(v):
    if isinstance(v,str):return v
    if isinstance(v,dict):
        ids=[v[k] for k in ('id','unit_id') if k in v]
        if ids and all(isinstance(x,str) and x==ids[0] for x in ids):return ids[0]
    return None
def ids(v,src,empty=False):
    issues=[]
    if not isinstance(v,list):return dict(valid=False,ids=[],issues=['not_list'])
    out=[unit_id(x) for x in v]
    if not out and not empty:issues.append('empty_ID_list')
    if any(x is None or x not in all_ids(src) for x in out):issues.append('unknown_empty_or_conflicting_ID')
    if len(set(out))!=len(out):issues.append('duplicate_ID')
    # Explicit rank is meaningful only if present for every entry, integer and unique.
    ranked=[x.get('rank') for x in v if isinstance(x,dict) and 'rank' in x]
    if ranked:
        if len(ranked)!=len(v) or any(type(r)is not int for r in ranked) or len(set(ranked))!=len(ranked):issues.append('ambiguous_rank')
        else:out=[u for r,u in sorted(zip(ranked,out))]
    return dict(valid=not issues,ids=out,issues=issues,object_IDs=sum(isinstance(x,dict) for x in v),missing_ids=[x for x in all_ids(src) if x not in out])
def citation(c,src):
    uid=unit_id(c);u=next((u for u in src['units'] if u['id']==uid),None)
    if not isinstance(c,dict) or u is None:return dict(valid=False,reason='invalid_unit_ID')
    z=locate(c.get('quote'),u['text'])
    if z['valid']:z.update(unit_id=uid,reference_start=u.get('start',0)+z['start'],reference_end=u.get('start',0)+z['end'])
    return z
def select_p(ex,src,obj,target):
    groups=obj.get('groups',obj.get('information')) if isinstance(obj,dict) else None
    records=[];errors=[]
    if not isinstance(groups,list) or not groups:return dict(usable=False,status='no_information_constraints',selected_ids=all_ids(src),groups=[],issues=['P never falls back to ordinary relevance'])
    for i,g in enumerate(groups):
        if not isinstance(g,dict):errors.append(f'group{i}:not_object');continue
        part=g.get('claim_part');alts=g.get('alternatives',[]);deps=g.get('dependencies',[])
        if not isinstance(part,str) or not part.strip() or norm(part) not in norm(ex['claim']) or not isinstance(alts,list) or not alts or not isinstance(deps,list):
            errors.append(f'group{i}:missing_claim_or_citations');continue
        ac=[citation(c,src) for c in alts];dc=[citation(c,src) for c in deps]
        if any(not c['valid'] for c in ac+dc):errors.append(f'group{i}:unlocated_source')
        records.append(dict(index=i,claim_part=part,role=g.get('role'),alternatives=ac,dependencies=dc,relation=g.get('relation'),all_citations_valid=all(c['valid'] for c in ac+dc)))
    ranking=ids(obj.get('priority_ids',[]),src,True)
    if errors:return dict(usable=False,status='unresolved_information_source',selected_ids=all_ids(src),groups=records,issues=errors,optional_ranking=ranking)
    units=all_ids(src)
    if len(units)>18:raise ValueError('Frozen passage enumerator limit exceeded')
    candidates=[]
    for n in range(1,len(units)+1):
        for selected in itertools.combinations(units,n):
            s=set(selected)
            if all(any(c['unit_id'] in s for c in g['alternatives']) and all(c['unit_id'] in s for c in g['dependencies']) for g in records):
                length=token_proxy(render_reference(src,list(selected)));candidates.append((length,selected))
    length,chosen=min(candidates,key=lambda x:(x[0],x[1]))
    return dict(usable=True,status='coverage_constructed',selected_ids=list(chosen),groups=records,issues=[],optional_ranking=ranking,
                initial_budget_proxy=target,selected_proxy=length,over_budget=length>target)
def select_q(ex,src,obj,target):
    parsed=ids(obj.get('selected_ids') if isinstance(obj,dict) else None,src)
    if not parsed['valid']:return dict(usable=False,status='invalid_Q_selection',selected_ids=all_ids(src),issues=parsed['issues'])
    # Honor independent relevance choice; NEVER add a unit merely to fill a length target.
    selected=[u for u in all_ids(src) if u in parsed['ids']];length=token_proxy(render_reference(src,selected))
    return dict(usable=True,status='relevance_constructed',selected_ids=selected,normalization=parsed,initial_budget_proxy=target,selected_proxy=length,over_budget=length>target)
def repair(ex,src,retained,obj):
    accepted=[];rejected=[];add=set();selected=set(retained);units={u['id']:u for u in src['units']}
    issues=obj.get('issues') if isinstance(obj,dict) else None
    if not isinstance(issues,list):return dict(review_valid=False,selected_ids=retained,accepted=[],rejected=[],unresolved='checker_schema_invalid')
    for raw in issues:
        issue=raw if isinstance(raw,dict) else {};uid=unit_id(issue);c=citation(issue,src);reason=None
        if uid not in units:reason='unknown_or_conflicting_ID'
        elif uid in selected:reason='not_deleted'
        elif not c['valid']:reason=c.get('reason','unlocated_quote')
        elif not isinstance(issue.get('claim_part'),str) or not issue['claim_part'].strip() or norm(issue['claim_part']) not in norm(ex['claim']):reason='claim_part_not_located'
        elif not issue.get('relation') or not issue.get('why_not_covered'):reason='missing_specific_relation'
        elif issue.get('kind') not in ('fact','limitation','counter','dependency'):reason='invalid_kind'
        elif issue.get('duplicate_of_retained'):reason='reported_duplicate'
        elif any(norm(c['original']) in norm(units[u]['text']) for u in selected|add):reason='already_covered_exact_normalized_quote'
        deps=issue.get('dependencies',[]);dc=[citation(d,src) for d in deps] if isinstance(deps,list) else []
        if reason is None and (not isinstance(deps,list) or any(not d['valid'] for d in dc)):reason='unlocated_dependency'
        if reason:rejected.append(dict(issue=raw,reason=reason));continue
        accepted.append(dict(issue=raw,citation=c,dependencies=dc));add.add(uid);add.update(d['unit_id'] for d in dc)
    final=[u for u in all_ids(src) if u in selected|add]
    return dict(review_valid=True,selected_ids=final,added_ids=[u for u in final if u not in selected],accepted=accepted,rejected=rejected,
        semantic_certified=False,reminders=obj.get('reminders',[]))
