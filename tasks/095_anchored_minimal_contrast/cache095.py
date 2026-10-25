"""Repo-wide native-request inventory; exact fixed C48, no correctness selection."""
import copy,json,subprocess,sys
from collections import Counter,defaultdict
import common095 as c
sys.path.insert(0,str(c.ROOT/'tasks/090_demo_constructor_repair_validation'))
from analyze090 import parse_arm
def signature(body):
    b=copy.deepcopy(body);msgs=b.pop('messages')
    assert len(msgs)==2 and msgs[0]['role']=='system' and msgs[1]['role']=='user'
    for k,v in [('n',1),('stream',False),('top_p',1)]:b.setdefault(k,v)
    return c.h(c.canonical(dict(parameters=b,system=msgs[0]['content'])))
def body_of(req):
    if isinstance(req.get('job'),dict) and isinstance(req['job'].get('body'),dict):return req['job']['body'],req['job']
    if isinstance(req.get('body'),dict):return req['body'],req
    if isinstance(req.get('request_body'),dict):return req['request_body'],req
    return None,None
def main():
    c.OUT.mkdir(parents=True,exist_ok=True);c.PRIVATE.mkdir(parents=True,exist_ok=True)
    inp=c.lines(c.ROOT/'.local_models/092/inputs.jsonl');byid={r['proposition_id']:r for r in inp};lookup=defaultdict(list)
    for r in inp:lookup[c.h(r['text']+'\0'+r['reference'])].append(r['proposition_id'])
    template=c.read(c.ROOT/'.local_models/094/judge_template.json');sig=signature(template);c.put(c.PRIVATE/'judge_template.json',template)
    paths=subprocess.check_output(['rg','--files','-uu','outputs','.local_models','-g','request.json','-g','!**/venv/**','-g','!**/site-packages/**'],cwd=c.ROOT,text=True).splitlines()
    candidates=[];counts=Counter();variants=Counter();formats=Counter();unpaired=[]
    for i,name in enumerate(paths):
        p=c.ROOT/name
        if '/095/' in p.as_posix() or '/095_anchored_' in p.as_posix():continue
        try:
            req=c.read(p);body,job=body_of(req)
            if body is None:formats[str(sorted(req.keys()))]+=1;continue
            if body.get('model')!=c.MODEL or body.get('enable_thinking') is not True or body.get('reasoning_effort')!='high':counts['different_model_or_thinking']+=1;continue
            try:actual_sig=signature(body)
            except (AssertionError,KeyError):counts['different_envelope']+=1;continue
            if actual_sig!=sig:counts['different_prompt_or_params']+=1;variants[actual_sig]+=1;continue
            payload=json.loads(body['messages'][1]['content'])
            if set(payload)!={'proposition','reference'}:counts['extra_payload']+=1;continue
            key=c.h(payload['proposition']+'\0'+payload['reference']);ids=lookup.get(key,[])
            if not ids:counts['different_actual_claim_or_reference']+=1;continue
            pid=next((str(job[k]) for k in ['proposition_id','id'] if str(job.get(k,'')) in ids),None)
            assignment='explicit_id'
            if pid is None and len(ids)==1:pid=ids[0];assignment='unique_exact_input'
            if pid is None:counts['ambiguous_id']+=1;continue
            rp=p.parent/'receipt.json'
            if not rp.exists():counts['no_receipt']+=1;continue
            rec=c.read(rp);tr=rec.get('transport',rec)
            if tr.get('http_status')!=200:counts['not_HTTP200']+=1;continue
            native=json.loads(tr['body_text'])
            if native.get('model')!=c.MODEL:counts['returned_model_mismatch']+=1;continue
            parsed,labels=parse_arm(tr,None)
            parsed['core_invalid_no_imputation']=parsed.pop('fallback_used');parsed['raw_invalid_no_imputation']=parsed.pop('raw_fallback_used')
            when=tr.get('started_utc') or tr.get('ended_utc') or req.get('created_utc') or req.get('utc') or '9999'
            candidates.append(dict(id=pid,time=when,request_path=p.relative_to(c.ROOT).as_posix(),receipt_path=rp.relative_to(c.ROOT).as_posix(),request_sha256=c.sha(p),receipt_sha256=c.sha(rp),signature=sig,body_sha256=c.h(c.canonical(body)),reference_sha256=c.h(payload['reference']),claim_sha256=c.h(payload['proposition']),id_assignment=assignment,parsed=parsed,labels=labels))
            counts['compatible_success']+=1
        except (ValueError,KeyError,TypeError,AssertionError) as e:counts['unrecognized_or_invalid_transport']+=1;unpaired.append(dict(path=name,error=type(e).__name__))
        if (i+1)%5000==0:print('scanned',i+1,'accepted',len(candidates),flush=True)
    candidates.sort(key=lambda r:(r['time'],r['request_path'],r['receipt_path']));selected={}
    for r in candidates:selected.setdefault(r['id'],r)
    missing=sorted(set(byid)-set(selected),key=lambda x:c.h('095/baseline/'+x))
    c.putl(c.OUT/'cache_candidates.jsonl',candidates);c.putl(c.OUT/'cache_selected.jsonl',[selected[k] for k in sorted(selected)]);c.putl(c.OUT/'baseline_missing_initial.jsonl',[dict(id=pid,reference_sha256=c.h(byid[pid]['reference']),source=byid[pid]['source']) for pid in missing])
    c.putl(c.OUT/'reference_inventory.jsonl',[dict(id=r['proposition_id'],claim_sha256=c.h(r['text']),reference_sha256=c.h(r['reference']),source=r['source']) for r in inp])
    stats=dict(utc=c.now(),universe=len(byid),requests_scanned=len(paths),compatible_receipts=len(candidates),covered=len(selected),missing=len(missing),valid_selected=sum(r['parsed']['valid'] for r in selected.values()),raw_valid_selected=sum(r['parsed']['raw_valid'] for r in selected.values()),rejections=dict(counts),unknown_request_formats=dict(formats),different_signature_counts=dict(variants),selected_sources=dict(Counter(r['request_path'].split('/')[1] for r in selected.values())),reference_sources=dict(Counter(r['source'] for r in inp)),template_signature=sig,input_sha256=c.sha(c.ROOT/'.local_models/092/inputs.jsonl'),code_sha256=c.sha(c.TASK/'cache095.py'),selection='earliest successful timestamp then request/receipt path; no validity or correctness preference')
    c.put(c.OUT/'cache_inventory.json',stats);c.putl(c.OUT/'cache_scan_exceptions.jsonl',unpaired);c.progress('A_cache','Completed repo-wide exact-input native request inventory.');print(stats,flush=True)
if __name__=='__main__':main()
