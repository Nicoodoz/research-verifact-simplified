"""Read-only document/link/history checks after the existing 009 offline replay."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/documentation_sync/20260915_001'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def main():
    before=read(OUT/'before.json')
    edits=read(OUT/'changes.json')
    allowed={e['file'] for e in edits}
    changed={name for name,h in before['tracked_sha256'].items() if sha(ROOT/name)!=h}
    assert changed==allowed
    for e in edits:
        assert e['after_sha256']==sha(ROOT/e['file'])
        data=(ROOT/e['file']).read_bytes()
        assert not data.startswith(b'\xef\xbb\xbf')
        assert repr('\r\n' if b'\r\n' in data else '\n')==e['line_endings']
    assert all(name.endswith('.md') for name in changed)
    assert not any('/run_' in name or '/revision_' in name or '/verification' in name for name in changed)
    assert not any(name.startswith('reviews/') and name!='reviews/README.md' for name in changed)
    # Scan every current task/result entry, plus the high-level and service docs.
    entries=[ROOT/'README.md',ROOT/'AGENTS.md',ROOT/'reviews/README.md',ROOT/'docs/siliconflow_pool/README.md']
    entries+=sorted((ROOT/'tasks').glob('*/README.md'))+sorted((ROOT/'outputs').glob('*/README.md'))
    links,broken=[],[]
    for path in entries:
        text=re.sub(r'```.*?```','',path.read_text(encoding='utf-8'),flags=re.S)
        for value in re.findall(r'\[[^\]\n]*\]\(([^\)]+)\)',text):
            value=value.strip('<>').split('#',1)[0]
            if not value or re.match(r'^[a-z]+:',value,re.I):
                continue
            target=(path.parent/value).resolve()
            if not target.exists():
                broken.append(dict(file=path.relative_to(ROOT).as_posix(),target=value))
            links.append(dict(file=path.relative_to(ROOT).as_posix(),target=value))
    assert not broken,broken
    for dirname in ('005_pilot_effect_analysis','006_source_context_feasibility','007_context_retrieval','008_retrieval_planning'):
        for category in ('tasks','outputs'):
            text=(ROOT/category/dirname/'README.md').read_text(encoding='utf-8')
            assert '已通过2026-09-14' in text
            assert '独立审计' in text and '009入口' in text
    for name in ('README.md','AGENTS.md'):
        text=(ROOT/name).read_text(encoding='utf-8')
        assert all(word in text for word in ('C48','A48','16名','前24名','40名reserved test','稳定优越或非劣','证据组织','融合公式网格'))
    audit=(ROOT/'reviews/009_retrieval_baselines.md').read_text(encoding='utf-8')
    assert '**结论：PASS。前述正常审计文档更新阻塞重放的必须修正项已关闭' in audit
    groups=read(ROOT/'outputs/003_error_analysis/patient_groups.json')['groups']
    assert len(groups['development'])==40
    cohorts=['outputs/004_event_alignment_pilot/run_003/cohort_llm.csv','outputs/006_source_context_feasibility/preparation_001/cohort.csv',
        'outputs/007_context_retrieval/preparation_003/cohort.csv','outputs/008_retrieval_planning/preparation_001/cohort.csv',
        'outputs/009_retrieval_baselines/confirmation_001/preparation/cohort.csv']
    used=set()
    for name in cohorts:
        with (ROOT/name).open(encoding='utf-8-sig',newline='') as f:
            used.update(row['subject_id'] for row in csv.DictReader(f))
    assert len(used)==24 and used<=set(groups['development'])
    unused=set(groups['development'])-used
    assert len(unused)==16
    v=read(ROOT/'outputs/009_retrieval_baselines/documentation_sync_verification_001/verification.json')
    assert v['tests']['success'] and v['tests']['run']==146 and v['network_disabled']
    assert sum(len(x) for x in v['byte_identical_replays'].values())==109
    assert abs(sum(x['cost_cny'] for x in v['expenses'].values())-18.08218167)<1e-8
    # These artifacts were not edited; their existing signed values remain sources.
    facts=dict(development_total=40,development_used=24,development_remaining=16,
        reserved_group_sizes={k:len(val) for k,val in groups.items()},new_patient_results=False,
        task006=read(ROOT/'outputs/006_source_context_feasibility/run_001/analysis/summary.json'),
        task007=read(ROOT/'outputs/007_context_retrieval/zero_budget_sensitivity_001/summary.json'),
        task008=read(ROOT/'outputs/008_retrieval_planning/run_001/analysis/costs.json')['total_estimated_or_reserved_cny'],
        task009=read(ROOT/'outputs/009_retrieval_baselines/confirmation_001/analysis_001/summary.json')['valid_predictions'])
    assert facts['task006']['valid_responses']==189 and facts['task007']['task_cumulative_used_or_reserved_cny']<4.171
    assert facts['task009']==dict(A48=650,B48=650,C48=650)
    result=dict(base_head=before['head'],current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        modified_documents=len(changed),modified_files=sorted(changed),entries_checked=[p.relative_to(ROOT).as_posix() for p in entries],
        local_links_checked=len(links),broken_links=broken,tracked_files_checked=len(before['tracked_sha256']),
        unchanged_tracked_files=len(before['tracked_sha256'])-len(changed),all_non_document_tracked_files_unchanged=True,
        historical_audits_reports_runs_manifests_unchanged=True,gitignore_and_gitattributes_unchanged=True,
        encodings_and_line_endings_preserved=True,tests=v['tests'],replay_content_files_byte_identical=109,
        replay='outputs/009_retrieval_baselines/documentation_sync_verification_001/verification.json',facts=facts,
        new_api_calls=0,independent_audit_of_this_document_sync=False)
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('modified_documents','local_links_checked','unchanged_tracked_files','tests','replay_content_files_byte_identical','new_api_calls')},ensure_ascii=False))

if __name__=='__main__':
    main()
