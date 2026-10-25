"""028 task-owned inputs, trace parser, and immutable API accounting."""
from pathlib import Path
import sys,json,re,copy
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/028_traceable_claim_evidence_verification'
sys.path.insert(0,str(ROOT/'tasks/024_lambda2_transfer_validation'))
import core024 as api
from transport_direct024 import DirectClient
sys.path.insert(0,str(ROOT/'tasks/025_lambda_flip_risk_separability'))
import common025 as risk
import frontier025_numeric as frontier
MODEL='deepseek-v4-flash-0731';CAP=80.;LABELS=api.LABELS;VALID=api.VALID
read=api.read;lines=api.lines;csvread=api.csvread;csvwrite=api.csvwrite;put=api.put;now=api.now;require=api.require;sha=api.file_hash;canonical=api.canonical;fingerprint=api.fingerprint;bound=api.bound;charge=api.charge

TRACE_INSTRUCTION='''Return one JSON object with claim_coverage, requirements, and summary.
Treat this as a claim-to-evidence verification table, not a generic clinical checklist.
First identify the minimal material requirements actually asserted by THIS proposition. Separate a factual event from any material attribute, scope, or relationship it asserts when each needs separate evidence. Use usually 2-6 rows, at most 8; a genuinely single requirement may have one row. Do not add requirements absent from the proposition. Account for every material part; do not omit a difficult part to obtain support.
For every row:
- claim_quote: an exact contiguous quote from the proposition identifying the requirement (overlapping quotes are allowed).
- requirement: a short faithful statement of what that text requires, preserving its strength, qualifiers and reference frame.
- evidence_fact: what the supplied reference actually states for this requirement; keep facts distinct from your interpretation.
- relation: supported, contradicted, unaddressed, or uncertain.
supported means evidence supports the actual requirement, including equivalent wording or an implication grounded in the text without new patient facts. Do not demand an exact restatement when the same fact is established. contradicted requires an actual incompatibility, not mere absence. unaddressed means the needed fact or relationship is not established in this reference. uncertain means the correspondence or meaning cannot be determined reliably. Missing information must not be fabricated.
- evidence: objects containing reference_id (the existing local integer reference number, not note ID) and quote (a short exact contiguous quotation from THAT entry; whitespace may be normalized). Supply at least one quote for supported or contradicted. For unaddressed/uncertain cite related material if present, otherwise use []. Do not use ellipses, paraphrases or invented quotations. Date/header text is permissible only when actually present in the cited entry.
Preserve the original proposition's strength: a possibility is not certainty, a focus is not exclusivity, a local time scope is not the entire stay, and the absence of a statement is not an explicit negative fact. Do not insert extra medical prerequisites or silently repair the proposition. If a reference frame is ambiguous, record that ambiguity without inventing an anchor.
claim_coverage is complete only if your rows account for all material requirements without strengthening or weakening the claim; otherwise uncertain. This is a coverage assessment, not a Supported probability. summary briefly describes the coverage and evidence relationship. No overall verdict or label_scores. Give concise observable findings, not a transcript of private deliberation. No Markdown fences or text outside JSON.
'''

def body(text,reference,arm):
    b=api.old.body(text,reference,False);b['model']=MODEL;b['max_tokens']=4096
    if arm=='trace':
        base=b['messages'][0]['content'].split('Return one JSON object only')[0];b['messages'][0]['content']=base+TRACE_INSTRUCTION
        string=dict(type='string');ev=dict(type='object',additionalProperties=False,required=['reference_id','quote'],properties=dict(reference_id=dict(type='integer'),quote=string))
        req=dict(type='object',additionalProperties=False,required=['claim_quote','requirement','evidence_fact','relation','evidence'],properties=dict(claim_quote=string,requirement=string,evidence_fact=string,relation=dict(type='string',enum=['supported','contradicted','unaddressed','uncertain']),evidence=dict(type='array',items=ev)))
        schema=dict(type='object',additionalProperties=False,required=['claim_coverage','requirements','summary'],properties=dict(claim_coverage=dict(type='string',enum=['complete','uncertain']),requirements=dict(type='array',minItems=1,maxItems=8,items=req),summary=string))
        b['response_format']=dict(type='json_schema',json_schema=dict(name='claim_evidence_trace',strict=True,schema=schema))
    require(arm in ('repeat','trace'),'Unknown arm');require(json.loads(b['messages'][1]['content'])==dict(proposition=text,reference=reference),'Input whitelist')
    return b

def matches(quote,text):
    if not isinstance(quote,str) or not quote.strip():return []
    return [[m.start(),m.end()] for m in re.finditer(r'\s+'.join(re.escape(s) for s in quote.split()),text)]

def entries(reference):
    starts=list(re.finditer(r'(?m)^(\d+)\. Date:',reference));return {int(m.group(1)):(m.start(),reference[m.start():starts[i+1].start() if i+1<len(starts) else len(reference)]) for i,m in enumerate(starts)}

def trace_parse(tr,job):
    out=dict(status='invalid_core_fields',keep=False,rows=[],errors=[],adherence=[],fully_traceable=False,relation_only_keep=False)
    if tr.get('http_status')!=200:out['errors']=['no_http200'];return out
    try:
        native=api.plain(api.loads(tr['body_text']));choice=native['choices'][0];content=choice['message']['content'];out.update(output_text=content,usage=native.get('usage'),model_returned=native.get('model'),response_id=native.get('id'),finish_reason=choice.get('finish_reason'))
        require(isinstance(content,str),'missing_content')
        try:obj=api.loads(content)
        except (ValueError,TypeError):obj=api.partial_object(content);out['adherence'].append('incomplete_json_decodable_core')
        require(isinstance(obj,api.Object),'not_object');coverage=api.unique(obj,'claim_coverage');require(coverage in ('complete','uncertain'),'invalid_coverage')
        versions=api.values(obj,'requirements');require(bool(versions),'missing_requirements');require(all(canonical(v)==canonical(versions[0]) for v in versions),'conflicting_requirements')
        reqs=versions[0];require(type(reqs) is list and 1<=len(reqs)<=8,'invalid_requirements_array');payload=json.loads(job['body']['messages'][1]['content']);refs=entries(payload['reference']);rows=[]
        for i,r in enumerate(reqs):
            require(isinstance(r,api.Object),'invalid_requirement_object');quote=api.unique(r,'claim_quote');relation=api.unique(r,'relation');ev=api.unique(r,'evidence');require(isinstance(quote,str) and relation in ('supported','contradicted','unaddressed','uncertain') and type(ev) is list,'invalid_row_core')
            spans=matches(quote,payload['proposition']);citations=[];row_flags=[]
            if not spans:row_flags.append('claim_quote_not_found')
            for e in ev:
                require(type(e) is dict and type(e.get('reference_id')) is int and isinstance(e.get('quote'),str),'invalid_evidence_core')
                rid=e['reference_id'];offset,entry=refs.get(rid,(0,''));locations=matches(e['quote'],entry);citations.append(dict(**e,valid=bool(locations),reference_spans=[[offset+a,offset+b] for a,b in locations]))
                if not locations:row_flags.append('evidence_quote_not_found')
            if relation in ('supported','contradicted') and not ev:row_flags.append('required_citation_missing')
            prose={}
            for key in ('requirement','evidence_fact'):
                try:val=api.unique(r,key);require(isinstance(val,str) and bool(val.strip()),'empty_'+key);prose[key]=val
                except (ValueError,TypeError):prose[key]=None;row_flags.append('explanation_format_'+key)
            rows.append(dict(index=i,claim_quote=quote,claim_spans=spans,relation=relation,evidence=citations,diagnostics=row_flags,**prose))
        try:summary=api.unique(obj,'summary');require(isinstance(summary,str),'invalid_summary')
        except (ValueError,TypeError):summary=None;out['adherence'].append('summary_format_anomaly')
        if choice.get('finish_reason')!='stop':out['adherence'].append('non_stop_finish')
        if choice['message'].get('reasoning_content'):out['adherence'].append('unexpected_thinking')
        if len(versions)>1:out['adherence'].append('identical_requirements_duplicate')
        semantic=coverage=='complete' and all(r['relation']=='supported' for r in rows)
        grounded=all(r['claim_spans'] and r['evidence'] and all(e['valid'] for e in r['evidence']) for r in rows)
        diagnostics=[d for r in rows for d in r['diagnostics']];out['adherence']+=diagnostics
        out.update(status='valid_with_format_anomaly' if out['adherence'] else 'valid',claim_coverage=coverage,rows=rows,summary=summary,keep=bool(semantic and grounded),fully_traceable=not diagnostics,relation_only_keep=semantic)
    except (ValueError,TypeError,KeyError,IndexError) as exc:out['errors'].append(str(exc)[:180])
    return out

def parse(tr,job):
    if job['arm']=='trace':out=trace_parse(tr,job)
    else:
        out=api.parse(tr,False);out['keep']=out['status'] in VALID and out['verdict']=='Supported'
    if out.get('model_returned') not in (None,MODEL):out.update(status='invalid_core_fields',keep=False);out['errors'].append('unexpected_model')
    return out

def verify_inputs():
    for p,h in read(OUT/'preparation_001/manifest.json')['sha256'].items():require(sha(ROOT/p)==h,'Frozen input changed: '+p)
    return lines(OUT/'preparation_001/jobs.jsonl')

def load_attempts(jobs):
    byid={j['request_id']:j for j in jobs};attempts=[];terminal={}
    for p in sorted((OUT/'attempts').glob('*/request.json')):
        req=read(p);j=byid[req['request_id']];require(req['body']==j['body'] and req['body_sha256']==fingerprint(j['body']),'Request mismatch');require(req['reservation_cny']==bound(j),'Reservation mismatch')
        a=dict(request_id=j['request_id'],proposition_id=j['proposition_id'],group=j['group'],arm=j['arm'],attempt_dir=p.parent.relative_to(OUT).as_posix(),http_status=None,charge_cny=bound(j),charge_basis='unresolved_attempt_reservation');rp=p.parent/'receipt.json'
        if rp.exists():
            receipt=read(rp);require(receipt['request_sha256']==sha(p),'Receipt binding');tr=receipt['transport'];cost,basis=charge(j,tr);a.update(http_status=tr['http_status'],charge_cny=cost,charge_basis=basis)
            if tr['http_status']==200:require(j['request_id'] not in terminal,'Repeated HTTP200');terminal[j['request_id']]=parse(tr,j)
        attempts.append(a)
    return attempts,terminal
