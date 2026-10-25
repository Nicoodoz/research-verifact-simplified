"""Materialize eligible single-component screening with one contemporaneous baseline."""
from pathlib import Path
import argparse,copy
import study013 as s
import mechanisms013 as m
from prepare013 import source_data,save_jobs
from io013 import stage,rerank_scores

def chosen():
    selection=s.read_json(s.OUT/'preparation_001/selection.json')
    ids=set(selection['selected_ids']);items,pp,notes,prompts=source_data()
    return [x for x in items if x['proposition_id'] in ids],pp,notes,prompts

def auxiliary():
    gate=s.read_json(s.OUT/'unit_analysis_001/gate.json');methods=gate['eligible_methods']
    items,pp,notes,prompts=chosen();jobs=[]
    for x in items:
        if 'wide_candidates' in methods:jobs.append(m.rerank_job(x,pp))
        if 'selector' in methods:jobs.append(m.selector_job(x,pp))
    return save_jobs('screen_aux',jobs,dependencies=[s.OUT/'preparation_001/manifest.json',s.OUT/'unit_analysis_001/gate.json'])

def judge():
    methods=s.read_json(s.OUT/'unit_analysis_001/gate.json')['eligible_methods']
    items,pp,notes,prompts=chosen();values,attempts=stage('screen_aux')
    records=[];jobs={};assign=[]
    # Repeat probes are selected using original fixed cohort metadata/ID only.
    repeats=set()
    for sid in sorted({x['subject_id'] for x in items}):
        for author in ('llm','human'):
            opts=[x for x in items if x['subject_id']==sid and x['author_type']==author]
            repeats.add(min(opts,key=lambda x:s.pilot.digest_text('013/repeat/v1:'+x['proposition_id']))['proposition_id'])
    for x in items:
        result={'baseline':copy.deepcopy(x['retrieval']['C48'])};errors={}
        if 'contract' in methods:result['contract']=copy.deepcopy(result['baseline'])
        if 'text_guard' in methods:result['text_guard']=m.text_guard(x,pp,notes)
        if 'wide_candidates' in methods:
            try:
                scores=rerank_scores(values['rerank:'+x['proposition_id']])
                result['wide_candidates']=s.core.select_evidence(m.wide_pool(x),scores,pp,x['admission'])
                result['refresh48']=s.core.select_evidence(x['retrieval']['C48']['candidate_ids'],scores,pp,x['admission'])
                result['wide_candidates']['real_rerank_scores']=scores
            except (AssertionError,KeyError,ValueError,TypeError) as e:
                # No manufactured scores or labels. These conditions remain absent.
                errors['wide_candidates']=str(e);errors['refresh48']=str(e)
        if 'selector' in methods:
            v=values['selector:'+x['proposition_id']]
            result['selector']=m.selected_evidence(x,pp,v['job'],v['native'])
        record=dict(proposition_id=x['proposition_id'],case_id=x['case_id'],subject_id=x['subject_id'],author_type=x['author_type'],
            text=x['text'],admission=x['admission'],retrieval=result,prejudge_errors=errors)
        records.append(record)
        for arm,r in result.items():
            body=(m.contract_body if arm=='contract' else s.judge_body)(x,r['reference'],prompts)
            digest=s.pilot.fingerprint(body);rid='screen:r0:'+digest
            jobs[rid]=dict(request_id=rid,kind='chat',body=body)
            assign.append(dict(proposition_id=x['proposition_id'],case_id=x['case_id'],arm=arm,round=0,request_id=rid,body_sha256=digest))
            if arm=='baseline' and x['proposition_id'] in repeats:
                rid='screen:r1:'+digest;jobs[rid]=dict(request_id=rid,kind='chat',body=body)
                assign.append(dict(proposition_id=x['proposition_id'],case_id=x['case_id'],arm=arm,round=1,request_id=rid,body_sha256=digest))
    out=s.OUT/'screen_inputs_001';out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/'inputs.jsonl',records)
    s.pilot.write_json(out/'repeats.json',sorted(repeats))
    s.pilot.write_json(out/'summary.json',dict(claims=len(records),arms=['baseline',*methods],prejudge_failures=sum(len(r['prejudge_errors']) for r in records),
        selector_fallbacks=sum(r['retrieval'].get('selector',{}).get('selector_status')=='fallback_invalid_or_missing' for r in records)))
    s.freeze(out,[s.OUT/'screen_aux_preparation_001/manifest.json',s.OUT/'live/screen_aux/state.json',s.OUT/'unit_analysis_001/gate.json'],[Path(__file__)])
    save_jobs('screen_judge',list(jobs.values()),assign,[out/'manifest.json'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('aux','judge'));a=p.parse_args()
    auxiliary() if a.phase=='aux' else judge()
