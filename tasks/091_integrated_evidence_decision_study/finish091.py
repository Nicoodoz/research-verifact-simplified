"""Narrow status synchronization and public delivery sealing."""
from common091 import *
import argparse,subprocess
def status():
    summary='091综合研究完成：新完整中文稿按证据/原生判定/决策边界组织；090自然167共同core的F4/P90 raw120/127、PriorG135/137，净优势7→2分解为7−4−1+2−2，未见一致类对排序改善；压力65最终净0，完整66净+1涉及fallback。C数值—单位原型盲盘点17条/8人、缺口4条/3人，未进入分类实测。0新API、¥0/20，未拟合或改默认；独立算式及执行者自检PASS，独立审计未执行。085已正式完成，旧暂停按历史理解；036仅用汇总、不用reserved开发，不改.gitignore、不自动092。'
    for rel in ('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md'):
        p=ROOT/rel;b=p.read_bytes();assert '**091最新'.encode() not in b;i=b.index(b'\n')+1;eol=b'\r\n' if b[:i].endswith(b'\r\n') else b'\n';prefix='../' if rel.startswith('docs/') else ''
        entry=f'**091最新（2026-09-27）：** {summary} [报告]({prefix}outputs/091_integrated_evidence_decision_study/report.md) · [完整稿]({prefix}outputs/091_integrated_evidence_decision_study/manuscript_zh.md)。'
        p.write_bytes(b[:i]+eol+entry.encode()+eol+b[i:])
def seal():
    assert read(OUT/'selfcheck.json')['status']=='PASS'
    if not (OUT/'cost_ledger.json').exists():put(OUT/'cost_ledger.json',dict(cap_original_cny=20,paid_API_attempts=0,known_cny=0,unknown_reserve_cny=0,inflight_cny=0,total_cny=0,construction_cny=0,main_cny=0,verification_cny=0,note='Offline analyses and public literature browsing only; no provider model requests. Historical expenses are not carried over.'))
    if not (OUT/'C_decision.json').exists():
        put(OUT/'C_decision.json',dict(status='FEASIBILITY_COMPLETE_NO_CLASSIFICATION_TRIAL',reason='17 eligible / 8 patients, only4 literal gaps /3 patients; minimum32 and at least8 per literal stratum unmet. Literal matching cannot certify predicate/time/negation linkage.',scientific_rule_versions=1,GT_joined=False,new_calls=0,source_sha256=bind([TASK/'c_materials091.py',TASK/'selective091.py',TASK/'test091.py',OUT/'C_material_inventory.json']),private_pool_sha256=sha(PRIVATE/'C_blind_pool.jsonl')))
    private_files={p.relative_to(ROOT).as_posix():sha(p) for p in PRIVATE.rglob('*') if p.is_file()}
    files=[p for root in (TASK,OUT) for p in root.rglob('*') if p.is_file() and p.name not in ('delivery_manifest.json','delivery_manifest.tmp')]
    secrets=[]
    for name in ('.env.aliyun','.env.siliconflow_pool'):
        if (ROOT/name).exists():
            for line in (ROOT/name).read_text(encoding='utf-8-sig').splitlines():
                if '=' not in line or line.lstrip().startswith('#'):continue
                k,v=line.split('=',1);v=v.strip().strip('\"\'')
                if ('KEY' in k.upper() or 'TOKEN' in k.upper()) and len(v)>12:secrets.append(v.encode())
    for p in files:
        b=p.read_bytes();assert not any(s in b for s in secrets),'credential copy';assert len(b)<20_000_000
    m=dict(status='PASS',created_utc=now(),public_files={p.relative_to(ROOT).as_posix():sha(p) for p in files},private_files=private_files,credential_scan='PASS',independent_audit=False)
    p=OUT/'delivery_manifest.tmp';put(p,m);p.replace(OUT/'delivery_manifest.json');print(canonical(dict(public_files=len(files),private_files=len(private_files),status='PASS')))
def stagecheck():
    m=read(OUT/'delivery_manifest.json')['public_files'];m[(OUT/'delivery_manifest.json').relative_to(ROOT).as_posix()]=sha(OUT/'delivery_manifest.json')
    raw=subprocess.check_output(['git','cat-file','--batch'],input=''.join(':'+p+'\n' for p in m).encode(),cwd=ROOT);pos=0
    for p,d in m.items():
        end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();assert len(head)==3 and head[1]=='blob',p;n=int(head[2]);start=end+1;assert hashlib.sha256(raw[start:start+n]).hexdigest()==d,p;pos=start+n+1
    names=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0');allowed={'AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md'}
    assert all(not n or n in allowed or n.startswith(('tasks/091_integrated_evidence_decision_study/','outputs/091_integrated_evidence_decision_study/')) for n in names)
    print(canonical(dict(status='PASS',exact_staged_blobs=len(m),private_files_staged=False)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('status','seal','stagecheck'));a=p.parse_args();globals()[a.action]()
