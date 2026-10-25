"""024 user-authorized core-field evaluation parser; raw receipts remain immutable."""
import json
import common024 as original
from common024 import *
VALID=('valid','valid_with_format_anomaly')
class Object(list):pass
def loads(text):return json.loads(text,object_pairs_hook=Object,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def plain(value):
    if isinstance(value,Object):
        out={}
        for k,v in value:
            v=plain(v)
            require(k not in out or canonical(out[k])==canonical(v),'conflicting_duplicate_'+k)
            out[k]=v
        return out
    if isinstance(value,list):return [plain(v) for v in value]
    return value
def values(obj,key):return [v for k,v in obj if k==key]
def unique(obj,key,required=True):
    vs=values(obj,key);require(vs or not required,'missing_'+key)
    if not vs:return None
    vals=[plain(v) for v in vs]
    require(all(canonical(v)==canonical(vals[0]) for v in vals),'conflicting_duplicate_'+key)
    return vals[0]
def partial_object(text):
    """Recover only fully decoded leading top-level fields; never infer unfinished values."""
    dec=json.JSONDecoder(object_pairs_hook=Object);i=0
    while i<len(text) and text[i].isspace():i+=1
    require(i<len(text) and text[i]=='{','not_json_object');i+=1;out=Object();partial_key=None
    while True:
        try:
            while i<len(text) and text[i].isspace():i+=1
            k,i=dec.raw_decode(text,i);require(isinstance(k,str),'non_string_key');partial_key=k
            while i<len(text) and text[i].isspace():i+=1
            require(text[i]==':','missing_colon');i+=1
            while i<len(text) and text[i].isspace():i+=1
            v,i=dec.raw_decode(text,i);out.append((k,v));partial_key=None
            while i<len(text) and text[i].isspace():i+=1
            if i>=len(text) or text[i]!=',':break
            i+=1
        except (ValueError,IndexError):break
    require(partial_key not in ('verdict','label_scores'),'unfinished_core_field')
    return out
def parse(tr,scored):
    oldparse=old.prior.parse(tr,scored)
    r=dict(status='invalid_core_fields',verdict=None,scores=None,errors=[],adherence=[],original_status=oldparse['status'],original_errors=oldparse['errors'],parser_version='024_core_fields_v1')
    if tr.get('http_status')!=200:r['errors']=['no_http_200'];return r
    try:
        native=plain(loads(tr['body_text']));choice=native['choices'][0];content=choice['message'].get('content')
        r.update(model_returned=native.get('model'),usage=native.get('usage'),response_id=native.get('id'),output_text=content,finish_reason=choice.get('finish_reason'))
        require(isinstance(content,str),'missing_content')
        try:obj=loads(content)
        except (ValueError,TypeError):
            obj=partial_object(content);r['adherence'].append('incomplete_json_with_decodable_core')
        require(isinstance(obj,Object),'not_json_object')
        verdict=unique(obj,'verdict');require(verdict in LABELS,'invalid_verdict')
        scores=unique(obj,'label_scores') if scored else None
        if scored:
            require(isinstance(scores,dict) and set(scores)==set(LABELS),'missing_score_labels')
            require(all(type(v) is int and 0<=v<=100 for v in scores.values()),'invalid_score_type_or_range')
            require(sum(scores.values())==100,'score_sum_not_100')
        explanation={}
        for key,kind in [('reason',str),('checks',list)]:
            vv=values(obj,key)
            if len(vv)>1:r['adherence'].append(key+'_duplicate')
            try:
                value=unique(obj,key)
                require(isinstance(value,kind),'invalid_'+key)
                if key=='checks':
                    expected=['claim_summary','relevant_evidence','supporting_case','opposing_case','overall_assessment']
                    require([x.get('aspect') if isinstance(x,dict) else None for x in value]==expected,'check_names_or_count')
                explanation[key]=value
            except (ValueError,TypeError):
                r['adherence'].append('explanation_format_anomaly:'+key)
                explanation[key]=None  # No semantic merge or arbitrary first/last choice.
        for key in ('verdict','label_scores'):
            if len(values(obj,key))>1:r['adherence'].append('identical_core_duplicate:'+key)
        if choice.get('finish_reason')!='stop':r['adherence'].append('non_stop_finish_with_decodable_core')
        if choice['message'].get('reasoning_content'):r['adherence'].append('unexpected_thinking')
        r.update(status='valid_with_format_anomaly' if r['adherence'] else 'valid',verdict=verdict,scores=scores,parsed=dict(verdict=verdict,label_scores=scores,**explanation))
    except (ValueError,KeyError,TypeError,IndexError) as exc:r['errors'].append(str(exc)[:160])
    return r
def verify_inputs():
    jobs=original.verify_inputs()
    for name in ('amendment_001/manifest.json','amendment_002/manifest.json'):
        for p,h in read(OUT/name)['sha256'].items():require(file_hash(ROOT/p)==h,'Frozen amendment changed: '+p)
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
                if parsed.get('model_returned')!=j['body']['model']:
                    parsed['status']='invalid_core_fields';parsed['errors'].append('unexpected_model')
                terminal[j['request_id']]=parsed
        attempts.append(a)
    return attempts,terminal
