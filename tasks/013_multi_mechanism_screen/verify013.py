"""Offline provenance, no-new-evidence, metrics and history replay for 013."""
from pathlib import Path
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
from collections import Counter
import argparse,io,unittest,subprocess
import study013 as s
import mechanisms013 as m
from prepare013 import source_data,ANCHORS
from io013 import stage,rerank_scores
from score013 import run as score

def verify(out):
    assert not out.exists() and out.resolve().is_relative_to(s.OUT.resolve())
    assert not list((s.OUT/'live').glob('*/runner.lock'))
    out.mkdir(parents=True)
    with ExitStack() as stack:
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            stack.enter_context(patch(target,side_effect=AssertionError('013 verification forbids network')))
        history=s.read_json(s.OUT/'history_before_hashes.json')
        for p,h in history.items():assert s.pilot.digest_file(s.ROOT/p)==h,p
        for p,h in s.read_json(s.OUT/'evaluation_source_hashes.json').items():assert s.pilot.digest_file(s.ROOT/p)==h,p
        for p,h in s.read_json(s.OUT/'authority_001.json')['immutable_source_sha256'].items():assert s.pilot.digest_file(s.ROOT/p)==h,p
        raw_hashes=s.read_json(s.ROOT/'outputs/001_dataset_audit/run_006/manifest.json')['input_sha256']
        for p,h in raw_hashes.items():assert s.pilot.digest_file(s.RAW/p)==h,p
        for name in ('preparation_001','unit_aux_preparation_001','unit_judge_preparation_001','unit_analysis_001',
                     'screen_aux_preparation_001','screen_inputs_001','screen_judge_preparation_001','screen_input_diagnostics_001','screen_input_diagnostics_002'):
            s.check(s.OUT/name)
        for name in ('screen_analysis_001','review_final_001','review_final_002','mechanism_analysis_001','membership_backcheck_001'):
            s.check(s.OUT/name)
        items,pp,notes,prompts=source_data();by={x['proposition_id']:x for x in items}
        rows=s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl')
        selections=s.read_json(s.OUT/'preparation_001/selection.json')
        assert {x['proposition_id'] for x in rows}==set(selections['selected_ids'])
        old=s.pilot.jsonl(s.TWELVE/'diagnosis_001/ledger.jsonl')
        chosen={r['proposition_id'] for r in old if r['error_union']}
        for sid in sorted({r['subject_id'] for r in old}):
            for a in ('llm','human'):
                candidates=[r for r in old if r['subject_id']==sid and r['author_type']==a and r['correctness_pattern']=='111']
                chosen|={r['proposition_id'] for r in sorted(candidates,key=lambda r:s.pilot.digest_text('013/control/v1:'+r['proposition_id']))[:3]}
        assert chosen==set(selections['selected_ids']) and len(chosen)==231
        aux,attempts=stage('screen_aux')
        rebuilt=0
        for x in rows:
            base=by[x['proposition_id']];current=x['retrieval']
            assert current['baseline']==base['retrieval']['C48']
            if 'contract' in current:assert current['contract']==current['baseline']
            if 'text_guard' in current:assert current['text_guard']==m.text_guard(base,pp,notes)
            if 'wide_candidates' in current:
                value=aux['rerank:'+x['proposition_id']]
                assert value['job']==m.rerank_job(base,pp)
                scores=rerank_scores(value)
                assert scores==current['wide_candidates']['real_rerank_scores']
                wide=s.core.select_evidence(m.wide_pool(base),scores,pp,base['admission']);wide['real_rerank_scores']=scores
                assert wide==current['wide_candidates']
                assert s.core.select_evidence(base['retrieval']['C48']['candidate_ids'],scores,pp,base['admission'])==current['refresh48']
            if 'selector' in current:
                value=aux['selector:'+x['proposition_id']]
                assert value['job']==m.selector_job(base,pp)
                assert m.selected_evidence(base,pp,value['job'],value['native'])==current['selector']
            for arm,r in current.items():
                assert r['body_characters']<=8000 and len(r['selected_ids'])<=16
                assert all(pp[k]['subject_id']==x['subject_id'] for k in r['selected_ids'])
                rebuilt+=1
        jobs={j['request_id']:j for j in s.pilot.jsonl(s.OUT/'screen_judge_preparation_001/jobs.jsonl')}
        assignments=s.pilot.read_csv(s.OUT/'screen_judge_preparation_001/assignments.csv')[1]
        xx={r['proposition_id']:r for r in rows}
        for a in assignments:
            x=xx[a['proposition_id']];r=x['retrieval'][a['arm']]
            body=(m.contract_body if a['arm']=='contract' else s.judge_body)(x,r['reference'],prompts)
            assert body==jobs[a['request_id']]['body']
            assert s.pilot.fingerprint(body)==a['body_sha256']
            parsed=s.pilot.strict_json(body['messages'][1]['content'])
            assert parsed['proposition']==by[a['proposition_id']]['text']
            assert set(parsed)<= {'proposition','reference','claim_contract'}
        with redirect_stdout(io.StringIO()):score(out/'score_replay')
        original=s.OUT/'screen_analysis_001';count=0
        for p in (out/'score_replay').iterdir():
            if p.name=='manifest.json':continue
            assert p.read_bytes()==(original/p.name).read_bytes(),p.name
            count+=1
        from render_review013_final import run as render
        from backcheck_membership013 import run as membership
        from measure_mechanisms013 import run as measurements
        for name,func in [('review_final_002',render),('membership_backcheck_001',membership),('mechanism_analysis_001',measurements)]:
            with redirect_stdout(io.StringIO()):func(out/(name+'_replay'))
            for p in (out/(name+'_replay')).rglob('*'):
                if not p.is_file() or p.name=='manifest.json':continue
                assert p.read_bytes()==(s.OUT/name/p.relative_to(out/(name+'_replay'))).read_bytes(),str(p)
                count+=1
        log=io.StringIO()
        with redirect_stdout(log),redirect_stderr(log):
            tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(s.ROOT/'tests')))
        (out/'tests.log').write_text(log.getvalue(),encoding='utf-8');assert tests.wasSuccessful()
        assert s.total_cost()<=40
        for p,h in history.items():assert s.pilot.digest_file(s.ROOT/p)==h,p
        result=dict(tests=tests.testsRun,tests_success=True,reconstructed_references=rebuilt,reconstructed_assignments=len(assignments),
            unique_screen_judge_requests=len(jobs),score_content_files_equal=count,history_files_unchanged=len(history),
            raw_files_equal_001=len(raw_hashes),
            task_cost_or_reserved_cny=s.total_cost(),network_blocked=True,new_verification_API_calls=0,
            git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),independent_audit=False)
        s.pilot.write_json(out/'verification.json',result)
        s.freeze(out,[s.OUT/'authority_001.json',s.OUT/'history_before_hashes.json'],[Path(__file__)])
    print(s.pilot.canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.output)
