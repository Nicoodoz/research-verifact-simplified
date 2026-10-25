"""Seal completed stage-one failure, final navigation checks, and audit handoff."""
from pathlib import Path
import re
import subprocess
import common019 as c

def finish():
    c.require(not (c.OUT/'task_api.lock').exists(),'API lock still active')
    ledger=c.read(c.OUT/'live_ledger.json');gate=c.read(c.OUT/'selection_freeze.json')
    c.require(not gate['passed'] and gate['selected_lambda'] is None,'Unexpected selection decision')
    c.require(not(c.OUT/'validation').exists(),'Unexpected validation outputs')
    c.require(all(j['status']=='received' for ph in ledger['phases'].values() for j in ph['jobs'].values()),'Unfinished requests')
    for p in ['authority.json','selection/preparation/manifest.json','selection/cohort_manifest.json',
              'selection/analysis_001/manifest.json','selection/risk_diagnostics_001/manifest.json','boundary_cases_001/manifest.json']:
        c.check_manifest(c.OUT/p)
    frozen=c.read(c.OUT/'history_before.json')['files'];changed=[]
    for name,h in frozen.items():
        c.require((c.ROOT/name).is_file(),'Missing historical file: '+name)
        if c.file_hash(c.ROOT/name)!=h:changed.append(name)
    expected={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md'}
    c.require(set(changed)==expected,'Changes outside permitted navigation')
    for row in c.read(c.OUT/'documentation_sync_001/changes.json')['changes']:
        c.require(row['after_sha256']==c.file_hash(c.ROOT/row['path']),'Navigation changed after sync')
        c.require(row['before_sha256']==frozen[row['path']],'Navigation initial snapshot differs')
    m=c.read(c.OUT/'selection/analysis_001/metrics.json');text=(c.OUT/'report.md').read_text(encoding='utf-8')
    table_arms={'同期B':'B','V_raw':'V_raw','U0':'U0',**{f'lambda={v:g}':f'U_lambda_{v:g}' for v in c.GRID if v},
                '原VeriFact O（历史）':'O','C_history（010历史）':'C_history','全部预测S（诊断）':'Always_S'}
    checked=[]
    for title,arm in table_arms.items():
        x=m['r0/all/'+arm];v=x['counts'];tp=v['tp']
        line=f"| {title} | {v['correct']} | {100*x['percent_agreement']:.2f} | {x['mcc']:.4f} | {v['false_s']} | {tp['Supported']} | {tp['Not Supported']} | {tp['Not Addressed']} |"
        c.require(line in text,'Report table differs: '+title);checked.append(arm)
    checked_links=[]
    for path in [c.OUT/'report.md',c.OUT/'audit_handoff.md',c.OUT/'CURRENT.md',c.TASK/'CURRENT.md',c.OUT/'boundary_cases_001/report.md']:
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            target=(path.parent/link.split('#')[0]).resolve()
            c.require(target.exists(),'Missing report link: '+str(path)+' -> '+link)
            checked_links.append(dict(source=path.relative_to(c.ROOT).as_posix(),target=target.relative_to(c.ROOT).as_posix()))
    closure=dict(created_utc=c.now(),status='completed_stage1_gate_failed',all_paid_calls_stopped=True,
        selection_claims=650,selection_successful_answers=1300,probe_answers=12,
        selected_lambda=None,stage2_started=False,remaining10_used=False,reserved_test_used=False,
        used_or_reserved_cny=ledger['used_or_reserved_cny'],cap_cny=80,
        unchanged_original_claims=True,unchanged_C48=True,core_replaced=False,
        independent_audit=False,git_commit_or_push_performed=False)
    c.write_json(c.OUT/'execution_closure.json',closure)
    final=dict(created_utc=c.now(),passed=True,executor_only=True,historical_files_checked=len(frozen),
        navigation_changes=changed,non_navigation_changes=[],report_table_checks=checked,
        report_link_checks=checked_links,source_manifests_passed=True,
        receipt_check_passed=c.read(c.OUT/'receipt_integrity_001.json')['passed'],
        recount_passed=c.read(c.OUT/'recount_001/checks.json')['passed'],
        actual_semantic_cases=c.read(c.OUT/'boundary_cases_001/reading_coverage.json')['actually_read_cases'],
        no_new_API_calls_in_verification=True)
    c.write_json(c.OUT/'final_verification.json',final)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip()
    status=subprocess.check_output(['git','status','--short','--branch'],cwd=c.ROOT,text=True)
    paths=[p for root in (c.TASK,c.OUT) for p in root.rglob('*') if p.is_file() and p.name!='handoff_001.json']
    paths.extend(c.ROOT/n for n in expected)
    handoff=dict(created_utc=c.now(),HEAD=head,working_tree=status,
        status='executor_complete_pending_independent_audit',entry_report='outputs/019_support_boundary_screen/report.md',
        file_count=len(paths),sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in paths},
        excluded_self='outputs/019_support_boundary_screen/handoff_001.json',
        selected_lambda=None,stage2_started=False,all_paid_calls_stopped=True,
        github_not_pushed=True)
    c.write_json(c.OUT/'handoff_001.json',handoff)
    print(c.canonical(dict(status=closure['status'],HEAD=head,protected_files=len(frozen),
        report_rows=len(checked),links=len(checked_links),handoff_files=len(paths),
        cost_cny=ledger['used_or_reserved_cny'],pending_independent_audit=True)),flush=True)

if __name__=='__main__':
    finish()
