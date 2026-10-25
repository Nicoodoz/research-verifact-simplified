"""Source-grounded coverage construction, independent Q, single concrete omission repair."""
import itertools, difflib, subprocess
from common089 import *
import api089 as api

COMMON='''Extract whole source units for a fixed training demonstration. Only this finite reference is visible, NOT the whole EHR. The physician label is historical, not a label for your extract. Never remove counterevidence to favor that label. Never generate medical facts or rewrite text. Units are indivisible including date, uncertainty, negation and event status. Return JSON: selected_ids, priority_ids (ALL unit IDs ranked), information (list), reminders (list). Each information item has claim_part (exact substring of claim), role (support/counter/limitation/related_insufficient), alternatives (list of {unit_id,quote}, verbatim source quotes representing the SAME fact including event/date/qualifiers), dependencies (list of {unit_id,quote,why}), relation (why it matters). Keep quotes short and exactly copy whitespace; no ellipses. No preserve_full veto. Explain any claimed need by concrete source facts, not hypothetical other records. Ordinary repetition can be omitted only if event/date/qualifiers truly agree. Aim for the given initial proxy budget, do not search ratios. Output analysis is private construction metadata and will never go to the Judge. '''
P_GOAL='''List the specific information needed to preserve how the COMPLETE claim relates to this finite source: favorable facts, alternatives/counterfacts, qualifications, related-but-insufficient information and concrete cross-unit dependencies. Each information item is a coverage constraint; use alternative citations only when they express the same information. Do not make all history mandatory by default. The program combines cited units to cover those items; your selected_ids is only a recommendation. Do not infer non-addressedness from what your extract omits or certify a full-record absence.'''
Q_GOAL='''Use ordinary semantic relevance to the claim, topic coverage and deduplication within the same budget. Give a serious compact selected_ids set and full priority ranking. Information may explain relevance using the same format, but is NOT a special verdict-preservation constraint. Do not emulate a special decision-basis protection method. Do not assume that an unrelated background paragraph is mandatory.'''
CHECK='''You compare a finite original source and a candidate extract for a claim. No physician label, arm identity or constructor notes are supplied. Do NOT classify the claim. Inspect deleted source units for concrete relevant information absent from retained text, considering subject/date/negation/possibility/event/value and counterfacts. Do not require unrelated background or proof about the unseen full EHR. Return JSON {issues:[{unit_id,quote,claim_part,relation,why_not_covered,kind,duplicate_of_retained,dependencies:[{unit_id,quote,why}]}],reminders:[]}. claim_part must be an exact substring of claim; quote must be a short exact verbatim substring in a DELETED unit, with original whitespace and no ellipses. kind is fact/limitation/counter/dependency. duplicate_of_retained is a list of retained unit IDs if duplicate, otherwise []. Include only grounded issues, and explain what specific information is not already retained. Generic concerns, hypothetical other records, repetition, and unlocated uncertainty belong in reminders and must not veto extraction. Do not recommend full text without specific issues that require every omitted unit. These observations are model assistance, not medical gold.'''

def body(system,payload,model=BUILDER):
    return dict(model=model,messages=[dict(role='system',content=system),dict(role='user',content=canonical(payload))],temperature=0,
        max_tokens=4000 if model==BUILDER else 3000,enable_thinking=False,stream=False,response_format={'type':'json_object'})
def all_ids(src):return [u['id'] for u in src['units']]
def size(src,ids):return token_proxy(render_reference(src,ids))
def valid_ids(ids,src):return isinstance(ids,list) and bool(ids) and all(isinstance(i,str) for i in ids) and len(set(ids))==len(ids) and set(ids)<=set(all_ids(src))
def citation(x,src):
    return isinstance(x,dict) and isinstance(x.get('quote'),str) and bool(x['quote'].strip()) and any(u['id']==x.get('unit_id') and x['quote'] in u['text'] for u in src['units'])
def ordinary(src,selected,rank,target,add_only=False):
    ids=list(selected)
    for uid in rank:
        if uid not in ids and abs(size(src,ids+[uid])-target)<abs(size(src,ids)-target):ids.append(uid)
    if not add_only:
        for uid in reversed(rank):
            rest=[x for x in ids if x!=uid]
            if rest and abs(size(src,rest)-target)<abs(size(src,ids)-target):ids=rest
    return [i for i in all_ids(src) if i in ids]
def coverage_select(ex,src,obj,target):
    constraints=[];rejected=[]
    for item in obj.get('information',[]):
        alts=item.get('alternatives',[]) if isinstance(item,dict) else []
        deps=item.get('dependencies',[]) if isinstance(item,dict) else []
        ok=isinstance(item,dict) and bool(item.get('claim_part')) and item['claim_part'] in ex['claim'] and bool(item.get('relation'))
        good=[z for z in alts if citation(z,src)]
        if not ok or not good or not isinstance(deps,list) or any(not citation(d,src) or not d.get('why') for d in deps):
            rejected.append(dict(item=item,reason='unlocated_or_incomplete_constraint'));continue
        constraints.append(dict(alternatives=sorted({a['unit_id'] for a in good}),dependencies=sorted({a['unit_id'] for a in deps}),item=item))
    if not constraints:return ordinary(src,obj['selected_ids'],obj['priority_ids'],target),constraints,rejected
    units=all_ids(src);assert len(units)<=18,'source too large for frozen enumerator'
    feasible=[]
    for n in range(1,len(units)+1):
        for tup in itertools.combinations(units,n):
            s=set(tup)
            if all(s.intersection(c['alternatives']) and set(c['dependencies'])<=s for c in constraints):
                length=size(src,list(tup));feasible.append((length,tuple(tup)))
    # Cover listed information using the shortest source set; budget is soft if required coverage exceeds it.
    length,chosen=min(feasible,key=lambda x:(x[0],x[1]))
    return list(chosen),constraints,rejected
def repair(ex,src,ids,obj):
    accepted=[];rejected=[];add=set()
    for issue in obj.get('issues',[]) if isinstance(obj,dict) and isinstance(obj.get('issues'),list) else []:
        reason=None
        if not citation(issue,src):reason='quote_or_source_ID_not_exact'
        elif issue['unit_id'] in ids:reason='not_deleted'
        elif not issue.get('claim_part') or issue['claim_part'] not in ex['claim']:reason='claim_relation_not_located'
        elif not issue.get('relation') or not issue.get('why_not_covered'):reason='no_concrete_relation_or_noncoverage_explanation'
        elif issue.get('kind') not in ('fact','limitation','counter','dependency'):reason='invalid_issue_kind'
        elif issue.get('duplicate_of_retained'):reason='reported_duplicate'
        elif any(issue['quote'] in u['text'] for u in src['units'] if u['id'] in ids):reason='verbatim_already_retained'
        elif not isinstance(issue.get('dependencies',[]),list) or any(not citation(d,src) or not d.get('why') for d in issue.get('dependencies',[])):reason='dependency_not_grounded'
        if reason:rejected.append(dict(issue=issue,reason=reason))
        else:
            accepted.append(issue);add.add(issue['unit_id']);add.update(d['unit_id'] for d in issue.get('dependencies',[]))
    return [i for i in all_ids(src) if i in set(ids)|add],accepted,rejected
def construct(ex,src,arm,phase='fixed'):
    target=round(token_proxy(ex['reference'])*.5)
    payload=dict(claim=ex['claim'],physician_label=ex['physician_label'],source_prefix=src['prefix'],source_units=src['units'],budget_proxy_tokens=target,
                 proxy_definition='English words, numbers, punctuation; not model tokens')
    j=api.freeze_job(phase+'_construct',arm,ex['proposition_id'],ex['sid'],body(COMMON+(P_GOAL if arm=='P4' else Q_GOAL),payload))
    obj,receipt=api.call_json(j)
    rec=dict(constructor_output=obj,constructor_receipt=receipt,budget_proxy_tokens=target)
    if not isinstance(obj,dict) or not valid_ids(obj.get('selected_ids'),src) or not valid_ids(obj.get('priority_ids'),src) or set(obj['priority_ids'])!=set(all_ids(src)):
        ids=all_ids(src);rec.update(status='invalid_constructor_full_retention',constraints=[],rejected_constraints=[])
    elif arm=='P4':
        ids,cs,rejected=coverage_select(ex,src,obj,target);rec.update(constraints=cs,rejected_constraints=rejected,status='constructed')
    else:ids=ordinary(src,obj['selected_ids'],obj['priority_ids'],target);rec.update(status='constructed')
    rec['initial_selected_ids']=ids
    payload=dict(claim=ex['claim'],original_reference=ex['reference'],source_units=src['units'],selected_ids=ids,candidate_reference=render_reference(src,ids))
    cj=api.freeze_job(phase+'_review',arm,ex['proposition_id'],ex['sid'],body(CHECK,payload,MODEL))
    checked,review=api.call_json(cj)
    final,accepted,rejected=repair(ex,src,ids,checked)
    rec.update(review_output=checked,review_receipt=review,accepted_issues=accepted,rejected_issues=rejected,selected_ids=final,
               review_valid=isinstance(checked,dict) and isinstance(checked.get('issues'),list),added_ids=[i for i in final if i not in ids])
    # Invalid checker does not invent a repair or a certificate; retain candidate, disclose unverified semantic coverage.
    source_check(ex['reference'],src,final,render_reference(src,final))
    return rec
def pair(ex,src,phase):
    if len(ex['reference'])<=1200 or len(src['units'])==1:
        return {a:dict(selected_ids=all_ids(src),initial_selected_ids=all_ids(src),status='short_or_single_unit',added_ids=[]) for a in ('P4','Q4')}
    p=construct(ex,src,'P4',phase);q=construct(ex,src,'Q4',phase)
    q['before_length_match_ids']=q['selected_ids'][:]
    if p.get('added_ids') and isinstance(q.get('constructor_output'),dict) and valid_ids(q['constructor_output'].get('priority_ids'),src):
        q['selected_ids']=ordinary(src,q['selected_ids'],q['constructor_output']['priority_ids'],size(src,p['selected_ids']),True)
    q['length_match_added_ids']=[x for x in q['selected_ids'] if x not in q['before_length_match_ids']]
    return dict(P4=p,Q4=q)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    examples=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl');sources={x['proposition_id']:unitize(x['reference']) for x in examples}
    f=OUT/'constructor_freeze.json'
    if not f.exists():
        put(OUT/'source_units.json',sources)
        put(f,dict(created_utc=now(),cap=20,construction_cap=2,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            sources={p.relative_to(ROOT).as_posix():sha(p) for p in [TASK/'protocol.md',TASK/'common089.py',TASK/'api089.py',TASK/'construct089.py',
             ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl',ROOT/'outputs/088_evidence_preserving_demonstration_compression/source_units.json',
             ROOT/'docs/089_Codex_具体遗漏核对驱动的示例压缩与实测_执行提示词.md']},prices=PRICES))
    for rel,d in read(f)['sources'].items():assert sha(ROOT/rel)==d
    assert sources==read(ROOT/'outputs/088_evidence_preserving_demonstration_compression/source_units.json')
    records=[];arms={a:copy.deepcopy(examples) for a in ARMS}
    for i,ex in enumerate(examples):
        path=OUT/'construction'/f'slot{i+1}.json';src=sources[ex['proposition_id']]
        if path.exists():rec=read(path)
        else:
            rec=dict(id=ex['proposition_id'],sid=ex['sid'],ordinal=i+1,claim=ex['claim'],label=ex['physician_label'],**pair(ex,src,'fixed'))
            put(path,rec)
        for a in ('P4','Q4'):
            arms[a][i]['reference']=render_reference(src,rec[a]['selected_ids'])
            rec[a].update(chars=len(arms[a][i]['reference']),proxy_tokens=token_proxy(arms[a][i]['reference']))
        rec.update(original_chars=len(ex['reference']),original_proxy_tokens=token_proxy(ex['reference']));records.append(rec)
        print(canonical(dict(slot=i+1,selected={a:rec[a]['selected_ids'] for a in ('P4','Q4')})),flush=True)
    old=read(ROOT/'outputs/087_f4_evidence_intervention/templates.json')
    systems={a:render_system(old['systems']['B'],old['header'],arms[a]) for a in ARMS};assert systems['F4']==old['systems']['F4']
    put(OUT/'construction_summary.json',records);put(OUT/'demonstrations.json',arms)
    put(OUT/'templates.json',dict(systems=systems,hashes={a:h(v) for a,v in systems.items()},chars={a:len(v) for a,v in systems.items()}))
    text(OUT/'source_changes.diff','\n'.join(''.join(difflib.unified_diff(examples[i]['reference'].splitlines(True),arms[a][i]['reference'].splitlines(True),fromfile=f'F4/slot{i+1}',tofile=f'{a}/slot{i+1}')) for a in ('P4','Q4') for i in range(4)))
    put(OUT/'demonstration_freeze.json',dict(created_utc=now(),target_GT_used=False,files={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
    print(canonical(dict(system_chars={a:len(v) for a,v in systems.items()},cost=sum(x['cost_or_unknown_cny'] for x in api.state()[0]))))
if __name__=='__main__':main()
