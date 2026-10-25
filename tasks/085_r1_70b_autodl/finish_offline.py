"""Offline evidence capture, new current-status notices, no commit or live inference."""
import argparse,subprocess
from common import *
def capture():
    commands={
        'client_dry_run':[sys.executable,'-B',str(TASK/'runner.py'),'dry-run'],
        'server_dry_run':[sys.executable,'-B',str(TASK/'remote_server.py'),'launch','--dry-run'],
        'gpu_ledger_empty':[sys.executable,'-B',str(TASK/'runtime_ledger.py'),'summary']}
    results={}
    for name,cmd in commands.items():
        r=subprocess.run(cmd,cwd=ROOT,text=True,encoding='utf-8',capture_output=True,check=True)
        results[name]=json.loads(r.stdout)
    put(OUT/'dry_run_evidence.json',dict(created_utc=now(),results=results,real_inference_calls=0))
def status():
    for rel in ('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/RUN_ENVIRONMENT.md','docs/REPRODUCIBILITY.md'):
        p=ROOT/rel;b=p.read_bytes();marker='**085 AutoDL恢复（2026-09-26）：**';assert marker.encode() not in b
        prefix='../' if rel.startswith('docs/') else ''
        entry=marker+' 用户恢复085并改走手工管理AutoDL/direct vLLM；旧085A/AWS文件和暂停历史不改。精确AWQ仓库及resolved revision已锁定，084的180条/21患者与360个B/F4输入复用，V4不重调。离线adapter/脚本/manifest/账本/预检及评价就绪，自检2308项、11项测试PASS；0推理/0新API费，实际GPU与端点未验证，租金未知。等待用户建立tunnel、提供实际manifest与小时单价；A/B后先预测费用，正式大批量须另行明确授权。默认不变、不用reserved、不改.gitignore、不自动其他任务；正式085完成后提交推送。'+f' [操作说明]({prefix}tasks/085_r1_70b_autodl/AUTODL_HANDOFF.md) · [离线报告]({prefix}outputs/085_r1_70b_autodl/report_offline.md)。'
        pos=b.index(b'\n')+1;eol=b'\r\n' if b[:pos].endswith(b'\r\n') else b'\n';p.write_bytes(b[:pos]+eol+entry.encode()+eol+b[pos:])
def seal():
    files=sorted(p for f in (TASK,OUT) for p in f.rglob('*') if p.is_file() and p.name!='delivery_manifest.json')
    secrets=[]
    for name in ('.env.aliyun','.env.siliconflow_pool'):
        p=ROOT/name
        if p.exists():
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                if '=' not in line or line.lstrip().startswith('#'):continue
                k,v=line.split('=',1);v=v.strip().strip('\"\'')
                if ('KEY' in k.upper() or 'TOKEN' in k.upper()) and len(v)>=12:secrets.append(v.encode())
    for p in files:
        b=p.read_bytes()
        if any(s in b for s in secrets):raise RuntimeError('Secret detected in deliverable')
        assert not b.startswith(b'\xef\xbb\xbf') and len(b)<95_000_000
    put(OUT/'delivery_manifest.json',dict(status='PASS',created_utc=now(),credential_scan='PASS',files=len(files),sha256={p.relative_to(ROOT).as_posix():sha(p) for p in files},independent_audit=False,formal_085_complete=False))
    print(canonical(dict(files=len(files),bytes=sum(p.stat().st_size for p in files),formal_complete=False)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('capture','status','seal'));a=p.parse_args();globals()[a.action]()
