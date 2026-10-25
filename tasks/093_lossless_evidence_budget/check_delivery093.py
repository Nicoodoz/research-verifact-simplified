"""Final delivery verification, including frozen artifacts and navigation links."""
import ast,json,re
import common093 as c
import api093
def main():
    api093.load_jobs()
    for path,sha in c.read(c.OUT/'completion.json')['artifacts'].items():assert c.sha(c.ROOT/path)==sha,path
    for path,sha in c.read(c.OUT/'source_manifest.json')['historical_sha256'].items():assert c.sha(c.ROOT/path)==sha,path
    paths=list(c.OUT.glob('*.md'))+list(c.TASK.glob('*.md'))+[c.ROOT/p for p in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/TASK_INDEX.md']]
    for p in paths:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
            if not link.startswith(('http','#')):assert (p.parent/link.split('#')[0]).exists(),(p,link)
    for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    for p in list(c.TASK.rglob('*'))+list(c.OUT.rglob('*')):
        if p.is_file() and '__pycache__' not in str(p):
            s=p.read_text(encoding='utf-8-sig');assert not re.search(r'sk-[A-Za-z0-9]{20,}',s),p
            if p.suffix in ['.md','.json','.jsonl']:assert ' | Text: ' not in s and '[**' not in s,p
    attempts,success,_=api093.state();assert len(attempts)==len(success)==153
    assert not (c.PRIVATE/'run.lock').exists()
    c.put(c.OUT/'delivery_selfcheck.json',dict(status='PASS',frozen_inputs_unchanged=True,completion_artifacts_unchanged=True,historical_sources_unchanged=True,links_valid=True,no_raw_clinical_markers_or_key_patterns=True,API_stopped=True,executor_selfcheck=True,independent_audit=False,utc=c.now()))
    print('Final delivery verification PASS; 153 completed responses; no active run.')
if __name__=='__main__':main()
