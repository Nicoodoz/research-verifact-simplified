"""Network-blocked deterministic 012 replay, with mutable documentation excluded."""
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from pathlib import Path
from unittest.mock import patch
import argparse,io,subprocess,unittest
import study012 as s
from align012 import align,choose
from evidence012 import run as pipeline
from raw012 import run as backcheck
from diagnose012 import build

def equal_content(original,replay):
    paths=[p for p in original.rglob('*') if p.is_file() and p.name!='manifest.json']
    other=[p.relative_to(replay).as_posix() for p in replay.rglob('*') if p.is_file() and p.name!='manifest.json']
    assert sorted(p.relative_to(original).as_posix() for p in paths)==sorted(other)
    for p in paths:assert p.read_bytes()==(replay/p.relative_to(original)).read_bytes(),str(p)
    return len(paths)

def check_materials():
    s.check(s.OUT/'materials_001')
    packets=s.pilot.jsonl(s.OUT/'materials_001/packets.jsonl')
    ids={p['row']['proposition_id'] for p in packets}
    fields={}
    for key,file in [('proposition','propositions.csv.gz'),('human','human_verdicts.csv.gz'),('validity','proposition_validity.csv.gz')]:
        fields[key]={r['proposition_id']:r for r in s.pilot.subset_csv(s.RAW/'propositions'/file,'proposition_id',ids)}
    for p in packets:
        for key,values in fields.items():assert p[key]==values[p['row']['proposition_id']]
    notes=s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',{p['row']['subject_id'] for p in packets})
    assert notes==s.pilot.jsonl(s.OUT/'materials_001/ehr_notes.jsonl')
    assert (s.OUT/'materials_001/corpus.jsonl').read_bytes()==(s.NINE/'preparation/corpus.jsonl').read_bytes()
    return dict(case_source_rows=len(packets)*3,raw_notes=len(notes),corpus_equal_009=True)

def verify(out):
    out=out.resolve();assert out.is_relative_to(s.OUT) and not out.exists()
    out.mkdir(parents=True)
    with ExitStack() as stack:
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            stack.enter_context(patch(target,side_effect=AssertionError('012 offline replay forbids network')))
        historical_roots=[]
        for top in ('tasks','outputs'):
            historical_roots += [p.relative_to(s.ROOT).as_posix() for p in (s.ROOT/top).iterdir() if p.is_dir() and p.name[:3].isdigit() and int(p.name[:3])<=11]
        tracked=subprocess.check_output(['git','ls-files','--',*historical_roots],cwd=s.ROOT,text=True).splitlines()
        # HEAD baseline is checked, then actual bytes remain fixed throughout replay.
        subprocess.run(['git','diff','--exit-code','HEAD','--',*historical_roots],cwd=s.ROOT,check=True,capture_output=True)
        before={p:s.pilot.digest_file(s.ROOT/p) for p in tracked}
        old=s.read_json(s.ROOT/'outputs/011_evidence_integrity_packaging/readiness_001/history_before_hashes.json')
        for path,h in old.items():assert s.pilot.digest_file(s.ROOT/path)==h,path
        replayed=0
        material_checks=check_materials()
        with redirect_stdout(io.StringIO()):
            for name,func in [('alignment_002',align),('pipeline_001',pipeline),('raw_search_001',backcheck),('diagnosis_001',build)]:
                s.check(s.OUT/name);func(out/name);replayed+=equal_content(s.OUT/name,out/name)
        rows=s.pilot.jsonl(s.OUT/'diagnosis_001/ledger.jsonl')
        initial=s.pilot.jsonl(s.OUT/'alignment_002/ledger.jsonl')
        assert choose(initial)==s.read_json(s.OUT/'alignment_002/selection.json')
        assert len(rows)==650 and len({r['proposition_id'] for r in rows})==650
        assert sum(r['error_union'] for r in rows)==195
        assert sum(r['semantic_review_status']=='deep_read_complete_executor' for r in rows)==24
        metrics=s.read_json(s.OUT/'diagnosis_001/metrics.json')
        originals=s.read_json(s.TEN/'preparation_001/system_reference_metrics.json')
        original_key=next(k for k in originals if not k.startswith('009_'))
        current=s.read_json(s.TEN/'analysis_001/metrics.json')
        for author in ('llm','human'):
            for sys,key in [('O',None),('V','verifact_reference'),('C','c48_reference')]:
                prior=originals[original_key][author] if sys=='O' else current[author]['metrics'][key]
                now=metrics[author][sys]
                for k in ('percent_agreement','gwet_ac1','mcc','confusion_matrix','per_class'):
                    assert now[k]==prior[k],(author,sys,k)
        log=io.StringIO()
        with redirect_stdout(log),redirect_stderr(log):
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(s.ROOT/'tests')))
        (out/'tests.log').write_text(log.getvalue(),encoding='utf-8');assert result.wasSuccessful()
        for p,h in before.items():assert s.pilot.digest_file(s.ROOT/p)==h,p
        report=dict(executor_selfcheck=True,independent_audit=False,tests=result.testsRun,tests_success=True,
            replayed_content_files=replayed,all_650_predictions_metrics_unchanged=True,
            historical_tracked_files_equal_HEAD_and_unchanged=len(before),additional_011_history_bindings=len(old),
            material_source_checks=material_checks,
            network_blocked=True,new_api_calls=0,cost_cny=0,
            base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),
            tracked_changes_informational=subprocess.check_output(['git','diff','--name-only'],cwd=s.ROOT,text=True).splitlines(),
            mutable_readme_agents_reviews_not_replay_dependencies=True)
        s.pilot.write_json(out/'verification.json',report)
        s.seal(out,[s.OUT/'diagnosis_001/manifest.json'],[Path(__file__),s.ROOT/'tests/test_comparative_diagnosis012.py'])
    print(s.pilot.canonical(report))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    verify(ap.parse_args().output)
