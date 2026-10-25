"""Offline original-source/request/receipt replay; mutable status docs never block."""
from pathlib import Path
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
from collections import Counter
import argparse
import io
import json
import subprocess
import unittest
import duckdb
import pandas as pd
import alignment_common as s
from score_alignment import score
from io010 import stage
from inspect_references import blocks,normalized


def verify(output):
    output=output.resolve()
    assert output.is_relative_to(s.OUT) and not output.exists()
    assert not (s.OUT/'live/judge/runner.lock').exists()
    output.mkdir(parents=True)
    with ExitStack() as stack:
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            stack.enter_context(patch(target,side_effect=AssertionError('010 offline replay blocks network')))
        for name in ('preparation_001','readiness_001','reference_diagnostics_001','metadata_diagnostics_001','metadata_linkage_001','analysis_001','tables_001','additional_diagnostics_001','review_001','review_002'):
            s.check(s.OUT/name)
        prior=s.read_json(s.OUT/'readiness_001/009_before_hashes.json')
        assert all(s.pilot.digest_file(s.ROOT/name)==h for name,h in prior.items()),'009 historical artifact changed'
        prep=s.OUT/'preparation_001'
        cohort=s.pilot.read_csv(prep/'cohort.csv')[1]
        assert (prep/'cohort.csv').read_bytes()==(s.PRIOR/'preparation/cohort.csv').read_bytes()
        inputs=s.pilot.jsonl(prep/'inputs.jsonl')
        bypid={x['proposition_id']:x for x in inputs}
        assert len(inputs)==len(bypid)==650
        old={x['proposition_id']:x for x in s.pilot.jsonl(s.PRIOR/'judge_preparation/inputs.jsonl')}
        binding=s.read_json(prep/'release_binding.json')
        rater=binding['configuration']['rater_alias']
        expected=dict(model='R1-70B',fact_type='sentence',top_n='100',retrieval_method='rerank',reference_format='absolute_time',reference_only_admission='True',deduplicate_text='True')
        cfg=[c for c in s.pilot.read_csv(s.RAW/'verifact/rater_configurations.csv')[1] if c['rater_alias']==rater]
        assert len(cfg)==1 and cfg[0]==binding['configuration'] and all(cfg[0][k]==v for k,v in expected.items())
        with duckdb.connect() as db:
            db.register('selected',pd.DataFrame({'proposition_id':list(bypid)}))
            vv=db.execute('SELECT proposition_id,reference_id,verdict,model FROM read_parquet(?) JOIN selected USING(proposition_id) WHERE rater_alias=?',
                [str(s.RAW/'verifact/verdicts.parquet'),rater]).fetchall()
            assert len(vv)==650 and all(v[3]=='R1-70B' for v in vv)
            db.register('refs',pd.DataFrame({'reference_id':sorted({v[1] for v in vv})}))
            refs=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN refs USING(reference_id)',[str(s.RAW/'verifact/reference_payloads.parquet')]).fetchall())
        saved={p['proposition_id']:p['verdict'] for p in s.pilot.read_csv(prep/'released_predictions.csv')[1]}
        for pid,rid,verdict,model in vv:
            assert bypid[pid]['reference_id']==rid and bypid[pid]['references']['verifact_reference']==refs[rid]
            assert s.pilot.digest_text(refs[rid])==rid and saved[pid]==verdict
        assert {x['subject_id'] for x in inputs}==set(s.previous.patient_order()[18:24])
        props={p['proposition_id']:p for p in s.pilot.subset_csv(s.RAW/'propositions/propositions.csv.gz','proposition_id',set(bypid))}
        jobs={j['request_id']:j for j in s.pilot.jsonl(prep/'jobs.jsonl')}
        prompts=s.read_json(prep/'judge_prompts.json')
        assignments=s.pilot.read_csv(prep/'assignments.csv')[1]
        seen={}
        for a in assignments:
            item=bypid[a['proposition_id']]
            assert item['text']==props[a['proposition_id']]['text']==old[a['proposition_id']]['text']
            assert item['references']['c48_reference']==old[a['proposition_id']]['retrieval']['C48']['reference']
            body=s.judge_body(item,item['references'][a['arm']],prompts)
            assert body==jobs[a['request_id']]['body'] and s.pilot.fingerprint(body)==a['body_sha256']
            assert a['body_sha256'] not in seen or seen[a['body_sha256']]==a['request_id']
            seen[a['body_sha256']]=a['request_id']
            assert set(s.pilot.strict_json(body['messages'][1]['content']))=={'proposition','reference'}
        repeats=s.read_json(prep/'repeats.json')
        expected_repeats=[]
        for sid in sorted({x['subject_id'] for x in inputs}):
            for author in ('llm','human'):
                chosen=min([x for x in inputs if x['subject_id']==sid and x['author_type']==author],key=lambda x:s.pilot.digest_text('010/repeat/v1:'+x['proposition_id']))
                expected_repeats.extend((chosen['proposition_id'],arm) for arm in s.METHODS)
        assert sorted((r['proposition_id'],r['arm']) for r in repeats)==sorted(expected_repeats)
        assert all(jobs[r['request_id']]['body']==jobs[r['canonical_request_id']]['body'] for r in repeats)
        values,attempts=stage('judge')
        manifest=s.read_json(s.OUT/'live/judge/manifest.json')
        assert manifest['jobs']==s.pilot.jsonl(prep/'jobs.jsonl')
        first=min(v['receipt']['transport']['started_utc'] for v in values.values() if v['receipt'])
        assert s.read_json(s.OUT/'authority_001.json')['created_utc']<first
        assert sum(a['charge_cny'] for a in attempts)<=40
        rawblocks=s.pilot.jsonl(s.OUT/'reference_diagnostics_001/blocks.jsonl')
        for b in rawblocks:
            ref=bypid[b['proposition_id']]['references'][b['arm']]
            assert ref[b['start']:b['end_exclusive']]==b['raw_block']
            assert ref[b['text_start']:b['end_exclusive']].rstrip()==b['text']
        with redirect_stdout(io.StringIO()):
            score(output/'analysis_replay')
        hashes={}
        for p in (s.OUT/'analysis_001').iterdir():
            if p.is_file() and p.name!='manifest.json':
                assert p.read_bytes()==(output/'analysis_replay'/p.name).read_bytes(),p.name
                hashes[p.name]=s.pilot.digest_file(p)
        from complete_diagnostics010 import run as complete_diagnostics
        with redirect_stdout(io.StringIO()):
            complete_diagnostics(output/'additional_replay')
        for p in (s.OUT/'additional_diagnostics_001').iterdir():
            if p.is_file() and p.name!='manifest.json':
                assert p.read_bytes()==(output/'additional_replay'/p.name).read_bytes(),p.name
                hashes['additional/'+p.name]=s.pilot.digest_file(p)
        if (s.OUT/'review_002/semantic_001/manifest.json').exists():
            from materialize_review010 import render
            s.check(s.OUT/'review_002');s.check(s.OUT/'review_002/semantic_001')
            with redirect_stdout(io.StringIO()):
                render(s.TASK/'review_notes.json',output/'review_replay')
            for p in (s.OUT/'review_002/semantic_001').rglob('*'):
                if p.is_file() and p.name!='manifest.json':
                    relative=p.relative_to(s.OUT/'review_002/semantic_001')
                    assert p.read_bytes()==(output/'review_replay'/relative).read_bytes()
                    hashes['review/'+relative.as_posix()]=s.pilot.digest_file(p)
        current=s.read_json(prep/'system_reference_metrics.json')
        release=s.pilot.read_csv(prep/'released_predictions.csv')[1]
        assert current['released_system']==s.evaluate_separately(cohort,release)
        for method in ('A48','C48'):
            assert current['009_'+method]==s.evaluate_separately(cohort,s.pilot.read_csv(s.PRIOR/'analysis_001'/('predictions_'+method+'.csv'))[1])
        log=io.StringIO()
        with redirect_stdout(log),redirect_stderr(log):
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(s.ROOT/'tests')))
        (output/'tests.log').write_text(log.getvalue(),encoding='utf-8')
        assert result.wasSuccessful()
        report=dict(network_disabled=True,tests=result.testsRun,test_success=True,claims=650,source_rater=rater,all_source_and_body_bindings_match=True,
            historical_009_files_unchanged=len(prior),replayed_content_sha256=hashes,reference_blocks_bound=len(rawblocks),task_cost_cny=sum(a['charge_cny'] for a in attempts),
            git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),
            tracked_changes=subprocess.check_output(['git','diff','--name-only'],cwd=s.ROOT,text=True).splitlines(),
            workspace_changes_are_informational=True,new_api_calls=0,independent_audit=False)
        s.pilot.write_json(output/'verification.json',report)
        s.seal(output,[prep/'manifest.json',s.OUT/'analysis_001/manifest.json'],[Path(__file__),s.TASK/'score_alignment.py'])
    print(s.pilot.canonical(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    verify(p.parse_args().output)
