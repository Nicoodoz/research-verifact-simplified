"""Freeze the exact uncommitted 009 audit version after final offline checks."""
from datetime import datetime,timezone
from pathlib import Path
import argparse
import re
import subprocess
import study009 as s


def inventory():
    files=[s.ROOT/'README.md',s.ROOT/'AGENTS.md',s.ROOT/'tests/test_retrieval_baselines.py']
    files += [p for base in (s.TASK,s.OUT) for p in base.rglob('*') if p.is_file() and p.name!='handoff_001.json' and '__pycache__' not in p.parts]
    return {p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in sorted(set(files))}


def verify_handoff():
    h=s.read_json(s.OUT/'handoff_001.json')
    assert s.pilot.fingerprint(h['files'])==h['inventory_sha256']
    assert all(s.pilot.digest_file(s.ROOT/name)==digest for name,digest in h['files'].items())
    print(s.pilot.canonical(dict(status='recorded_version_unchanged',files=len(h['files']),inventory_sha256=h['inventory_sha256'],independent_audit='pending')))


def finalize():
    target=s.OUT/'handoff_001.json'
    assert not target.exists(),'Handoff already frozen; do not modify it'
    assert not list(s.OUT.rglob('runner.lock')) and not (s.OUT/'task_api.lock').exists()
    git=lambda *args:subprocess.check_output(['git',*args],cwd=s.ROOT,text=True).strip()
    head,remote=git('rev-parse','HEAD'),git('rev-parse','origin/main')
    assert head==remote==s.BASE_HEAD
    assert set(git('diff','--name-only').splitlines())=={'README.md','AGENTS.md'}
    assert not git('diff','--check')
    initial=inventory()
    # Do not hash, copy, print, or otherwise export credential files or values.
    from verifact_research.inference.siliconflow_pool import load_accounts
    accounts=load_accounts(s.ROOT/'.env.siliconflow_pool')
    for name in initial:
        content=(s.ROOT/name).read_bytes()
        assert not any(account.key.encode('utf-8') in content for account in accounts),'Credential detected in artifact: '+name
    verification=s.read_json(s.OUT/'verification_001/verification.json')
    assert verification['tests']==dict(run=143,errors=0,failures=0,success=True,network_disabled=True)
    assert verification['network_disabled']
    costs=s.read_json(s.OUT/'synthesis_001/costs.json')
    assert abs(costs['total_cny']-18.08218167)<1e-8
    assert costs['total_jobs']==2692 and costs['total_attempts']==2700
    assert s.read_json(s.OUT/'confirmation_001/analysis_001/summary.json')['valid_predictions']==dict(A48=650,B48=650,C48=650)
    # Check current reading entries and prose reports; generated clinical code blocks
    # are deliberately excluded from Markdown link parsing.
    docs=[s.ROOT/'README.md',s.ROOT/'AGENTS.md',s.TASK/'README.md',s.TASK/'research_notes.md']
    docs += list(s.OUT.glob('*.md'))+[s.OUT/'interventions_001/interpretation.md',s.OUT/'confirmation_001/targeted_trace_001/interpretation.md']
    checked=[]
    for path in docs:
        text=re.sub(r'```.*?```','',path.read_text(encoding='utf-8'),flags=re.S)
        for url in re.findall(r'\[[^\]\n]*\]\(([^\)]+)\)',text):
            url=url.strip('<>').split('#',1)[0]
            if not url or re.match(r'^[a-z]+:',url,re.I):
                continue
            resolved=(path.parent/url).resolve()
            assert resolved.exists() or resolved==target,(str(path),url)
            checked.append(dict(document=path.relative_to(s.ROOT).as_posix(),target=url))
    # Validate all existing experimental manifests after the current-document edits.
    frozen=[]
    for path in s.OUT.rglob('manifest.json'):
        m=s.read_json(path)
        if 'files' in m:
            s.check(path.parent)
            for name,digest in {**m.get('dependencies',{}),**m.get('code_sha256',{})}.items():
                assert s.pilot.digest_file(s.ROOT/name)==digest,(str(path),name)
            frozen.append(path.relative_to(s.ROOT).as_posix())
    report=(s.OUT/'report.md').read_text(encoding='utf-8')
    metrics=s.read_json(s.OUT/'confirmation_001/analysis_001/metrics.json')
    for section in metrics.values():
        for m in section['metrics'].values():
            assert f"{m['percent_agreement']*100:.2f}%" in report
            assert f"{m['gwet_ac1']:.4f}" in report and f"{m['mcc']:.4f}" in report
    checks=dict(created_utc=datetime.now(timezone.utc).isoformat(),current_links_checked=checked,
        frozen_manifests_after_current_document_updates=frozen,credential_values_not_present_in_artifacts=True,
        keys_or_env_files_hashed_copied_or_printed=False,metrics_in_main_report_match=True,
        replay_content_files=sum(len(v) for v in verification['byte_identical_replays'].values()),
        only_expected_tracked_files_changed=True,git_diff_check=True,api_calls=0,independent_audit=False)
    s.pilot.write_json(s.OUT/'final_checks_001.json',checks)
    files=inventory()
    h=dict(created_utc=datetime.now(timezone.utc).isoformat(),repository='Nicoodoz/research-verifact',branch=git('branch','--show-current'),head=head,origin_main=remote,
        actual_audited_version='HEAD plus all listed uncommitted files; no commit or push made',
        working_tree_status=git('status','--short'),initial_working_tree_clean=True,
        allowed_changed_scopes=['README.md','AGENTS.md','tests/test_retrieval_baselines.py','tasks/009_retrieval_baselines/','outputs/009_retrieval_baselines/'],
        files=files,inventory_sha256=s.pilot.fingerprint(files),handoff_file_excluded_from_own_inventory=True,
        main_report='outputs/009_retrieval_baselines/report.md',primary_results='outputs/009_retrieval_baselines/confirmation_001/analysis_001',
        verification='outputs/009_retrieval_baselines/verification_001/verification.json',task_cost_cny=costs['total_cny'],task_cap_cny=40,
        paid_work_closed=True,no_api_process_running=True,execution_status='执行修订完成，等待独立复核',independent_audit='pending')
    s.pilot.write_json(target,h)
    verify_handoff()


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--verify-handoff',action='store_true')
    a=ap.parse_args()
    verify_handoff() if a.verify_handoff else finalize()
