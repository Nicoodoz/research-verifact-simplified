"""Read-only audit package for incomplete budget-stopped016; never computes efficacy."""
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import argparse
import socket
import os
import tempfile
import subprocess
import numpy as np
import common016 as c
from replay_history import check_history

def verify(out):
    c.require(not out.exists(),'Verification output exists');out.mkdir(parents=True)
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Network blocked during verification')):
        stop=c.OUT/'interruption_001';c.check_manifest(stop)
        if (c.OUT/'deliverables_001/manifest.json').exists():c.check_manifest(c.OUT/'deliverables_001')
        c.check_hashes(c.read(stop/'live_frozen_files.json'))
        auth=c.read(c.OUT/'authority_001.json');c.check_hashes(auth['execution_sha256'])
        c.require(auth['protocol_sha256']==c.file_hash(c.OUT/'protocol_002.md') and auth['task_cap_cny']==40,'Authority drift')
        history=check_history(c.read(c.OUT/'historical_protection_001.json'),bindings={});c.write_json(out/'history_check.json',history)
        root=c.OUT/'stage1';prep=root/'preparation_002';can=root/'candidates_001';base=root/'base_preparation_001'
        for folder in (prep,can,base):c.check_manifest(folder)
        c.require((c.OUT/'task_api.lock').exists(),'Budget-stop lock removed')
        ledger=c.read(stop/'reconciled_ledger.json');original=c.read(stop/'ledger_at_stop.json')
        c.require(original==c.read(c.OUT/'live/ledger.json'),'Live run changed after stop')
        alljobs={};successful={};total=0.;raw_n=0;unknown_n=0
        for phase,state in ledger['phases'].items():
            folder=c.OUT/'live'/phase;spec=c.read(folder/'manifest.json');c.require(c.fingerprint(spec)==state['run_id'],'Phase fingerprint')
            jobs=c.jsonlines(c.ROOT/spec['jobfile']);c.require(c.file_hash(c.ROOT/spec['jobfile'])==spec['jobs_sha256'],'Job file drift');seen=set()
            for j in jobs:
                alljobs[j['request_id']]=j;p=state['jobs'][j['request_id']];answers=[]
                for ptr in p['receipts']:
                    path=folder/ptr['file'];seen.add(path.name);c.require(c.file_hash(path)==ptr['sha256'],'Receipt drift');r=c.read(path);tr=r['transport']
                    c.require(r['request_id']==j['request_id'] and r['job_sha256']==c.fingerprint(j) and r['run_id']==state['run_id'],'Receipt/job binding')
                    fee,basis=c.cost(j,tr);c.require(abs(fee-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Receipt fee mismatch');total+=fee;raw_n+=1
                    if tr['http_status']==200:answers.append(r)
                c.require(len(answers)<=1,'A successful answer was regenerated')
                if answers:successful[j['request_id']]=answers[0]
                for u in p.get('unreceipted',[]):
                    c.require(abs(u['reservation']-c.bound(j))<1e-12,'Unknown reservation mismatch');total+=u['reservation'];unknown_n+=1
            c.require(seen=={p.name for p in folder.glob('receipt_*.json')},'Unbound raw receipt')
        summary=c.read(stop/'summary.json');c.require(abs(total-summary['total_used_or_reserved_cny'])<1e-8 and total<=40,'Whole task fee mismatch')
        predicted=[];vectors={};rerank={}
        for rid,r in successful.items():
            j=alljobs[rid];native=c.pilot.strict_json(r['transport']['body_text'])
            if j['kind']=='chat':
                n=c.normalize(j,r);c.require(n['status']=='success','Invalid saved partial answer')
                predicted.append(dict(proposition_id=j['proposition_id'],role=j['role'],verdict=n['verdict'],request_id=rid))
            elif j['kind']=='embedding':
                c.require(native['model']==c.baseline.EMBED_MODEL,'Embedding model')
                for x in native['data']:vectors[j['text_ids'][x['index']]]=np.asarray(x['embedding'],dtype=np.float64)
            else:rerank[j['proposition_id']]=(j,native)
        saved=c.csvrows(stop/'partial_predictions.csv');c.require(sorted(predicted,key=lambda r:r['request_id'])==sorted(saved,key=lambda r:r['request_id']),'Partial prediction export mismatch')
        keys=c.read(can/'embedding_ids.json');c.require(np.array_equal(np.load(can/'vectors.npy',allow_pickle=False),np.asarray([vectors[k] for k in keys])),'Vector reconstruction')
        corpus=c.jsonlines(prep/'corpus.jsonl');passages={p['passage_id']:p for p in corpus}
        indices={sid:c.baseline.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp]) for sid in c.patient_ids('stage1') for pp in [[p for p in corpus if p['subject_id']==sid]] if pp}
        candidates={r['proposition_id']:r for r in c.jsonlines(can/'candidates.jsonl')};items={r['proposition_id']:r for r in c.jsonlines(base/'inputs.jsonl')}
        for item in c.jsonlines(prep/'inputs.jsonl'):
            pid=item['proposition_id'];ranks=indices[item['subject_id']].retrieve(item['text'],vectors[item['claim_embedding_id']]) if item['subject_id'] in indices else dict(bm25=[],dense=[],hybrid=[])
            pools={a+'48':c.baseline.candidates(ranks,a) for a in ('A','B','C')}
            c.require(c.canonical(dict(proposition_id=pid,rankings=ranks,candidate_ids=pools))==c.canonical(candidates[pid]),'Candidate reconstruction')
            union=sorted({p for pool in pools.values() for p in pool});scores={}
            if union:
                j,n=rerank[pid];c.require(j['body']['query']==item['text'] and j['body']['documents']==[passages[p]['search_text'] for p in union],'Rerank request reconstruction')
                scores={union[x['index']]:float(x['relevance_score']) for x in n['results']}
            packed=c.baseline.core.select_evidence(pools['C48'],scores,passages,item['admission'])
            c.require(c.canonical(dict(item,**packed,candidate_ids=pools['C48'],scores=scores))==c.canonical(items[pid]),'C48 reconstruction')
        prompts=c.read(prep/'judge_prompts.json');assignments=c.csvrows(base/'assignments.csv')
        for a in assignments:
            item=items[a['proposition_id']];expected=c.judge_body(item,item['reference'],prompts,a['role']);j=alljobs[a['request_id']]
            c.require(expected==j['body'] and c.fingerprint(expected)==a['body_sha256'],'Base body reconstruction')
        c.require(len(items)==601 and len(assignments)==1202 and set(j.get('role') for j in alljobs.values() if j['kind']=='chat')=={'v4_first','qwen'},'Scope drift')
        # Existing helper policy: normal top-level status changes are visible, frozen material changes fail.
        original_bytes=Path.read_bytes;nav=(c.ROOT/'reviews/README.md').resolve()
        def nav_edit(path):return original_bytes(path)+(b'\n# isolated status update\n' if path.resolve()==nav else b'')
        with patch.object(Path,'read_bytes',nav_edit):positive=check_history(c.read(c.OUT/'historical_protection_001.json'),bindings={})
        c.require(any(r['path']=='reviews/README.md' and r['changed'] for r in positive['mutable_entries']),'Mutable navigation boundary failed')
        negatives=[]
        for target in (base/'jobs.jsonl',c.OUT/'authority_001.json',next((c.OUT/'live/stage1_base_chat').glob('receipt_*.json')),stop/'partial_predictions.csv',c.OUT/'report.md'):
            def altered(path):return original_bytes(path)+(b'\nTAMPERED\n' if path.resolve()==target.resolve() else b'')
            try:
                with patch.object(Path,'read_bytes',altered):
                    c.check_manifest(stop);c.check_hashes(c.read(stop/'live_frozen_files.json'))
                    c.check_manifest(c.OUT/'deliverables_001')
            except ValueError:negatives.append(target.relative_to(c.ROOT).as_posix())
            else:raise AssertionError('Tamper not rejected: '+str(target))
        paths=set(auth['execution_sha256'])|{p.relative_to(c.ROOT).as_posix() for p in c.TASK.glob('*.py')}|{'tests/test_review_validation016.py'}
        checkout=[]
        with tempfile.TemporaryDirectory(prefix='verifact016-checkout-') as temp:
            temp=Path(temp);env=dict(os.environ,GIT_INDEX_FILE=str(temp/'index'))
            def git(args):return subprocess.check_output(['git',*args],cwd=c.ROOT,env=env,stderr=subprocess.PIPE)
            git(['read-tree','HEAD']);git(['-c','core.autocrlf=false','add','--','.gitattributes',*sorted(paths)])
            dest=temp/'checkout';dest.mkdir();git(['-c','core.autocrlf=true','checkout-index','--prefix='+dest.as_posix()+'/','--',*sorted(paths)])
            for name in sorted(paths):checkout.append(dict(path=name,same_bytes=(c.ROOT/name).read_bytes()==(dest/name).read_bytes()))
        c.require(all(r['same_bytes'] for r in checkout),'Windows checkout bytes changed');c.write_json(out/'checkout.json',checkout)
        result=dict(status='executor_interruption_self_check_passed_not_independent_audit',created_utc=c.now(),external_calls=0,
            historical_strict_files=history['strict_unchanged_files'],C48_rebuilt=601,base_bodies_rebuilt=1202,
            valid_partial_predictions_replayed=len(predicted),raw_receipts_verified=raw_n,unreceipted_reservations_verified=unknown_n,
            cost_verified_cny=total,cap_cny=40,GT_performance_evaluated=False,mutable_navigation_positive=True,
            frozen_tamper_rejections=negatives,windows_checkout_files=len(checkout),independent_audit=False)
        c.write_json(out/'summary.json',result);print(c.canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'interruption_verification_002')
    verify(p.parse_args().output.resolve())
