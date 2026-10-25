"""Read-only document consistency checks; preserve frozen001–016 evidence."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/documentation_sync/20260916_001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')

def main():
    before=read(OUT/'before.json')['tracked_sha256']
    changed={n for n,h in before.items() if sha(ROOT/n)!=h}
    allowed={'README.md','AGENTS.md','reviews/README.md','docs/siliconflow_pool/README.md'}
    assert changed==allowed,changed
    assert sha(ROOT/'.gitignore')==before['.gitignore'] and sha(ROOT/'.gitattributes')==before['.gitattributes']
    handoff=read(ROOT/'outputs/016_disagreement_triggered_review_validation/completion_002/handoff_001.json')['files_sha256']
    assert all(sha(ROOT/n)==h for n,h in handoff.items()),'016 audited handoff changed'
    docs=[ROOT/n for n in sorted(allowed)]+[ROOT/n for n in ('docs/API_POLICY.md','docs/PROJECT_STATUS.md','docs/aliyun/CURRENT.md',
        'tasks/016_disagreement_triggered_review_validation/CURRENT.md','outputs/016_disagreement_triggered_review_validation/CURRENT.md')]
    old_entries=list((ROOT/'tasks').glob('*/README.md'))+list((ROOT/'outputs').glob('*/README.md'))
    broken=[];links=[]
    for p in docs+old_entries:
        text=re.sub(r'```.*?```','',p.read_text(encoding='utf-8'),flags=re.S)
        for dest in re.findall(r'\[[^\]\n]*\]\(([^\)]+)\)',text):
            dest=dest.strip('<>').split('#',1)[0]
            if not dest or re.match(r'^[a-z]+:',dest,re.I):continue
            links.append((p.relative_to(ROOT).as_posix(),dest))
            if not (p.parent/dest).resolve().exists():broken.append(links[-1])
    assert not broken,broken
    for n in changed:
        data=(ROOT/n).read_bytes();prior=subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)
        assert not data.startswith(b'\xef\xbb\xbf')
        assert (b'\r\n' in data)==(b'\r\n' in prior),'Newline convention changed'
    for n in ('AGENTS.md','README.md','docs/API_POLICY.md','docs/aliyun/CURRENT.md','docs/siliconflow_pool/README.md'):
        t=(ROOT/n).read_text(encoding='utf-8')
        assert '80' in t and '通知' in t and '阿里云' in t,n
    agents=(ROOT/'AGENTS.md').read_text(encoding='utf-8')
    policy=agents.split('## API 调用费用与确认规则',1)[1].split('\n---',1)[0]
    assert all(x in policy for x in ('80元','所有启用账号','所有API','所有模型、账号、供应商和阶段','503','未知','不重置','016历史上限40元'))
    assert '默认费用保护上限80元' in policy
    summary=read(ROOT/'outputs/016_disagreement_triggered_review_validation/completion_002/analysis_001/summary.json')
    assert summary['correct']==dict(v4_first=446,qwen=457,cross_repeat=451,cross_review=452,released=489)
    assert not summary['passed'] and abs(summary['task_used_or_reserved_cny']-21.79039103)<1e-8
    assert 'PASS，无阻塞修正' in (ROOT/'reviews/016_disagreement_triggered_review_validation.md').read_text(encoding='utf-8')
    groups=read(ROOT/'outputs/003_error_analysis/patient_groups.json')['groups'];used=set()
    paths=['outputs/004_event_alignment_pilot/run_003/cohort_llm.csv','outputs/006_source_context_feasibility/preparation_001/cohort.csv',
        'outputs/007_context_retrieval/preparation_003/cohort.csv','outputs/008_retrieval_planning/preparation_001/cohort.csv',
        'outputs/009_retrieval_baselines/confirmation_001/preparation/cohort.csv','outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/cohort.csv']
    for n in paths:
        with (ROOT/n).open(encoding='utf-8-sig',newline='') as f:used.update(r['subject_id'] for r in csv.DictReader(f))
    assert len(used)==30 and used<=set(groups['development']) and len(set(groups['development'])-used)==10
    records=[dict(path=n,before_sha256=before[n],after_sha256=sha(ROOT/n)) for n in sorted(changed)]
    write(OUT/'changes_final.json',records)
    result=dict(status='documentation_self_check_passed',modified_existing_documents=sorted(changed),
        new_current_documents=[p.relative_to(ROOT).as_posix() for p in docs if p.relative_to(ROOT).as_posix() not in before],
        unchanged_tracked_files=len(before)-len(changed),audited016_handoff_files_unchanged=len(handoff),
        local_links_checked=len(links),broken_links=broken,encodings_and_newline_conventions_preserved=True,
        current_development_used=30,current_development_remaining=10,current_task_budget_cny=80,
        historical016_budget_cny=40,all_provider_pool_exhausted_not_asserted=True,new_API_calls=0,
        frozen_research_code_results_audits_unchanged=True,gitignore_and_gitattributes_unchanged=True)
    write(OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
