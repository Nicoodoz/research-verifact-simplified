"""Task navigation, publication scan and exact staged byte check."""
import argparse,subprocess
from common089 import *
def status():
    a=read(OUT/'analysis.json');c=a['cost'];n=a['panels']['natural']['full_metrics']['PriorG'];p=a['panels']['pressure']['full_metrics']['PriorG']
    summary=f"089固定示例压缩实测完成：P长槽排序接口失败保留全文，P4=F4共享同体；Q仅NS示例缩短。自然110条F/P/Q正确{n['F4']['correct']}/{n['P4']['correct']}/{n['Q4']['correct']}，MCC {n['F4']['MCC']:.4f}/{n['P4']['MCC']:.4f}/{n['Q4']['MCC']:.4f}；压力44条正确{p['F4']['correct']}/{p['P4']['correct']}/{p['Q4']['correct']}，两面板分报。{c['attempts']}次尝试、原价¥{c['total_original_or_unknown_cny']:.6f}/20。P覆盖机制未成功测试，不把同体零差当等效；不升级默认、不自动090。自检PASS、独立审计未执行；085A/R1/AWS继续暂停。"
    for rel in ('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/REPRODUCIBILITY.md'):
        path=ROOT/rel;b=path.read_bytes();assert b'**089' not in b
        link=('../' if rel.startswith('docs/') else '')+'outputs/089_source_audited_demo_compression/'
        entry=f'**089最新（2026-09-26）：** {summary} [报告]({link}report.md) · [交审]({link}audit_handoff.md)。'
        pos=b.index(b'\n')+1;eol=b'\r\n' if b[:pos].endswith(b'\r\n') else b'\n';path.write_bytes(b[:pos]+eol+entry.encode()+eol+b[pos:])
    p=ROOT/'.gitattributes';b=p.read_bytes();assert b'docs/089_* -text' not in b
    eol=b'\r\n' if b.split(b'\n',1)[0].endswith(b'\r') else b'\n';p.write_bytes(b+eol+b'# Preserve the frozen 089 task instruction bytes.'+eol+b'docs/089_* -text'+eol)
def seal():
    assert read(OUT/'selfcheck.json')['status']=='PASS' and not (OUT/'run.lock').exists()
    dest=OUT/'delivery_manifest.json';temp=OUT/'delivery_manifest.tmp';assert not temp.exists()
    files=sorted(p for folder in (TASK,OUT) for p in folder.rglob('*') if p.is_file() and p!=dest)
    secrets=[]
    for env in ('.env.aliyun','.env.siliconflow_pool'):
        if (ROOT/env).exists():
            for line in (ROOT/env).read_text(encoding='utf-8-sig').splitlines():
                if '=' not in line or line.lstrip().startswith('#'):continue
                k,v=line.split('=',1);v=v.strip().strip('\"\'')
                if ('KEY' in k.upper() or 'TOKEN' in k.upper()) and len(v)>=12:secrets.append(v.encode())
    for p in files:
        b=p.read_bytes();assert not b.startswith(b'\xef\xbb\xbf') and len(b)<95_000_000
        if any(s in b for s in secrets):raise RuntimeError('credential detected in deliverable')
    put(temp,dict(status='PASS',created_utc=now(),files=len(files),credential_scan='PASS',independent_audit=False,sha256={p.relative_to(ROOT).as_posix():sha(p) for p in files}))
    temp.replace(dest);print(canonical(dict(files=len(files),bytes=sum(p.stat().st_size for p in files))))
def stagecheck():
    hashes=read(OUT/'delivery_manifest.json')['sha256'];hashes.update(read(OUT/'constructor_freeze.json')['sources'])
    hashes[(OUT/'delivery_manifest.json').relative_to(ROOT).as_posix()]=sha(OUT/'delivery_manifest.json')
    paths=list(hashes);r=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=''.join(':'+p+'\n' for p in paths).encode(),stdout=subprocess.PIPE,check=True)
    raw=r.stdout;offset=0
    for p in paths:
        end=raw.index(b'\n',offset);head=raw[offset:end].decode().split();assert len(head)==3 and head[1]=='blob',p
        size=int(head[2]);start=end+1;assert hashlib.sha256(raw[start:start+size]).hexdigest()==hashes[p],p;offset=start+size+1
    assert offset==len(raw)
    changed=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
    allowed={'.gitattributes','AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/REPRODUCIBILITY.md','docs/089_Codex_具体遗漏核对驱动的示例压缩与实测_执行提示词.md'}
    assert all(not p or p in allowed or p.startswith('tasks/089_source_audited_demo_compression/') or p.startswith('outputs/089_source_audited_demo_compression/') for p in changed)
    print(canonical(dict(status='PASS',staged_exact_blobs=len(paths))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('status','seal','stagecheck'));a=p.parse_args();globals()[a.action]()
