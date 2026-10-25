"""Check delivered reports/navigation after scientific checks; never calls a model."""
import ast,re
import common094 as c
import api094
def main():
    for p,h in c.read(c.OUT/'completion.json')['artifacts'].items():assert c.sha(c.ROOT/p)==h,p
    paths=list(c.OUT.glob('*.md'))+list(c.TASK.glob('*.md'))+[c.ROOT/p for p in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/TASK_INDEX.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md']]
    for p in paths:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
            if not link.startswith(('http','#')):assert (p.parent/link.split('#')[0]).exists(),(p,link)
    for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    for folder in [c.TASK,c.OUT]:
        for p in folder.rglob('*'):
            if not p.is_file() or '__pycache__' in str(p):continue
            text=p.read_text(encoding='utf-8-sig');assert not re.search(r'sk-[A-Za-z0-9]{20,}',text),p
            if p.suffix in ['.md','.json','.jsonl'] and p.name!='preflight_result.json':assert '[**' not in text and ' | Text: ' not in text,p
    attempts,s=api094.state();assert len(s)==157 and not (c.PRIVATE/'run.lock').exists()
    c.put(c.OUT/'delivery_selfcheck.json',dict(status='PASS',utc=c.now(),all_completion_hashes=True,links=True,syntax=True,privacy_markers=True,API_stopped=True,executor_selfcheck=True,independent_audit=False))
    print('Final delivery verification PASS')
if __name__=='__main__':main()
