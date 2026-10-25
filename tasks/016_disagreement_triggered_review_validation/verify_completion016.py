"""Offline reconstruction and audit handoff for completed016; no service calls."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from copy import deepcopy
import argparse
import io
import os
import socket
import subprocess
import tempfile
import numpy as np
import common016 as c
from completion_io016 import ORIGINAL,OUT,collect,answers,ALI_MODEL
from analyze_completion016 import analyze
from prepare016 import prepare
from replay_history import check_history,MUTABLE_HISTORY_PATHS
from decisions016 import compose

def verify(out):
    c.require(not out.exists(),'Verification exists');out.mkdir(parents=True)
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Network forbidden in replay')):
        auth=c.read(OUT/'authority.json');c.check_hashes(auth['execution_sha256'])
        c.check_hashes(c.read(OUT/'evaluation_plan.json')['code_sha256'])
        c.require(auth['protocol_sha256']==c.file_hash(OUT/'protocol_amendment.json'),'Amendment changed')
        c.require(c.read(OUT/'protocol_amendment.json')['gate_code_sha256']==c.file_hash(c.TASK/'decisions016.py'),'Preregistered gate changed')
        history=check_history(c.read(ORIGINAL/'historical_protection_001.json'),bindings={});c.write_json(out/'history_check.json',history)
        handoffs=[]
        for name in ('handoff_001.json','recovery_001/handoff_001.json','v4_completion_001/handoff_001.json','finalization_001/handoff_001.json','finalization_001/handoff_002.json'):
            hashes=c.read(ORIGINAL/name)['files_sha256'];frozen={n:v for n,v in hashes.items() if n not in MUTABLE_HISTORY_PATHS}
            c.check_hashes(frozen);handoffs.append(dict(path=name,strict_files=len(frozen),mutable_navigation=[n for n in hashes if n in MUTABLE_HISTORY_PATHS]))
        c.write_json(out/'prior_handoffs.json',handoffs)
        for folder in (ORIGINAL/'stage1/preparation_002',ORIGINAL/'stage1/candidates_001',ORIGINAL/'stage1/base_preparation_001',OUT/'base',OUT/'review',OUT/'analysis_001'):
            c.check_manifest(folder)
        values,attempts,total=collect();a,prov=answers(values,True)
        prep=ORIGINAL/'stage1/preparation_002';can=ORIGINAL/'stage1/candidates_001';base=ORIGINAL/'stage1/base_preparation_001'
        shadow=out/'raw_replay';shadow.mkdir();(shadow/'protocol_002.md').write_bytes((ORIGINAL/'protocol_002.md').read_bytes())
        with patch.object(c,'OUT',shadow),redirect_stdout(io.StringIO()):prepare('stage1')
        rebuilt=shadow/'stage1/preparation_002';names=[p.name for p in prep.iterdir() if p.is_file() and p.name!='manifest.json']
        c.require(all(c.file_hash(prep/n)==c.file_hash(rebuilt/n) for n in names),'Raw/cohort replay mismatch')
        vectors={}
        for v in values.values():
            if v['job']['kind']!='embedding':continue
            native=c.pilot.strict_json(v['receipt']['transport']['body_text'])
            for x in native['data']:vectors[v['job']['text_ids'][x['index']]]=np.asarray(x['embedding'],dtype=np.float64)
        ids=c.read(can/'embedding_ids.json');c.require(np.array_equal(np.load(can/'vectors.npy',allow_pickle=False),np.asarray([vectors[k] for k in ids])),'Vector receipt mismatch')
        corpus=c.jsonlines(prep/'corpus.jsonl');passages={p['passage_id']:p for p in corpus}
        indices={sid:c.baseline.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp]) for sid in c.patient_ids('stage1') for pp in [[p for p in corpus if p['subject_id']==sid]] if pp}
        rankings={r['proposition_id']:r for r in c.jsonlines(can/'candidates.jsonl')};items={r['proposition_id']:r for r in c.jsonlines(base/'inputs.jsonl')}
        for item in c.jsonlines(prep/'inputs.jsonl'):
            pid=item['proposition_id'];ranks=indices[item['subject_id']].retrieve(item['text'],vectors[item['claim_embedding_id']]) if item['subject_id'] in indices else dict(bm25=[],dense=[],hybrid=[])
            pools={key+'48':c.baseline.candidates(ranks,key) for key in ('A','B','C')}
            c.require(c.canonical(dict(proposition_id=pid,rankings=ranks,candidate_ids=pools))==c.canonical(rankings[pid]),'Candidate reconstruction mismatch')
            union=sorted({p for pool in pools.values() for p in pool});scores={}
            if union:
                v=values['stage1:rerank:'+pid]
                c.require(v['job']['body']['query']==item['text'] and v['job']['body']['documents']==[passages[p]['search_text'] for p in union],'Rerank request mismatch')
                native=c.pilot.strict_json(v['receipt']['transport']['body_text']);scores={union[x['index']]:float(x['relevance_score']) for x in native['results']}
            packed=c.baseline.core.select_evidence(pools['C48'],scores,passages,item['admission'])
            c.require(c.canonical(dict(item,**packed,candidate_ids=pools['C48'],scores=scores))==c.canonical(items[pid]),'C48 reconstruction mismatch')
        prompts=c.read(prep/'judge_prompts.json');body_count=0
        for v in values.values():
            j=v['job']
            if j['kind']!='chat':continue
            item=items[j['proposition_id']];expected=c.judge_body(item,item['reference'],prompts,j['role'])
            if j['body']['model']==ALI_MODEL:expected['model']=ALI_MODEL
            c.require(expected==j['body'],'Actual Judge body differs from frozen construction')
            c.require(set(c.pilot.strict_json(expected['messages'][1]['content']))=={'proposition','reference'},'Hidden Judge input')
            body_count+=1
        dis={pid for pid,role in a if role=='qwen' and a[(pid,'qwen')]['verdict']!=a[(pid,'v4_first')]['verdict']}
        for role in ('v4_repeat','independent_review'):c.require({pid for pid,r in a if r==role}==dis,'Review trigger coverage differs')
        c.require({r['proposition_id'] for r in c.csvrows(OUT/'review/trigger.csv') if r['disagreement']=='True'}==dis,'Frozen trigger differs')
        with redirect_stdout(io.StringIO()):analyze(out/'analysis_replay')
        official=OUT/'analysis_001';content=[p.relative_to(official) for p in official.rglob('*') if p.is_file() and p.name!='manifest.json']
        c.require(all(c.file_hash(official/p)==c.file_hash(out/'analysis_replay'/p) for p in content),'Analysis replay mismatch')
        negative={}
        for name,fn in [('reserved_phase',lambda:c.patient_ids('confirmation')),('missing_review',lambda:compose([dict(v4_first='Supported',qwen='Not Addressed',v4_repeat='',independent_review='')])),
            ('illegal_label',lambda:compose([dict(v4_first='bad',qwen='Supported')])),
            ('body_tamper',lambda: c.check_hashes({(OUT/'base/jobs.jsonl').relative_to(c.ROOT).as_posix():'0'*64}))]:
            try:fn();negative[name]=False
            except ValueError:negative[name]=True
        c.require(all(negative.values()),'Negative boundary check failed')
        paths=set(auth['execution_sha256'])|{(c.TASK/n).relative_to(c.ROOT).as_posix() for n in ('analyze_completion016.py','render_completion016.py','verify_completion016.py','batch_completion016.py')}|{'tests/test_completion016.py','tests/test_aliyun.py','tests/test_finish016.py'}
        with tempfile.TemporaryDirectory(prefix='016-completion-checkout-') as temp:
            temp=Path(temp);env=dict(os.environ,GIT_INDEX_FILE=str(temp/'index'))
            def git(args):return subprocess.check_output(['git',*args],cwd=c.ROOT,env=env,stderr=subprocess.PIPE)
            git(['read-tree','HEAD']);git(['-c','core.autocrlf=false','add','--','.gitattributes',*sorted(paths)])
            dest=temp/'checkout';dest.mkdir();git(['-c','core.autocrlf=true','checkout-index','--prefix='+dest.as_posix()+'/','--',*sorted(paths)])
            c.require(all((c.ROOT/n).read_bytes()==(dest/n).read_bytes() for n in paths),'Windows byte drift')
        result=dict(status='executor_self_check_not_independent_audit',external_calls=0,raw_preparation_files=len(names),
            C48_reconstructed=601,actual_Judge_bodies_reconstructed=body_count,disagreements=len(dis),
            analysis_content_files_replayed=len(content),negative_checks=negative,windows_checkout_files=len(paths),
            historical_files=history['strict_unchanged_files'],whole_task_cny=total,no_reserved_test=True)
        c.write_json(out/'summary.json',result);print(c.canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=OUT/'verification_001');verify(p.parse_args().output.resolve())
