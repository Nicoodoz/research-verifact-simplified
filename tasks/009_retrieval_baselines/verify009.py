"""Repeatable network-disabled 009 handoff checks and receipt-only replay."""
from collections import Counter,defaultdict
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from datetime import datetime
from pathlib import Path
import argparse
import io
import json
import re
import subprocess
import sys
import unittest
from unittest.mock import patch
import numpy as np
import study009 as s
from io009 import stage,rerank_scores,old_judge_cache
from retrieval_baseline import pack as pack_baseline,retrieve as retrieve_baseline


def content_equal(original,replay):
    checks=[]
    original_files=[p for p in original.rglob('*') if p.is_file() and p.name!='manifest.json']
    assert {p.relative_to(original) for p in original_files}=={p.relative_to(replay) for p in replay.rglob('*') if p.is_file() and p.name!='manifest.json'}
    for p in original_files:
        q=replay/p.relative_to(original)
        assert p.read_bytes()==q.read_bytes(),str(p)
        checks.append(dict(file=p.relative_to(original).as_posix(),sha256=s.pilot.digest_file(p)))
    return checks



def check_frozen_manifest(path):
    """Strict artifacts/computation; a past verifier version is provenance only."""
    m=s.check(path.parent)
    for name,digest in m.get('dependencies',{}).items():
        assert s.pilot.digest_file(s.ROOT/name)==digest,(str(path),name)
    historical_self_check=('verification.json' in m['files'] and
        s.read_json(path.parent/'verification.json').get('self_check_not_independent_audit') is True)
    provenance=[]
    for name,digest in m.get('code_sha256',{}).items():
        actual=s.pilot.digest_file(s.ROOT/name)
        if historical_self_check and name=='tasks/009_retrieval_baselines/verify009.py':
            provenance.append(dict(manifest=path.relative_to(s.ROOT).as_posix(),code=name,
                recorded_sha256=digest,current_sha256=actual,matches=actual==digest,
                role='historical_verifier_provenance_not_experimental_computation'))
        else:
            assert actual==digest,(str(path),name)
    return provenance


def workspace_snapshot():
    """Repository state is diagnostic, not a substitute for frozen bindings."""
    return dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),
        tracked_changes=subprocess.check_output(['git','diff','--name-only'],cwd=s.ROOT,text=True).splitlines(),
        workspace_changes_policy='informational_only; frozen materials and computational code remain strict')


def run(output,tests=True):
    output=output.resolve()
    assert output.is_relative_to(s.OUT) and not output.exists()
    assert not list(s.OUT.rglob('runner.lock')) and not (s.OUT/'task_api.lock').exists()
    output.mkdir(parents=True)
    evidence={}
    with ExitStack() as stack:
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            stack.enter_context(patch(target,side_effect=AssertionError('Network prohibited during 009 replay')))
        manifest_checks=[]
        verifier_provenance=[]
        for path in sorted(s.OUT.rglob('manifest.json')):
            if path.is_relative_to(output):
                continue
            m=s.read_json(path)
            if 'files' not in m:
                continue
            verifier_provenance.extend(check_frozen_manifest(path))
            manifest_checks.append(path.relative_to(s.ROOT).as_posix())
        evidence['frozen_manifests']=manifest_checks
        evidence['historical_verifier_provenance']=verifier_provenance
        auth=s.read_json(s.OUT/'authority_001.json')
        for name,digest in auth['immutable_source_sha256'].items():
            assert s.pilot.digest_file(s.ROOT/name)==digest
        assert s.pilot.digest_file(s.TASK/'native_stage.py')==auth['native_stage_sha256']
        assert s.pilot.digest_file(s.OUT/'execution_protocol_001.md')==auth['protocol_sha256']
        stages={phase:stage(phase) for phase in s.STAGE_CAPS}
        evidence['expenses']={phase:dict(cost_cny=sum(a['charge_cny'] for a in attempts),attempts=len(attempts),
            charge_bases=dict(Counter(a['charge_basis'] for a in attempts))) for phase,(_,attempts) in stages.items()}
        assert sum(x['cost_cny'] for x in evidence['expenses'].values())<=40
        token_rows=[]
        for phase,(values,attempts) in stages.items():
            assert all(v['status']=='received' for v in values.values())
            assert sum(a['charge_cny'] for a in attempts)<=s.STAGE_CAPS[phase]
            for v in values.values():
                native=v['native']
                usage=native.get('usage',{})
                counted=usage.get('prompt_tokens',usage.get('total_tokens'))
                if counted is None:
                    counted=native.get('meta',{}).get('billed_units',{}).get('input_tokens')
                if counted is None:
                    counted=native.get('meta',{}).get('tokens',{}).get('input_tokens')
                assert isinstance(counted,int) and counted>0
                token_rows.append(dict(phase=phase,request_id=v['job']['request_id'],kind=v['job']['kind'],provider_input_tokens=counted,
                    provider_output_tokens=usage.get('completion_tokens',0)))
        s.pilot.write_csv(output/'provider_token_accounting.csv',token_rows)
        protocol=s.read_json(s.OUT/'confirmation_protocol_001.json')
        assert protocol['patient_ids']==s.patient_order()[18:24]
        first=min(v['receipt']['transport']['started_utc'] for phase in ('confirm_embed','confirm_rerank','confirm_judge') for v in stages[phase][0].values())
        assert datetime.fromisoformat(protocol['created_utc'])<datetime.fromisoformat(first)
        evidence['confirmation_protocol_before_first_request']=True
        # Fresh index construction against the selected patients' raw records.
        all_subjects=set(s.patient_order()[12:24])
        raw_notes=s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',all_subjects)
        notes={n['ROW_ID']:n for n in raw_notes}
        rawprops={p['proposition_id']:p for p in s.pilot.subset_csv(s.RAW/'propositions/propositions.csv.gz','subject_id',all_subjects)}
        oldvectors=s.prior_stages.embedding_vectors()
        oldcache=old_judge_cache()
        cohort_summaries=[]
        for name,rrphase,jphase in [('development_001','dev_embed','dev_judge'),('confirmation_001','confirm_rerank','confirm_judge')]:
            folder=s.OUT/name
            inputs=s.pilot.jsonl(folder/'judge_preparation/inputs.jsonl')
            corpus=s.pilot.jsonl(folder/'preparation/corpus.jsonl')
            pp={p['passage_id']:p for p in corpus}
            bynote=defaultdict(list)
            for p in corpus:
                raw=notes[p['note_id']]
                assert p['text']==raw['TEXT'][p['start']:p['end_exclusive']]
                assert p['note_sha256']==s.pilot.digest_text(raw['TEXT'])
                assert p['subject_id']==s.pilot.integer_id(raw['SUBJECT_ID'])
                assert p['search_text']==f"Date: {p['date']}. {p['category']} {p['description']}. {p['text']}"
                assert p['embedding_id']==s.pilot.digest_text(p['search_text'])
                bynote[p['note_id']].append((p['start'],p['end_exclusive']))
            for nid,spans in bynote.items():
                assert sorted(spans)==list(s.core.paragraph_spans(notes[nid]['TEXT']))
            for item in inputs:
                assert rawprops[item['proposition_id']]['text']==item['text']
                assert item['subject_id'] in s.patient_order()[12:24]
                scope={n['ROW_ID'] for n in raw_notes if s.pilot.integer_id(n['SUBJECT_ID'])==item['subject_id']
                    and item['admission']['ADMITTIME'][:10]<=n['CHARTDATE'][:10]<=item['admission']['DISCHTIME'][:10]
                    and n['CATEGORY'].strip().lower()!='discharge summary' and n['TEXT'].strip()}
                assert scope=={p['note_id'] for p in corpus if p['subject_id']==item['subject_id']}
            if name=='confirmation_001':
                vectors={}
                for value in stages['confirm_embed'][0].values():
                    job,native=value['job'],value['native']
                    assert native['model']==s.EMBED_MODEL
                    assert sorted(x['index'] for x in native['data'])==list(range(len(job['text_ids'])))
                    for d in native['data']:
                        key=job['text_ids'][d['index']]
                        assert s.pilot.digest_text(job['body']['input'][d['index']])==key
                        assert key not in vectors
                        vectors[key]=np.asarray(d['embedding'],dtype=np.float64)
                        assert vectors[key].shape==(1024,) and np.isfinite(vectors[key]).all()
                ids=s.read_json(folder/'candidates/embedding_ids.json')
                assert np.array_equal(np.asarray([vectors[k] for k in ids]),np.load(folder/'candidates/vectors.npy'))
                master=s.pilot.subset_csv(s.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv','subject_id',set(protocol['patient_ids']))
                expected=[r for r in master if r['proposition_type']=='claim' and r['invalid']=='False']
                cohort=s.pilot.read_csv(folder/'preparation/cohort.csv')[1]
                assert {r['proposition_id'] for r in expected}=={r['proposition_id'] for r in cohort}
                ei={r['proposition_id']:r for r in expected}
                assert all(ei[r['proposition_id']]==r for r in cohort)
            else:
                vectors=oldvectors
            indices={sid:s.core.HybridIndex([p for p in corpus if p['subject_id']==sid],[vectors[p['embedding_id']] for p in corpus if p['subject_id']==sid]) for sid in {x['subject_id'] for x in inputs}}
            canonical={}
            max_numeric_difference=0
            prompts=s.read_json(folder/'preparation/judge_prompts.json')
            for item in inputs:
                actual=indices[item['subject_id']].retrieve(item['text'],vectors[s.pilot.digest_text(item['text'])])
                for route in ('bm25','dense'):
                    saved=item['rankings'][route]
                    assert [x[0] for x in actual[route]]==[x[0] for x in saved]
                    max_numeric_difference=max(max_numeric_difference,max((abs(x[1]-y[1]) for x,y in zip(actual[route],saved)),default=0))
                assert actual['hybrid']==item['rankings']['hybrid']
                rv=stages[rrphase][0][('dev_refresh:' if name=='development_001' else 'confirm_rerank:')+item['proposition_id']]
                assert rv['job']['body']['query']==item['text']
                assert rv['job']['body']['documents']==[pp[k]['search_text'] for k in rv['job']['passage_ids']]
                assert rerank_scores(rv)==item['scores']
                for method,r in item['retrieval'].items():
                    assert r['status']=='ready'
                    rule=method[0]
                    pool=s.candidates(actual,rule,80 if method.endswith('80') else 48)
                    assert pool==r['candidate_ids']
                    scores=dict(actual['dense']) if method=='B48_no_rerank' else item['scores']
                    selected=s.core.select_evidence(pool,scores,pp,item['admission'],max_per_note=r['max_per_note'])
                    assert all(selected[k]==r[k] for k in selected)
                    if method in ('A48','B48','C48'):
                        assert pack_baseline(pool,scores,pp,item['admission'])==selected
                    body=s.prior_stages.judge_body(item,selected['reference'],prompts)
                    assert s.pilot.fingerprint(body)==r['body_sha256']
                    source=oldcache[r['body_sha256']]['body'] if r['source']=='008' else stages[jphase][0][r['request_id']]['job']['body']
                    assert body==source
                    assert s.pilot.strict_json(body['messages'][1]['content'])==dict(proposition=item['text'],reference=selected['reference'])
                    assert r['body_sha256'] not in canonical or canonical[r['body_sha256']]==r['request_id']
                    canonical[r['body_sha256']]=r['request_id']
            assert max_numeric_difference<1e-12
            for sid in indices:
                item=next(x for x in inputs if x['subject_id']==sid)
                own=[p for p in corpus if p['subject_id']==sid]
                for method in ('A48','B48','C48'):
                    result=retrieve_baseline(item['text'],own,[vectors[p['embedding_id']] for p in own],vectors[s.pilot.digest_text(item['text'])],method)
                    assert result['candidate_ids']==item['retrieval'][method]['candidate_ids']
            cohort_summaries.append(dict(cohort=name,claims=len(inputs),passages=len(corpus),notes=len(bynote),conditions=sum(len(x['retrieval']) for x in inputs),
                max_replayed_ranking_numeric_difference=max_numeric_difference,all_raw_claims_pools_scores_references_bodies_match=True))
            print(name,'raw corpus, vectors, rankings, packing and cache verified',flush=True)
        evidence['retrieval']=cohort_summaries
        from score009 import score
        from score_interventions import score as score_diag
        from render_review009 import render
        from publish_confirmation_review import render as render_new
        from compile009 import compile
        replay_checks={}
        quiet=io.StringIO()
        with redirect_stdout(quiet):
            for name,phase in [('development_001','dev_judge'),('confirmation_001','confirm_judge')]:
                target=output/('replay_'+name)
                score(s.OUT/name,phase,target)
                replay_checks[name]=content_equal(s.OUT/name/'analysis_001',target)
            score_diag(output/'replay_diagnostics')
            replay_checks['diagnostics']=content_equal(s.OUT/'interventions_001/analysis_001',output/'replay_diagnostics')
            render(s.OUT/'development_001',s.TASK/'notes_development.json',output/'replay_dev_review')
            replay_checks['development_review']=content_equal(s.OUT/'development_001/review_001/semantic_001',output/'replay_dev_review')
            render_new(s.OUT/'confirmation_001',s.TASK/'notes_confirmation_complete.json',output/'replay_confirm_review')
            replay_checks['confirmation_review']=content_equal(s.OUT/'confirmation_001/review_002/semantic_001',output/'replay_confirm_review')
            compile(output/'replay_synthesis')
            replay_checks['synthesis']=content_equal(s.OUT/'synthesis_001',output/'replay_synthesis')
        evidence['byte_identical_replays']=replay_checks
        # Interventions contain only original raw evidence, exact claims and fixed bodies.
        from prepare_interventions import reference
        prep=s.OUT/'interventions_001/preparation'
        for case in s.read_json(prep/'cases.json'):
            folder=s.OUT/case['spec']['folder']
            item=next(x for x in s.pilot.jsonl(folder/'judge_preparation/inputs.jsonl') if x['case_id']==case['spec']['case_id'])
            pp={p['passage_id']:p for p in s.pilot.jsonl(folder/'preparation/corpus.jsonl')}
            for mode,r in case['variants'].items():
                rebuilt=reference(r['selected_ids'],pp,item['admission'])
                assert rebuilt['reference']==r['reference'] and rebuilt['body_characters']<=8000
                assert len(r['selected_ids'])<=16 and all(pp[k]['subject_id']==item['subject_id'] for k in r['selected_ids'])
                body=s.prior_stages.judge_body(item,r['reference'],s.read_json(folder/'preparation/judge_prompts.json'))
                assert s.pilot.fingerprint(body)==r['body_sha256']
                if r['source']=='new':
                    assert body==stages['diagnostics'][0][r['request_id']]['job']['body']
        evidence['diagnostic_inputs_verified']=True
        if tests:
            log=io.StringIO()
            with redirect_stdout(log),redirect_stderr(log):
                suite=unittest.defaultTestLoader.discover(str(s.ROOT/'tests'))
                result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
            (output/'tests.log').write_text(log.getvalue(),encoding='utf-8')
            evidence['tests']=dict(run=result.testsRun,errors=len(result.errors),failures=len(result.failures),success=result.wasSuccessful(),network_disabled=True)
            assert result.wasSuccessful()
        evidence['network_disabled']=True
    evidence.update(workspace_snapshot())
    evidence['self_check_not_independent_audit']=True
    s.pilot.write_json(output/'verification.json',evidence)
    s.seal(output,[s.OUT/'authority_001.json',s.OUT/'confirmation_protocol_001.json'],[Path(__file__),s.TASK/'retrieval_baseline.py',s.TASK/'score009.py',s.TASK/'score_interventions.py'])
    print('009 offline verification complete:',output,flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--skip-tests',action='store_true')
    a=ap.parse_args()
    run(a.output,not a.skip_tests)
