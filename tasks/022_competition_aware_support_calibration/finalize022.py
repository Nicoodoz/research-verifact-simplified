"""Finish navigation and create concrete audit fingerprint; no API/commit/push."""
from pathlib import Path
import argparse,re,subprocess
import common022 as c
from sync022 import replace
NAV=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md','docs/aliyun/CURRENT.md','reviews/README.md','.gitattributes']

def after_line(path,prefix,addition):
    p=c.ROOT/path;raw=p.read_bytes();ls=raw.splitlines(keepends=True);ix=[i for i,l in enumerate(ls) if l.startswith(prefix.encode())]
    c.require(len(ix)==1,'Table marker');i=ix[0];nl=b'\r\n' if ls[i].endswith(b'\r\n') else b'\n';ls.insert(i+1,addition.encode()+nl);p.write_bytes(b''.join(ls))

def sync_tail():
    after_line('README.md','| `021_bge_localization`','| `022_competition_aware_support_calibration` | 阶段A停止；待独立审计 | [任务](tasks/022_competition_aware_support_calibration/README.md) · [报告](outputs/022_competition_aware_support_calibration/report.md) · [交审](outputs/022_competition_aware_support_calibration/audit_handoff.md) |')
    after_line('README.md','| 021：','| 022：竞争感知校准 | [主报告](outputs/022_competition_aware_support_calibration/report.md) | [待独立审计，阶段A停止](outputs/022_competition_aware_support_calibration/audit_handoff.md) |')
    after_line('docs/PROJECT_STATUS.md','| 021 |','| 022 | 16人1529条R0与879条R1折外筛查；竞争感知与全局λ同标签，较U2 PA/MCC不达门槛。停止收费阶段，保留λ2；0元 | [报告](../outputs/022_competition_aware_support_calibration/report.md) · [待审交接](../outputs/022_competition_aware_support_calibration/audit_handoff.md) |')
    for p in ('README.md','AGENTS.md'):
        replace(p,'**当前状态（2026-09-19）：019–021快速独立审计PASS，可冻结／结项。**','**此前已审状态：019–021快速独立审计PASS，可冻结／结项。**')
    replace('README.md','当前阶段：021已完成','当前022按阶段A门槛停止、待独立审计，保留λ2；0新增API。此前021已完成')
    replace('README.md','后续收费API先使用硅基流动启用池，只有全池真实明确耗尽后通知并转阿里云单key；跨阶段、账号、平台累计80元。','022按模型分流：BGE继续硅基流动冻结缓存，Judge直接阿里云0731，不等待池耗尽；全任务累计80元。022已停止，不自动新增调用。')
    replace('AGENTS.md','后续收费API统一先硅基流动启用池，全池真实明确耗尽后通知并转阿里云单key；跨阶段/账号/平台累计80元。此前“Qwen直接阿里云”按历史版本理解。','019–021的先硅基流动全池、耗尽后阿里云规则属于历史阶段；022以顶部BGE/主Judge分流为准，累计80元上限不变。')
    replace('AGENTS.md','本轮用户明确授权同步.gitignore、环境和说明后推送GitHub。','019–021审计收尾曾获用户授权同步.gitignore、环境并推送；该历史授权不用于022自动commit/push。')
    replace('docs/PROJECT_STATUS.md','未来收费任务先硅基流动启用池，全池明确耗尽后通知并转阿里云单key。','022的BGE继续硅基流动缓存，主Judge直接阿里云0731；旧通用路由不覆盖022专项授权。')
    replace('docs/API_POLICY.md','更新：2026-09-19。以用户019–021阶段最新路由指示为准；旧文档“Qwen直接阿里云”仅反映此前版本。','更新：2026-09-19。022按顶部专项路由；下方019–021规则保留历史含义。')
    replace('docs/aliyun/CURRENT.md','按019–021阶段用户最新指示，后续收费API（含Qwen）先用硅基流动启用号池；全部明确余额耗尽后，执行者须通知用户，将DeepSeek、Qwen等所有API工作转阿里云。','022最新专项指示：主Judge直接阿里云DeepSeek V4 Flash，优先核实并冻结deepseek-v4-flash-0731；可选Qwen也走阿里云，不等待硅基流动池耗尽。Embedding/reranker仍采用硅基流动API冻结缓存。022已在零API阶段A停止，没有新增阿里云性能或可用性结果。')
    print('Navigation and API-specific override complete.')

def handoff():
    for p in ('preparation_001','stageA_002','verification_001'):c.check(c.OUT/p)
    missing=[]
    for path in [*c.TASK.glob('*.md'),*c.OUT.glob('*.md')]:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            if not (path.parent/link.split('#')[0]).resolve().exists():missing.append([str(path),link])
    c.require(not missing,'Broken links: '+c.canonical(missing))
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();c.require(set(changed)<=set(NAV),'Historical tracked modification')
    files={p.relative_to(c.ROOT).as_posix():c.sha(p) for root in (c.TASK,c.OUT) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update({name:c.sha(c.ROOT/name) for name in NAV+['docs/022_竞争感知支持边界校准_任务计划.md']})
    c.write(c.OUT/'handoff_001.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),status='completed_stageA_stop_pending_independent_audit',git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),files=files,tests=dict(task022=12,evaluator002=15),replayed_content_files=15,new_API_calls=0,cost_cny=0,stageB_executed=False,reserved_test_used=False,git_commit_push=False))
    print('Audit handoff saved; files',len(files))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sync-tail',action='store_true');a=p.parse_args();sync_tail() if a.sync_tail else handoff()
