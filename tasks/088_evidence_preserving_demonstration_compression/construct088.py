"""One fixed reusable source-ID constructor and label-blind source checker."""
import difflib,subprocess
from common088 import *
import api088 as api

COMMON='''You extract whole original source units for a fixed training demonstration, not for a target evaluation patient. You see its claim, existing physician label, source reference units and a length budget. The label belongs to the original patient's record, not newly annotated excerpts. Never selectively discard contrary material merely to make that label look correct. Never invent or rewrite medical facts, metadata, or sentences. Units are indivisible existing passages; retain dependencies and qualify uncertainty rather than filling gaps. Only return source IDs; program code will reproduce the text. Short units may still contain pre-existing boundary gaps. Return JSON with selected_ids (unique source IDs), priority_ids (ALL source IDs ranked most to least relevant), preserve_full (boolean), and notes (brief internal concerns). No generated explanation will be given to the downstream Judge. Aim near the provided proxy-token budget without padding. If meaningful relation/context cannot be retained, set preserve_full true. '''
P_GOAL='''Objective: preserve the basis for judging the COMPLETE claim, including supporting facts and necessary qualifiers; refuting, limiting, partial-support or non-completion facts; topically related facts that do not establish the claim; cross-date/event/subject dependencies; and any information whose deletion could change the addressedness or support relationship. For Supported protect full scope; for Not Supported retain the specific insufficiency as well as relevant facts, not only explicit contradictions. For Not Addressed preserve relevant event/attribute context: omission from an excerpt never proves absence from the entire source. Select both directions, not only label-favoring excerpts.'''
Q_GOAL='''Objective: ordinary claim-focused relevance extraction. Select the most relevant passages, cover the claim's topics and concepts, and avoid redundant repetitions within the length budget. Rank all source units by semantic relevance and topic coverage; prefer the concise relevant set. Use the same source-only constraints. Do not design a special verdict-basis protection scheme.'''
CHECK='''Compare a source reference and an extract for a training claim. You are NOT given an expected label and must NOT issue a medical verdict or decide a patient case. Identify source unit IDs omitted from the candidate whose facts or qualifiers could materially change how the COMPLETE claim can be judged: support/contrary/partial facts, temporal or subject dependencies, event status, or whether the topic is addressed. Pure repetition need not be restored. Do not require unrelated content or treat missing words as full-record absence. Every issue must cite source unit IDs. Return JSON: missing_ids (units to add), distorted_ids (selected units whose combination falsely changes meaning beyond repair by those additions), uncertain_after_adding_missing_ids (boolean), issues (brief source-based explanation). An addition must be grounded in the original, never a newly inferred fact. These are source-preservation observations, not new clinical gold labels.'''

def body(system,payload):
    return dict(model=BUILDER,messages=[dict(role='system',content=system),dict(role='user',content=canonical(payload))],
                temperature=0,max_tokens=3000,enable_thinking=False,stream=False,response_format={'type':'json_object'})
def all_ids(src):return [x['id'] for x in src['units']]
def valid_ids(v,src,allow_empty=False):
    return isinstance(v,list) and (bool(v) or allow_empty) and all(isinstance(x,str) for x in v) and len(set(v))==len(v) and set(v)<=set(all_ids(src))
def size(src,ids):return token_proxy(render_reference(src,ids))
def match_budget(src,ids,rank,target):
    # Ordinary relevance priority only, no P selection or label-based editing.
    ordered=[x for x in rank if x in ids]
    for uid in rank:
        if uid not in ordered and abs(size(src,ordered+[uid])-target)<abs(size(src,ordered)-target):ordered.append(uid)
    for uid in reversed(rank):
        if uid in ordered and len(ordered)>1:
            smaller=[x for x in ordered if x!=uid]
            if abs(size(src,smaller)-target)<abs(size(src,ordered)-target):ordered=smaller
    return [x for x in all_ids(src) if x in ordered]
def fallback(src,reason,**extra):return dict(selected_ids=all_ids(src),status='original_retained',reason=reason,**extra)

def construct(ex,src,arm,target):
    payload=dict(claim=ex['claim'],physician_label=ex['physician_label'],source_prefix=src['prefix'],source_units=src['units'],
                 budget_proxy_tokens=target,proxy_definition='count English words, numbers and punctuation; not actual model tokens')
    j=api.freeze_job('construct',arm,ex['proposition_id'],ex['sid'],body(COMMON+(P_GOAL if arm=='P4' else Q_GOAL),payload))
    obj,receipt=api.call_json(j)
    base=dict(constructor_receipt=receipt,constructor_output=obj,budget_proxy_tokens=target)
    if not isinstance(obj,dict) or type(obj.get('preserve_full')) is not bool or not valid_ids(obj.get('selected_ids'),src):
        return fallback(src,'constructor_invalid_no_content_retry',**base)
    if obj['preserve_full']:return fallback(src,'constructor_uncertain',**base)
    ids=obj['selected_ids'];rank=obj.get('priority_ids')
    if not valid_ids(rank,src) or set(rank)!=set(all_ids(src)):return fallback(src,'invalid_priority_list',**base)
    if arm=='Q4':ids=match_budget(src,ids,rank,target)
    candidate=render_reference(src,ids);source_check(ex['reference'],src,ids,candidate)
    check_payload=dict(claim=ex['claim'],source_prefix=src['prefix'],source_units=src['units'],selected_ids=ids,candidate_reference=candidate)
    assert 'physician_label' not in check_payload
    cj=api.freeze_job('review',arm,ex['proposition_id'],ex['sid'],body(CHECK,check_payload))
    checked,review_receipt=api.call_json(cj)
    base.update(initial_selected_ids=ids,review_receipt=review_receipt,review_output=checked)
    if not isinstance(checked,dict) or not valid_ids(checked.get('missing_ids'),src,True) or not valid_ids(checked.get('distorted_ids'),src,True) or type(checked.get('uncertain_after_adding_missing_ids')) is not bool:
        return fallback(src,'review_invalid_no_content_retry',**base)
    if checked['uncertain_after_adding_missing_ids'] or checked['distorted_ids']:
        return fallback(src,'review_unresolved',**base)
    repaired=[u for u in all_ids(src) if u in set(ids)|set(checked['missing_ids'])]
    final=render_reference(src,repaired);source_check(ex['reference'],src,repaired,final)
    return dict(selected_ids=repaired,status='extracted' if final!=ex['reference'] else 'original_retained',
                reason='single_source_id_addition_repair' if checked['missing_ids'] else 'source_check_no_additions',**base)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    frozen=OUT/'constructor_freeze.json'
    examples=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl')
    units={x['proposition_id']:unitize(x['reference']) for x in examples}
    if not frozen.exists():
        put(OUT/'source_units.json',units)
        put(frozen,dict(created_utc=now(),cap=20,constructor_cap=2,model=BUILDER,price_per_million=[.2,2],
            price_checked_utc=now(),price_url='https://help.aliyun.com/zh/model-studio/qwen3-5-flash',
            prompts=dict(common=COMMON,P=P_GOAL,Q=Q_GOAL,review=CHECK),ratio=.5,short_reference_chars=1200,
            head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            sources={p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl',
                ROOT/'outputs/087_f4_evidence_intervention/templates.json',ROOT/'docs/088_Codex_保留判定依据的固定示例压缩_执行提示词.md',
                TASK/'protocol.md',TASK/'common088.py',TASK/'api088.py',TASK/'construct088.py']},source_units_sha256=sha(OUT/'source_units.json')))
    f=read(frozen)
    for rel,d in f['sources'].items():assert sha(ROOT/rel)==d,rel
    assert sha(OUT/'source_units.json')==f['source_units_sha256']
    records=[];arms={a:copy.deepcopy(examples) for a in ARMS}
    for i,ex in enumerate(examples):
        ep=OUT/'construction'/f'slot{i+1}.json';src=units[ex['proposition_id']]
        if ep.exists():rec=read(ep)
        else:
            if len(ex['reference'])<=1200 or len(src['units'])==1:
                p=fallback(src,'short_or_single_unit');q=fallback(src,'same_short_or_single_unit')
            else:
                p=construct(ex,src,'P4',round(token_proxy(ex['reference'])*.5))
                if p['status']=='original_retained':q=fallback(src,'same_P_original_slot')
                else:
                    target=size(src,p['selected_ids']);q=construct(ex,src,'Q4',target)
                    tolerance=max(round(.05*target),max(x['proxy_tokens'] for x in src['units']))
                    if q['status']=='original_retained' or abs(size(src,q['selected_ids'])-target)>tolerance:
                        p=dict(**{k:v for k,v in p.items() if k not in ('selected_ids','status','reason')},selected_ids=all_ids(src),status='original_retained',reason='symmetric_Q_safety_or_length_fallback')
                        q=dict(**{k:v for k,v in q.items() if k not in ('selected_ids','status','reason')},selected_ids=all_ids(src),status='original_retained',reason='symmetric_Q_safety_or_length_fallback')
            rec=dict(ordinal=i+1,id=ex['proposition_id'],sid=ex['sid'],claim=ex['claim'],label=ex['physician_label'],P4=p,Q4=q)
            put(ep,rec)
        for a in ('P4','Q4'):
            reference=render_reference(src,rec[a]['selected_ids']);source_check(ex['reference'],src,rec[a]['selected_ids'],reference)
            arms[a][i]['reference']=reference
            rec[a]['reference_chars']=len(reference);rec[a]['proxy_tokens']=token_proxy(reference)
        rec['original_chars']=len(ex['reference']);rec['original_proxy_tokens']=token_proxy(ex['reference']);records.append(rec)
    old=read(ROOT/'outputs/087_f4_evidence_intervention/templates.json');base=old['systems']['B'];header=old['header']
    systems={a:render_system(base,header,arms[a]) for a in ARMS};assert systems['F4']==old['systems']['F4']
    put(OUT/'demonstrations.json',arms);put(OUT/'construction_summary.json',records)
    put(OUT/'templates.json',dict(systems=systems,hashes={a:h(v) for a,v in systems.items()},chars={a:len(v) for a,v in systems.items()},
        measurable=systems['P4']!=systems['F4'],P_Q_identical=systems['P4']==systems['Q4']))
    text(OUT/'source_changes.diff','\n'.join(''.join(difflib.unified_diff(examples[i]['reference'].splitlines(True),arms[a][i]['reference'].splitlines(True),
        fromfile=f'F4/slot{i+1}',tofile=f'{a}/slot{i+1}')) for a in ('P4','Q4') for i in range(4)))
    put(OUT/'demonstration_freeze.json',dict(created_utc=now(),constructor_freeze_sha256=sha(frozen),
        files={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='run.lock'},
        target_evaluation_GT_used=False,judge_main_calls=0))
    rows,_,_=api.state();print(canonical(dict(measurable=systems['P4']!=systems['F4'],P_Q_identical=systems['P4']==systems['Q4'],
        system_chars={a:len(v) for a,v in systems.items()},cost=sum(x['cost_or_unknown_cny'] for x in rows),
        slots=[{k:r[k] for k in ('ordinal','original_chars','P4','Q4')} for r in records])))

if __name__=='__main__':main()
