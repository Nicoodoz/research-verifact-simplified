"""Offline documentation/configuration audit; never executes research tasks."""
import json,hashlib,re,subprocess
from pathlib import Path
from ruamel.yaml import YAML
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    changes=read(HERE/'changes.json');checks=[];errors=[]
    def check(ok,name):
        checks.append(dict(name=name,passed=bool(ok)))
        if not ok:errors.append(name)
    for v in changes:
        p=ROOT/v['path'];check(p.is_file(),'exists '+v['path']);check(sha(p)==v['after_sha256'],'current hash '+v['path'])
        if v['archive']:
            a=ROOT/v['archive'];check(sha(a)==v['before_sha256'],'original bytes '+v['path'])
        else:check(not p.read_bytes().startswith(b'\xef\xbb\xbf'),'new UTF8 without BOM '+v['path'])
    yaml=YAML(typ='safe')
    envs={name:yaml.load((ROOT/name).read_text()) for name in ['environment.yml','environment.legacy-analysis.yml','environment.local-bge.yml','environment.local-verifier.yml','environment.autodl-verifier.yml']}
    def pins(env):
        values=next(d['pip'] for d in env['dependencies'] if isinstance(d,dict) and 'pip' in d)
        return dict(v.split('==',1) for v in values if '==' in v)
    cpu=read(HERE/'cpu_packages.json')['packages'];local=read(HERE/'local_verifier_environment.json')['versions']
    check(envs['environment.yml']['name']=='research-verifact-029','CPU name matches launcher')
    check('-n research-verifact-029' in (ROOT/'scripts/run_research.ps1').read_text(),'launcher uses documented environment')
    for name,value in pins(envs['environment.yml']).items():check(cpu.get(name)==value,'CPU pin '+name)
    for name,value in pins(envs['environment.local-verifier.yml']).items():check(local.get(name)==value,'local GPU pin '+name)
    cloud=(ROOT/'outputs/092_task_adapted_verifier/092_autodl_environment.txt').read_text()
    for name,value in pins(envs['environment.autodl-verifier.yml']).items():
        check((name+'=='+value) in cloud or name=='torch' and ('torch: '+value) in cloud,'cloud pin '+name)
    check(envs['environment.legacy-analysis.yml']['name']=='research-verifact','legacy name preserved')
    check(pins(envs['environment.legacy-analysis.yml'])==pins(yaml.load((ROOT/'docs/history/2026-09-27_before_sync/environment.yml.snapshot.txt').read_text())),'legacy exact dependencies preserved')
    check(pins(envs['environment.local-bge.yml'])==pins(yaml.load((ROOT/'docs/history/2026-09-27_before_sync/environment.local-bge.yml.snapshot.txt').read_text())),'021 dependency pins unchanged')
    check(read(HERE/'cpu_environment.json')['passed'],'CPU smoke test passed')
    canonical=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/RUN_ENVIRONMENT.md','docs/REPRODUCIBILITY.md','docs/TASK_INDEX.md','docs/README.md','docs/aliyun/README.md','docs/aliyun/CURRENT.md','reviews/README.md']
    linkcount=0
    for v in changes:
        name=v['path'];p=ROOT/name
        if p.suffix!='.md':continue
        body=p.read_text(encoding='utf-8-sig')
        if name.startswith('tasks/') and not name.startswith('tasks/092_'):body=body.split('## 原任务阶段说明（历史）')[0]
        if name.startswith('docs/VeriFact_论文草稿'):body=body.split('\n\n',1)[0]
        # Existing legacy client examples are retained; current links are all relative or HTTPS.
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',body):
            if '://' in target or target.startswith('#'):continue
            path=target.split('#')[0]
            check((p.parent/path).exists(),'link '+name+' -> '+path);linkcount+=1
        if name in canonical:
            check('2026-09-27' in body or '092' in body,'current date/scope '+name)
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()
    check(not any(p.startswith(('outputs/','src/','tests/','reviews/artifacts/','docs/sources/')) for p in changed),'frozen outputs/source/audit evidence unchanged')
    check(not any(p.startswith('tasks/') and Path(p).name not in ['README.md','AUTODL_HANDOFF.md'] and not Path(p).name.startswith('CURRENT') for p in changed),'task protocols and scientific code unchanged')
    check('.gitignore' not in changed,'gitignore unchanged')
    check(not any(p.startswith('reviews/') and p!='reviews/README.md' for p in changed),'independent audit judgments unchanged')
    inventory=read(HERE/'inventory.json');check(len(inventory)==len({v['path'] for v in inventory}),'documentation inventory unique')
    # User's unrelated pending files remain outside maintenance staging scope.
    check('docs/002提示词.txt' not in {v['path'] for v in changes},'unrelated deletion not part of change manifest')
    status=dict(status='PASS' if not errors else 'FAIL',executor_selfcheck=True,independent_audit=False,checks=len(checks),failures=errors,links_checked=linkcount,updated_files=len(changes),inventoried_tracked_documents=len(inventory),API_calls=0,environments_installed_or_upgraded=False,research_outputs_modified=False,scope='current docs, exact archives, live CPU/metadata versions, YAML parsing and links')
    (HERE/'verification.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(status,ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
