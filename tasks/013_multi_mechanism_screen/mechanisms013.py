"""Four single-component candidates. No GT/source text is an argument."""
import copy,re,json
from collections import Counter
import study013 as s

CONTRACT_INSTRUCTION='''Literal subject-predicate contract (only this additional operation):
The supplied contract contains two exact spans of the original proposition, not a corrected paraphrase. In claim_summary, reproduce the original proposition verbatim. In relevant_evidence, explicitly state what entity the predicate is asserted about in the proposition and what entity the cited record predicates it about. Use the literal grammatical subject, even if the sentence looks mistaken; never silently substitute a more plausible entity or intended statement. Evaluate the original subject-predicate pair with the unchanged shared label definitions. Keep the other four ordinary checks and the same 200-word total allowance. This is not a request for an event/time/status checklist or a new clinical interpretation. Do not infer patient evidence from the contract itself.'''

SELECTOR_INSTRUCTION='''Select an evidence SET for the unchanged clinical proposition from the supplied candidate records. These are the complete eligible C48 candidates, already ranked by the original claim. Select only supplied IDs, in priority order (most indispensable first), at most 16. Do not write new evidence, change the claim, request retrieval, or use knowledge as patient evidence. Prefer complementary records that together determine support or lack of support: keep actual counterevidence as well as support; avoid spending the budget on repeated versions of the same fact. A short examination header can be useful, while a generic billing tail is not automatically useful. Preserve distinct events if both matter; do not force a date or condition absent from the claim. You may select more than two records from a note when they supply different necessary information. The deterministic packer will admit whole records in your priority order within the same 8000-character budget as baseline; original chronological display is preserved. Respond with one JSON object containing exactly selected_ids (array of unique supplied IDs) and reason (concise explanation). The explanation never enters the final Judge. Do not predict the verification label.'''

def literal_contract(claim):
    # Conservative surface split at the first finite auxiliary; no correction,
    # coreference resolution, source access or new time/dose assertion.
    m=re.search(r'\s+(?:is|are|was|were|has|have|had|will|would|can|could|did|does|do)\b',claim,re.I)
    if not m or re.search(r'[,;:!?]',claim[:m.start()]):return None
    n=m.start()
    return dict(subject=claim[:n],predicate=claim[n:],subject_span=[0,n],predicate_span=[n,len(claim)],
                claim_sha256=s.pilot.digest_text(claim),operation='literal_subject_predicate_no_repair')

def contract_body(item,reference,prompts):
    body=s.judge_body(item,reference,prompts);contract=literal_contract(item['text'])
    if contract:
        body['messages'][0]['content']+='\n'+CONTRACT_INSTRUCTION
        body['messages'][1]['content']=s.pilot.canonical(dict(proposition=item['text'],reference=reference,claim_contract=contract))
    return body

def repair_passage(p,note):
    assert p['note_id']==note['ROW_ID'] and p['subject_id']==note['SUBJECT_ID']
    text=note['TEXT'];start,end=p['start'],p['end_exclusive']
    assert text[start:end]==p['text']
    lo=start;reason=None
    prefix=text[max(0,start-180):start]
    # Only a dangling lexical operator right at the cut, not a nearby negative sentence.
    m=re.search(r'\b(?:no|not|without|denies|denied|never)\s*$',prefix,re.I)
    if m:lo=max(0,start-180)+m.start();reason='dangling_polarity_operator'
    else:
        # Recover a preceding conditional clause only within this same list item,
        # with no completed sentence / paragraph / new list item in between.
        hits=list(re.finditer(r'\b(?:if|unless|provided that)\b',prefix,re.I))
        if hits:
            m=hits[-1];between=prefix[m.start():]
            if not re.search(r'[.!?;]|\n\s*\n|\n\s*\d+[.)]\s',between) and len(between)<=180:
                lo=max(0,start-180)+m.start();reason='conditional_prefix_at_cut'
    q=dict(p)
    if lo<start:q.update(start=lo,text=text[lo:end])
    return q,dict(passage_id=p['passage_id'],note_id=p['note_id'],old_start=start,new_start=lo,
        end_exclusive=end,added_characters=start-lo,reason=reason,raw_sha256=s.pilot.digest_text(text))

def text_guard(item,passages,notes):
    view=dict(passages);changes=[]
    for pid in item['retrieval']['C48']['candidate_ids']:
        q,change=repair_passage(passages[pid],notes[passages[pid]['note_id']]);view[pid]=q
        if change['added_characters']:changes.append(change)
    result=s.core.select_evidence(item['retrieval']['C48']['candidate_ids'],item['scores'],view,item['admission'])
    result['repairs']=changes
    return result

def wide_pool(item):
    ranks=item['rankings']
    # Include both full saved top80 lists, no new query/fusion formula/dense-only.
    return s.old.quota_candidates([x[0] for x in ranks['dense']],[x[0] for x in ranks['bm25']],160)

def rerank_job(item,passages):
    ids=sorted(wide_pool(item))
    return dict(request_id='rerank:'+item['proposition_id'],kind='rerank',passage_ids=ids,
        body=dict(model=s.RERANK_MODEL,query=item['text'],documents=[passages[k]['search_text'] for k in ids],
            top_n=len(ids),return_documents=False,max_chunks_per_doc=1))

def selector_job(item,passages):
    ids=sorted(item['retrieval']['C48']['candidate_ids'],key=lambda k:(-item['scores'][k],k))
    aliases={f'p{i:03d}':pid for i,pid in enumerate(ids,1)}
    records=[dict(id=a,text=passages[k]['text'],note_id=passages[k]['note_id'],date=passages[k]['date'],
        time=passages[k]['time'],category=passages[k]['category'],start=passages[k]['start'],end_exclusive=passages[k]['end_exclusive']) for a,k in aliases.items()]
    body=dict(model=s.CHAT_MODEL,messages=[dict(role='system',content=SELECTOR_INSTRUCTION),
        dict(role='user',content=s.pilot.canonical(dict(proposition=item['text'],candidates=records,character_budget=8000)))],
        temperature=0,max_tokens=1024,enable_thinking=False,n=1,stream=False,response_format={'type':'json_object'})
    return dict(request_id='selector:'+item['proposition_id'],kind='chat',body=body,aliases=aliases)

def selected_evidence(item,passages,job,native):
    try:
        choice=native['choices'][0]
        assert choice['finish_reason']=='stop' and native['model']==s.CHAT_MODEL
        obj=s.pilot.strict_json(choice['message']['content'])
        ids=obj['selected_ids'];assert isinstance(ids,list) and len(ids)<=16 and len(set(ids))==len(ids)
        assert all(isinstance(k,str) and k in job['aliases'] for k in ids)
        selected=[job['aliases'][k] for k in ids]
        # Priority selection is the treatment, not fabricated BGE scores.
        priority={k:len(selected)-i for i,k in enumerate(selected)}
        result=s.core.select_evidence(selected,priority,passages,item['admission'],max_per_note=16)
        result.update(selector_status='valid',selector_requested_ids=selected,selector_explanation=obj.get('reason',''),
            selection_order_basis='LLM priority, score fields in skips are priority only, never BGE')
    except (AssertionError,KeyError,TypeError,ValueError,IndexError):
        result=copy.deepcopy(item['retrieval']['C48']);result.update(selector_status='fallback_invalid_or_missing',selector_requested_ids=[])
    return result
