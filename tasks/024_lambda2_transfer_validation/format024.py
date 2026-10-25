"""User-authorized, pre-performance, lossless duplicate-key repair for024 only."""
import json
import common024 as original
from common024 import *

def fold_json(text,events,scope):
    def pairs(items):
        obj={}
        for key,value in items:
            if key in obj:
                # Serialized JSON equality distinguishes bool/int/float and preserves arrays/text.
                require(canonical(obj[key])==canonical(value),'Conflicting duplicate JSON key: '+key)
                events.append(dict(scope=scope,key=key,values_identical=True))
            else:obj[key]=value
        return obj
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))

def parse(tr,scored):
    prior=old.prior.parse(tr,scored)
    events=[]
    if tr.get('http_status')!=200:return prior
    try:
        native=fold_json(tr['body_text'],events,'native_response')
        content=native['choices'][0]['message'].get('content')
        answer=fold_json(content,events,'assistant_content')
        native['choices'][0]['message']['content']=canonical(answer)
        normalized=dict(tr,body_text=canonical(native))
        result=old.prior.parse(normalized,scored)
        # Keep original assistant text in derived output too; native receipt is never changed.
        result['output_text']=content
        result['format_repair']=dict(version='024_lossless_duplicates_v1',folded=events,original_status=prior['status'],original_errors=prior['errors'])
        return result
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        result=dict(prior,status='invalid')
        result['format_repair']=dict(version='024_lossless_duplicates_v1',folded=[],repair_error=str(exc)[:160],original_status=prior['status'],original_errors=prior['errors'])
        return result

def verify_inputs():
    jobs=original.verify_inputs()
    m=read(OUT/'amendment_001/manifest.json')
    for p,h in m['sha256'].items():require(file_hash(ROOT/p)==h,'Amendment changed: '+p)
    return jobs

def load_attempts(jobs):
    byid={j['request_id']:j for j in jobs};attempts=[];terminal={}
    for p in sorted((OUT/'attempts').glob('*/request.json')):
        r=read(p);j=byid[r['request_id']]
        require(r['body']==j['body'] and r['body_sha256']==fingerprint(j['body']),'Request mismatch')
        require(r['reservation_cny']==bound(j),'Reservation mismatch')
        a=dict(request_id=j['request_id'],attempt_dir=p.parent.relative_to(OUT).as_posix(),model_key=j['model_key'],charge_cny=bound(j),charge_basis='unresolved_attempt_reservation',http_status=None)
        rp=p.parent/'receipt.json'
        if rp.exists():
            t=read(rp);require(t['request_sha256']==file_hash(p),'Receipt binding mismatch')
            tr=t['transport'];cost,basis=charge(j,tr);a.update(charge_cny=cost,charge_basis=basis,http_status=tr['http_status'])
            if tr['http_status']==200:
                require(j['request_id'] not in terminal,'Duplicate terminal answer')
                parsed=parse(tr,j['arm']=='S')
                require(parsed.get('model_returned')==j['body']['model'],'Unexpected returned model')
                terminal[j['request_id']]=parsed
        attempts.append(a)
    return attempts,terminal
