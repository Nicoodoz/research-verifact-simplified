"""Current-navigation update and export checks, not scientific-result mutation."""
import argparse,subprocess
from common088 import *

def status():
    assert read(OUT/'decision.json')['status']=='STOP_INPUT_EQUIVALENCE_NO_COMPRESSION'
    for rel in ('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/REPRODUCIBILITY.md'):
        p=ROOT/rel;data=p.read_bytes();assert b'**088' not in data
        link=('../' if rel.startswith('docs/') else '')+'outputs/088_evidence_preserving_demonstration_compression/'
        if rel.endswith('API_POLICY.md'):
            entry=f'**088专项结项（2026-09-26）：** 固定Qwen快照构造2次HTTP200，输入10298/输出698 token，原价¥0.0034556/20，0重试/未知。P4=Q4=F4且无压缩，按事前输入等价门槛未启动主Judge/Q构造/源核对；无历史余额结转。[账本]({link}cost_ledger.json) · [报告]({link}report.md)。'
        elif rel.endswith('REPRODUCIBILITY.md'):
            entry=f'**088只读入口（2026-09-26）：** 构造阶段按三臂输入等价停止，不是待补跑主实验；`verify088.py`只读核对冻结、原文、真实回执和费用，不联网。[交审]({link}audit_handoff.md)。不要删除冻结文件重跑构造，不自动089。'
        else:
            entry=f'**088最新（2026-09-26）：** 固定示例原文抽取原型完成；两条短S保留，NS/NA长例均被固定Qwen构造器标记保留全文，最终P4=Q4=F4逐字相同、0%压缩。按事前第6节停止无信息量主重复，分类质量未评价、P特有机制未测试，不能写成等效或压缩原则上不可行。2次构造HTTP200、原价¥0.0034556/20，源核对/Q构造/主Judge均0次；自检136项及8项合成测试PASS，独立审计未执行。默认B/Frozen PriorG不变，087/086不回写，085A/R1/AWS暂停，不用reserved、不改.gitignore、不自动089；按用户授权提交推送。[088报告]({link}report.md) · [决策]({link}decision.json)。'
        pos=data.index(b'\n')+1;eol=b'\r\n' if data[:pos].endswith(b'\r\n') else b'\n'
        p.write_bytes(data[:pos]+eol+entry.encode()+eol+data[pos:])
    p=ROOT/'.gitattributes';data=p.read_bytes();assert b'docs/088_* -text' not in data
    eol=b'\r\n' if data.split(b'\n',1)[0].endswith(b'\r') else b'\n'
    p.write_bytes(data+eol+b'# Preserve the frozen 088 task instruction bytes.'+eol+b'docs/088_* -text'+eol)
    print('Current navigation updated; original bytes retained.')

def seal():
    assert read(OUT/'selfcheck.json')['status']=='PASS'
    assert not (OUT/'run.lock').exists()
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
    put(temp,dict(status='PASS',created_utc=now(),files=len(files),credential_scan='PASS',independent_audit=False,
                  sha256={p.relative_to(ROOT).as_posix():sha(p) for p in files}))
    temp.replace(dest);print(canonical(dict(status='PASS',files=len(files),bytes=sum(p.stat().st_size for p in files))))

def stagecheck():
    hashes=read(OUT/'delivery_manifest.json')['sha256'];hashes.update(read(OUT/'constructor_freeze.json')['sources'])
    hashes[(OUT/'delivery_manifest.json').relative_to(ROOT).as_posix()]=sha(OUT/'delivery_manifest.json')
    paths=list(hashes)
    result=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=''.join(':'+p+'\n' for p in paths).encode(),stdout=subprocess.PIPE,check=True)
    raw=result.stdout;offset=0
    for p in paths:
        end=raw.index(b'\n',offset);head=raw[offset:end].decode().split();assert len(head)==3 and head[1]=='blob',p
        size=int(head[2]);start=end+1
        assert hashlib.sha256(raw[start:start+size]).hexdigest()==hashes[p],p
        offset=start+size+1
    assert offset==len(raw)
    print(canonical(dict(status='PASS',staged_exact_blobs=len(paths))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('status','seal','stagecheck'));a=p.parse_args()
    globals()[a.action]()
