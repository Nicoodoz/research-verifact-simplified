"""Status and public-only delivery seal; never stages private clinical artifacts."""
import argparse,subprocess,datetime
from common090 import *
def status():
    date=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
    a=read(PUB/'analysis.json');cost=a['cost'];n=a['panels']['natural'];p=a['panels']['pressure']
    seq=['B','F4','P90','Q90'];ns='/'.join(str(n['full_metrics']['PriorG'][k]['correct']) for k in seq if k in n['full_metrics']['PriorG']);ps='/'.join(str(p['full_metrics']['PriorG'][k]['correct']) for k in seq if k in p['full_metrics']['PriorG'])
    summary=f"090固定示例构造修复与同期比较完成：P两长槽真实构造，第2工程版只分离不相容来源替代项并补回具体遗漏；自然{n['n']}条B/F4/P90/Q90＋PriorG正确{ns}，压力{p['n']}条正确{ps}，两面板分报。原价及未知预留¥{cost['total_original_or_unknown_cny']:.6f}/40，构造/测试/核对¥{cost['construction_review_coverage_cny']:.6f}/4。自检PASS、独立审计未执行。默认不变、不用reserved、不改.gitignore；新临床原文/回执仅私有忽略目录，公开ID/哈希/指标。今晚085/AutoDL/AWS/R1暂停，Casperhansen0.9.2与Valdemardi0.10.1.1差异只备忘、不改身份锁；不自动091。"
    for rel in ('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/REPRODUCIBILITY.md','docs/RUN_ENVIRONMENT.md'):
        path=ROOT/rel;b=path.read_bytes();assert '**090最新'.encode() not in b
        prefix='../' if rel.startswith('docs/') else ''
        entry=f'**090最新（{date}）：** {summary} [报告]({prefix}outputs/090_demo_constructor_repair_validation/report.md) · [085备忘]({prefix}outputs/090_demo_constructor_repair_validation/085_resume_memo.md)。'
        i=b.index(b'\n')+1;eol=b'\r\n' if b[:i].endswith(b'\r\n') else b'\n';path.write_bytes(b[:i]+eol+entry.encode()+eol+b[i:])
    path=ROOT/'.gitattributes';b=path.read_bytes()
    if b'docs/090_* -text' not in b:
        eol=b'\r\n' if b.split(b'\n',1)[0].endswith(b'\r') else b'\n';path.write_bytes(b+eol+b'# Preserve frozen090 instruction bytes.'+eol+b'docs/090_* -text'+eol)
def seal():
    assert read(PUB/'selfcheck.json')['status']=='PASS' and not (OUT/'run.lock').exists()
    dest=PUB/'delivery_manifest.json';files=sorted(p for folder in (TASK,PUB) for p in folder.rglob('*') if p.is_file() and p!=dest)
    secrets=[]
    for env in ('.env.aliyun','.env.siliconflow_pool'):
        if (ROOT/env).exists():
            for line in (ROOT/env).read_text(encoding='utf-8-sig').splitlines():
                if '=' not in line or line.lstrip().startswith('#'):continue
                k,v=line.split('=',1);v=v.strip().strip('\"\'')
                if ('KEY' in k.upper() or 'TOKEN' in k.upper()) and len(v)>=12:secrets.append(v.encode())
    # Check actual source claims/references are not newly copied to public deliverables.
    samples=lines(OUT/'sample_blind.jsonl');demo=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl')
    sensitive=[x['reference'].encode() for x in samples+demo]
    for p in files:
        b=p.read_bytes();assert not b.startswith(b'\xef\xbb\xbf') and len(b)<95_000_000
        if any(s in b for s in secrets):raise RuntimeError('Credential found in public delivery')
        if any(s in b for s in sensitive):raise RuntimeError('Complete clinical reference found in public delivery')
    # Clinical JSON strings are escaped, so inspect parsed textual fields as well.
    forbidden={'claim','reference','source_units','constructor_output','review_output','body_text','reasoning_content','original_reference'}
    def inspect(x):
        if isinstance(x,dict):
            assert not forbidden.intersection(x),'Unexpected clinical text field in public JSON'
            for v in x.values():inspect(v)
        elif isinstance(x,list):
            for v in x:inspect(v)
    for p in PUB.rglob('*.json'):
        if p.name=='checker_test_results.json':continue  # entirely fictional fixtures, explicitly reviewed
        inspect(read(p))
    for p in PUB.glob('*.jsonl'):
        for x in lines(p):inspect(x)
    value=dict(status='PASS',created_utc=now(),public_files=len(files),credential_scan='PASS',clinical_text_scope_scan='PASS',private_root=OUT.relative_to(ROOT).as_posix(),
        sha256={p.relative_to(ROOT).as_posix():sha(p) for p in files},independent_audit=False)
    temp=PUB/'delivery_manifest.tmp';put(temp,value);temp.replace(dest);print(canonical(dict(status='PASS',public_files=len(files))))
def stagecheck():
    m=read(PUB/'delivery_manifest.json')['sha256'];m[(PUB/'delivery_manifest.json').relative_to(ROOT).as_posix()]=sha(PUB/'delivery_manifest.json')
    m[(ROOT/'docs/090_Codex_夜间构造修复与示例方案补验_执行提示词.md').relative_to(ROOT).as_posix()]=sha(ROOT/'docs/090_Codex_夜间构造修复与示例方案补验_执行提示词.md')
    raw=subprocess.check_output(['git','cat-file','--batch'],input=''.join(':'+p+'\n' for p in m).encode(),cwd=ROOT);pos=0
    for p,d in m.items():
        end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();assert len(head)==3 and head[1]=='blob',p;n=int(head[2]);start=end+1
        assert hashlib.sha256(raw[start:start+n]).hexdigest()==d,p;pos=start+n+1
    names=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
    allowed={'.gitattributes','AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/REPRODUCIBILITY.md','docs/RUN_ENVIRONMENT.md','docs/090_Codex_夜间构造修复与示例方案补验_执行提示词.md'}
    assert all(not n or n in allowed or n.startswith(('tasks/090_demo_constructor_repair_validation/','outputs/090_demo_constructor_repair_validation/')) for n in names)
    print(canonical(dict(status='PASS',exact_staged_blobs=len(m),private_files_staged=False)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('status','seal','stagecheck'));a=p.parse_args();globals()[a.action]()
