"""One neutral question, separate extraction, unchanged C48, matched final Judge."""
import copy,json,re,sys
import common094 as c
GEN='''Create ONE neutral open question for independent evidence reading of a clinical claim. Output JSON with question, claimed_value, answer_span, target, applicable. You see only the claim. Choose its most material event status, time, value, actor, destination, or relation as the target. answer_span MUST be an exact contiguous nonempty substring of the claim expressing the asserted answer; claimed_value faithfully states that answer, NOT a truth judgement. The question must NOT contain that answer, its paraphrase, a suggested alternative containing it, or the entire claim. Keep identifying clinical topic/event context, but do not presuppose that the claimed event occurred. Ask what, if anything, is documented, allow absence/uncertainty. Do not ask a yes/no confirmation. If occurrence itself is the target, ask openly about the relevant clinical course/status, not 'when did X happen'. Avoid losing actor/time scope needed to locate the same event. Do not add medical facts. One question only; no rationale, no answer to the question, no labels. If no meaningful neutral question can preserve identification while withholding the answer, applicable=false. question at most 350 characters; claimed_value and answer_span at most 200 each. target one of event,status,time,value,actor,relation,location.'''
QA='''Independently read ONLY the supplied EHR to answer the neutral question. If an unverified_claim is supplied, it is a hypothesis, NOT evidence; do not infer facts from it. Return JSON {"status":"answered|ambiguous|insufficient","candidates":[{"answer":"...","time":"...","state":"...","evidence":[{"reference_id":1,"quote":"exact contiguous EHR text"}]}]}. At most 2 candidates and 2 quotations per candidate. Preserve competing events, negation, temporal scope and planned versus completed status. Do not assume the event occurred. Do not use general medical knowledge to fill gaps. Every candidate needs an exact quotation from its cited numbered C48 entry. time/state are observed qualifiers, not invented facts; use unknown when absent. If the record is insufficient use status=insufficient and candidates=[]; this is NOT a three-class verdict. Each answer<=200 characters, time<=100, state<=80, quote<=200. No explanation, no clinical verdict, no private reasoning. Return JSON only.'''
FINAL='''The user also supplies auxiliary_question, claimed_value, and auxiliary_record. These are fallible generated reading aids, NOT additional EHR and NOT physician annotations. The original complete reference remains the sole patient evidence. Compare the proposition with independently traceable facts, checking quotations in that reference, event identity, time and status. Do not trust an auxiliary answer over the EHR; insufficient or absent answers alone do not imply Not Supported or Not Addressed. Judge the full original proposition under the original three-label contract and output the same schema. No requirement that every auxiliary field be answered to allow Supported.'''
def aux(system,payload,max_tokens):return dict(model=c.MODEL,messages=[dict(role='system',content=system),dict(role='user',content=c.canonical(payload))],enable_thinking=False,temperature=0,max_tokens=max_tokens,response_format={'type':'json_object'})
def gen_body(claim):return aux(GEN,{'claim':claim},1000)
def qa_body(row,q,arm):
    p=dict(question=q['question'],reference=row['reference'])
    if arm=='V':p['unverified_claim']=row['text']
    assert arm in ['V','Q']
    return aux(QA,p,2048)
def judge_body(template,row,q=None,record=None):
    b=copy.deepcopy(template);p=dict(proposition=row['text'],reference=row['reference'])
    if q is not None:
        b['messages'][0]['content']+='\n'+FINAL
        p.update(auxiliary_question=q['question'],claimed_value=q['claimed_value'],auxiliary_record=record)
    b['messages'][1]['content']=c.canonical(p)
    return b
def obj(tr):
    n=json.loads(tr['body_text']);s=n['choices'][0]['message'].get('content','').strip()
    if s.startswith('```'):s=re.sub(r'^```(?:json)?\s*|\s*```$','',s)
    o=json.loads(s);assert isinstance(o,dict)
    return o
def parse_question(tr,claim):
    try:
        q=obj(tr);assert q.get('applicable') is True
        for k,n in [('question',350),('answer_span',200),('claimed_value',200)]:assert isinstance(q[k],str) and 0<len(q[k])<=n
        assert q['answer_span'] in claim and q['answer_span'].lower() not in q['question'].lower()
        assert claim.lower() not in q['question'].lower()
        assert len(q['question'].encode())<=1200 and len(q['claimed_value'].encode())<=800
        return dict(valid=True,**{k:q[k] for k in ['question','answer_span','claimed_value','target']})
    except (ValueError,KeyError,TypeError,AssertionError):return dict(valid=False,error='question_format_or_literal_leak')
def entries(reference):
    starts=list(re.finditer(r'(?m)^(\d+)\. Date:',reference))
    return {int(m.group(1)):reference[m.start():starts[i+1].start() if i+1<len(starts) else len(reference)] for i,m in enumerate(starts)}
def parse_qa(tr,reference):
    try:
        o=obj(tr);assert o['status'] in ['answered','ambiguous','insufficient'] and isinstance(o['candidates'],list) and len(o['candidates'])<=2
        assert (o['status']=='insufficient')==(len(o['candidates'])==0)
        refs=entries(reference);citations=[];clean=[]
        for r in o['candidates']:
            for k,n in [('answer',200),('time',100),('state',80)]:assert isinstance(r[k],str) and 0<len(r[k])<=n
            assert 1<=len(r['evidence'])<=2
            ev=[]
            for e in r['evidence']:
                rid=e['reference_id'];quote=e['quote'];assert type(rid)is int and isinstance(quote,str) and 0<len(quote)<=200 and quote in refs.get(rid,'')
                ev.append(dict(reference_id=rid,quote=quote));citations.append(dict(reference_id=rid,quote_sha256=c.h(quote)))
            clean.append({**{k:r[k] for k in ['answer','time','state']},'evidence':ev})
        record=dict(status=o['status'],candidates=clean);assert len(c.canonical(record).encode())<=4000
        return dict(valid=True,record=record,citations=citations)
    except (ValueError,KeyError,TypeError,AssertionError):return dict(valid=False,record=dict(status='unavailable_invalid_auxiliary_output',candidates=[]),citations=[])
