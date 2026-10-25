"""Offline audit handoff: strict material checks, C48/body rebuild, analysis replay."""
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack,redirect_stdout
import argparse
import io
import socket
import os
import subprocess
import tempfile
import numpy as np
import common016 as c
from replay_history import check_history
from io016 import load_phase
from analyze016 import analyze
from prepare016 import prepare

def verify(out):
    c.require(not out.exists(),'Verification already exists');out.mkdir(parents=True)
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket,'connect',side_effect=AssertionError('Offline verification must not access network')))
        c.require(not (c.OUT/'task_api.lock').exists(),'Active API phase')
        auth=c.read(c.OUT/'authority_001.json');c.check_hashes(auth['execution_sha256'])
        c.require(auth['task_cap_cny']==40 and auth['protocol_sha256']==c.file_hash(c.OUT/'protocol_002.md') and auth['prices_sha256']==c.file_hash(c.OUT/'prices_001.json'),'Authority/protocol drift')
        history=c.read(c.OUT/'historical_protection_001.json');history_check=check_history(history,bindings={})
        c.write_json(out/'history_check.json',history_check)
        old=c.read(c.OUT/'stage1/preparation_001/manifest.json');snap=c.OUT/'precharge_history_001'
        for key in ('files','dependencies'):c.check_hashes(old[key])
        for name,digest in old['code_sha256'].items():
            candidate=snap/Path(name).name if name.startswith(c.TASK.relative_to(c.ROOT).as_posix()+'/') else c.ROOT/name
            c.require(c.file_hash(candidate)==digest,'Old precharge code provenance changed')
        for name,digest in c.read(snap/'inventory.json').items():c.require(c.file_hash(snap/Path(name).name)==digest,'Precharge snapshot changed')
        # Explicit existing navigation allowlist only; all original computational materials strict.
        if (c.OUT/'deliverables_001/manifest.json').exists():c.check_manifest(c.OUT/'deliverables_001')
        root=c.OUT/'stage1';prep=root/'preparation_002';can=root/'candidates_001';base=root/'base_preparation_001';review=root/'review_preparation_001'
        for p in (prep,can,base,review,c.OUT/'analysis_001'):c.check_manifest(p)
        # Rebuild cohort, raw paragraphs and embeddings catalog from original data.
        shadow=out/'preparation_replay';shadow.mkdir();(shadow/'protocol_002.md').write_bytes((c.OUT/'protocol_002.md').read_bytes())
        with patch.object(c,'OUT',shadow),redirect_stdout(io.StringIO()):prepare('stage1')
        rebuilt=shadow/'stage1/preparation_002'
        prep_files=[p.name for p in prep.iterdir() if p.is_file() and p.name!='manifest.json']
        c.require(all(c.file_hash(prep/n)==c.file_hash(rebuilt/n) for n in prep_files),'Raw preparation replay mismatch')
        vv,_=load_phase('stage1_embedding');vectors={}
        for v in vv.values():
            c.require(v['status']=='received','Missing embedding')
            for x in v['native']['data']:vectors[v['job']['text_ids'][x['index']]]=np.asarray(x['embedding'],dtype=np.float64)
        ids=c.read(can/'embedding_ids.json');saved=np.load(can/'vectors.npy',allow_pickle=False)
        c.require(np.array_equal(saved,np.asarray([vectors[k] for k in ids])),'Saved vectors changed')
        corpus=c.jsonlines(prep/'corpus.jsonl');passages={p['passage_id']:p for p in corpus}
        indices={sid:c.baseline.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp]) for sid in c.patient_ids('stage1') for pp in [[p for p in corpus if p['subject_id']==sid]] if pp}
        oldcan={r['proposition_id']:r for r in c.jsonlines(can/'candidates.jsonl')};items={r['proposition_id']:r for r in c.jsonlines(base/'inputs.jsonl')}
        rr,_=load_phase('stage1_rerank');bc,_=load_phase('stage1_base_chat')
        if c.jsonlines(review/'jobs.jsonl'):rc,_=load_phase('stage1_review_chat')
        else:rc={}
        values={**bc,**rc}
        assignments=c.csvrows(base/'assignments.csv')+c.csvrows(review/'assignments.csv');prompts=c.read(prep/'judge_prompts.json')
        for item in c.jsonlines(prep/'inputs.jsonl'):
            pid=item['proposition_id'];ranks=indices[item['subject_id']].retrieve(item['text'],vectors[item['claim_embedding_id']]) if item['subject_id'] in indices else dict(bm25=[],dense=[],hybrid=[])
            pools={a+'48':c.baseline.candidates(ranks,a) for a in ('A','B','C')}
            c.require(c.canonical(dict(proposition_id=pid,rankings=ranks,candidate_ids=pools))==c.canonical(oldcan[pid]),'Candidate reconstruction mismatch')
            union=sorted({p for pool in pools.values() for p in pool});scores={}
            if union:
                v=rr['stage1:rerank:'+pid];c.require(v['job']['body']['query']==item['text'] and v['job']['body']['documents']==[passages[p]['search_text'] for p in union],'Rerank input changed')
                scores={union[x['index']]:float(x['relevance_score']) for x in v['native']['results']}
            packed=c.baseline.core.select_evidence(pools['C48'],scores,passages,item['admission'])
            c.require(c.canonical(dict(item,**packed,candidate_ids=pools['C48'],scores=scores))==c.canonical(items[pid]),'C48 reconstruction mismatch')
        for a in assignments:
            item=items[a['proposition_id']];expected=c.judge_body(item,item['reference'],prompts,a['role']);v=values[a['request_id']]
            c.require(expected==v['job']['body'] and c.fingerprint(expected)==a['body_sha256'],'Judge input/prompt mismatch')
            c.require(set(c.pilot.strict_json(expected['messages'][1]['content']))=={'proposition','reference'},'Judge input leak')
        norm={rid:c.normalize(v['job'],v['receipt']) for rid,v in bc.items()};labels={}
        for a in c.csvrows(base/'assignments.csv'):labels.setdefault(a['proposition_id'],{})[a['role']]=norm[a['request_id']]['verdict']
        expected={pid for pid,p in labels.items() if p['v4_first']!=p['qwen']}
        for role in ('v4_repeat','independent_review'):c.require({a['proposition_id'] for a in assignments if a['role']==role}==expected,'Reviews outside frozen disagreement trigger')
        c.require(set(labels)==set(items) and len(labels)==601,'Cohort drift')
        replay=out/'analysis_replay'
        with redirect_stdout(io.StringIO()):analyze(replay)
        official=c.OUT/'analysis_001';content=[p.relative_to(official) for p in official.rglob('*') if p.is_file() and p.name!='manifest.json']
        c.require(all(c.file_hash(official/p)==c.file_hash(replay/p) for p in content),'Analysis replay mismatch')
        # Isolated in-memory negatives; never mutate actual clinical material.
        negative={}
        from decisions016 import compose
        for name,fn in [('future_patient_phase',lambda:c.patient_ids('confirmation')),('invalid_role',lambda:c.judge_body(dict(text='synthetic',proposition_id='synthetic'),'synthetic',prompts,'union_review')),
            ('missing_disagreement_review',lambda:compose([dict(v4_first='Supported',qwen='Not Addressed',v4_repeat='',independent_review='')]))]:
            try:fn();negative[name]=False
            except ValueError:negative[name]=True
        c.require(all(negative.values()),'Boundary negative failed')
        # Actual Windows checkout into a disposable index, preserving the real worktree/index.
        paths=set(auth['execution_sha256'])|{p.relative_to(c.ROOT).as_posix() for p in c.TASK.glob('*.py')}|{'tests/test_review_validation016.py'}
        checkout=[]
        with tempfile.TemporaryDirectory(prefix='verifact016-checkout-') as temp:
            temp=Path(temp);env=dict(os.environ,GIT_INDEX_FILE=str(temp/'index'))
            def git(args):return subprocess.check_output(['git',*args],cwd=c.ROOT,env=env,stderr=subprocess.PIPE)
            git(['read-tree','HEAD']);git(['-c','core.autocrlf=false','add','--','.gitattributes',*sorted(paths)])
            dest=temp/'checkout';dest.mkdir();git(['-c','core.autocrlf=true','checkout-index','--prefix='+dest.as_posix()+'/','--',*sorted(paths)])
            for name in sorted(paths):checkout.append(dict(path=name,same_bytes=(c.ROOT/name).read_bytes()==(dest/name).read_bytes()))
        c.require(all(r['same_bytes'] for r in checkout),'Windows checkout changed frozen bytes');c.write_json(out/'checkout.json',checkout)
        result=dict(status='executor_self_check_passed_not_independent_audit',created_utc=c.now(),external_calls=0,
            protected_historical_files=len(history),raw_preparation_content_files=len(prep_files),C48_rebuilt=601,judge_bodies_rebuilt=len(assignments),
            disagreement_only_count=len(expected),analysis_content_files_replayed=len(content),negative_checks=negative,cap_cny=40,
            windows_checkout_files=len(checkout),mutable_historical_changes=[r['path'] for r in history_check['mutable_entries'] if r['changed']],
            final_confirmation_performed=False,reserved_test_selected_or_analyzed=False)
        c.write_json(out/'summary.json',result);print(c.canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'verification_001');verify(p.parse_args().output.resolve())
