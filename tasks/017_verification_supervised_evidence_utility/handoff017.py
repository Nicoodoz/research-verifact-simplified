"""Prepare review fingerprints and capture offline tests; not an independent audit."""
from pathlib import Path
from collections import Counter
import importlib.metadata
import re
import subprocess
import sys
import common017 as c
from verifact_research.inference.aliyun import load_config

def build():
    c.require((c.OUT/'report.md').exists(),'Formal report required')
    c.require(not (c.OUT/'task_api.lock').exists(),'API still running')
    c.check(c.OUT/'analysis_001');c.check(c.OUT/'verification_001')
    c.require(c.file_hash(c.OUT/'report.md')==c.file_hash(c.OUT/'verification_report_001/report.md'),'Formal report replay differs')
    from verify017 import MUTABLE
    history=c.read(c.OUT/'history_before.json');changed=[];protected=0
    for name,sha in history['files'].items():
        if not (c.ROOT/name).exists() or c.file_hash(c.ROOT/name)!=sha:
            c.require(name in MUTABLE,'Protected historical file changed: '+name);changed.append(name)
        else:protected+=1
    summary=c.read(c.OUT/'analysis_001/summary.json');attempts=c.csvrows(c.OUT/'analysis_001/attempts.csv')
    normalized=c.jsonlines(c.OUT/'analysis_001/normalized_responses.jsonl')
    c.require(not summary['gate_passed'] and not (c.OUT/'learning_001').exists() and not (c.OUT/'confirmation_001').exists(),'Expected headroom stop with no training/confirmation')
    c.write_json(c.OUT/'execution_closure_001.json',dict(created_utc=c.now(),status='completed_stage1_stopped_by_preregistered_gate',
        first_attempt_utc=min(r['started_utc'] for r in attempts),last_attempt_utc=max(r['ended_utc'] for r in attempts),
        used_or_reserved_cny=summary['used_or_reserved_cny'],unknown_usage_reserved_cny=summary['unknown_reservations_cny'],
        observed_usage_cost_cny=summary['used_or_reserved_cny']-summary['unknown_reservations_cny'],task_cap_cny=80,
        protected_history_files=protected,changed_mutable_navigation=changed,report_byte_identical=True,
        report_sha256=c.file_hash(c.OUT/'report.md'),adherence_counts=dict(Counter(e for r in normalized for e in r['adherence_errors'])),
        final_patients_used=False,reserved_test_used=False,selector_trained=False,no_new_API_after_gate=True))
    check=c.OUT/'self_check_001';c.require(not check.exists(),'Self-check already captured');check.mkdir()
    records=[]
    for suite in ('test_utility017.py','test_evaluation.py'):
        command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p',suite]
        result=subprocess.run(command,cwd=c.ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        log=check/(suite+'.txt');log.write_text(result.stdout+result.stderr,encoding='utf-8',newline='\n')
        records.append(dict(command=command,exit_code=result.returncode,log=log.relative_to(c.ROOT).as_posix(),sha256=c.file_hash(log)))
        c.require(result.returncode==0,'Offline tests failed; inspect saved log')
    runtime=dict(python=sys.version,packages={n:importlib.metadata.version(n) for n in ('numpy','pandas','scipy','scikit-learn','irrCAC')})
    c.write_json(check/'tests.json',dict(created_utc=c.now(),tests=records,runtime=runtime,not_independent_audit=True))
    files=[p for base in (c.OUT,c.TASK) for p in base.rglob('*') if p.is_file()]+[c.ROOT/'tests/test_utility017.py']
    keys=[a.key for a in c.old.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={})]+[load_config(c.ROOT/'.env.aliyun').api_key]
    hits=[]
    for p in files:
        data=p.read_bytes()
        if any(k and k.encode() in data for k in keys) or re.search(rb'\bsk-[A-Za-z0-9_-]{24,}',data):hits.append(p.relative_to(c.ROOT).as_posix())
    c.require(not hits,'Potential credential exposure detected; filenames retained locally only')
    c.write_json(check/'secret_scan.json',dict(created_utc=c.now(),files_scanned=len(files),known_enabled_keys_and_generic_pattern=True,hits=0,keys_never_written=True))
    c.seal(check,[],[Path(__file__),c.ROOT/'tests/test_utility017.py'])
    nav=[c.ROOT/n for n in ('README.md','AGENTS.md','.gitattributes','docs/PROJECT_STATUS.md','docs/API_POLICY.md','reviews/README.md')]
    files=[p for base in (c.OUT,c.TASK) for p in base.rglob('*') if p.is_file()]+[c.ROOT/'tests/test_utility017.py']+nav
    snapshot=dict(created_utc=c.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),
        git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),
        independent_audit_status='not_yet_performed',files_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in files},
        historical_inputs_bound_by='outputs/017_verification_supervised_evidence_utility/preparation_001/manifest.json',
        execution_dependencies_bound_by='outputs/017_verification_supervised_evidence_utility/authority_001.json',
        replay='tasks/017_verification_supervised_evidence_utility/verify017.py --output outputs/017_verification_supervised_evidence_utility/verification_AUDITOR_FRESH')
    c.write_json(c.OUT/'handoff_001.json',snapshot)
    print(c.canonical(dict(files_fingerprinted=len(files),tests='8 utility +15 evaluation',credential_scan_hits=0,HEAD=snapshot['HEAD'])))

if __name__=='__main__':build()
