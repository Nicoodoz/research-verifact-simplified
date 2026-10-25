"""Current navigation only; original documents retain bytes except targeted edits."""
import common022 as c

def replace(path,old,new):
    p=c.ROOT/path;raw=p.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n'
    old=old.replace('\n',nl).encode();new=new.replace('\n',nl).encode()
    c.require(raw.count(old)==1,'Navigation marker: '+path);p.write_bytes(raw.replace(old,new,1))

if __name__=='__main__':
    msg='022完成零API阶段A：16名development患者1529条R0＋879条R1折外评分，竞争感知与学习全局λ的2408条标签完全相同；相对U2正确数R0−28、R1−13，false-S虽减少但PA/MCC未达门槛。停止B/Qwen，保留λ=2；新增费用0/80元，待独立审计。'
    route='022最新按模型分流：Embedding/reranker继续硅基流动Pro BGE并优先复用冻结缓存；主Judge直接阿里云DeepSeek V4 Flash，固定0731快照须在实际发送前核实，不等待硅基流动池耗尽。可选Qwen也走阿里云。022已在阶段A停止，本指示不自动启动新调用；历史019–021路由不回写。'
    replace('README.md','# Research-VeriFact','# Research-VeriFact\n\n**当前022：** '+msg+'[中文主报告](outputs/022_competition_aware_support_calibration/report.md) · [交审](outputs/022_competition_aware_support_calibration/audit_handoff.md)。')
    replace('AGENTS.md','# 项目背景','# 项目背景\n\n**022当前（2026-09-19）：** '+msg+'[主报告](outputs/022_competition_aware_support_calibration/report.md)。\n\n'+route)
    replace('docs/PROJECT_STATUS.md','# 项目现状总览','# 项目现状总览\n\n**022当前：** '+msg+'[主报告](../outputs/022_competition_aware_support_calibration/report.md) · [交审](../outputs/022_competition_aware_support_calibration/audit_handoff.md)。\n\n'+route)
    replace('docs/API_POLICY.md','# API现行执行约定','# API现行执行约定\n\n**022最新专项授权（2026-09-19，优先于下方旧通用路由）：** '+route+'累计上限80元包含所有阶段/模型/异常，本轮实际0元。')
    replace('docs/API_POLICY.md','## 路由','## 019–021阶段路由（历史；022以顶部专项规则为准）')
    replace('reviews/README.md','# 独立审计记录与后续状态','# 独立审计记录与后续状态\n\n**022待独立审计：** '+msg+'[报告](../outputs/022_competition_aware_support_calibration/report.md) · [交接](../outputs/022_competition_aware_support_calibration/audit_handoff.md)。当前没有022独立PASS结论。')
    p=c.ROOT/'.gitattributes';raw=p.read_bytes();c.require(b'tasks/022_competition_aware_support_calibration/**' not in raw,'Already has022 attributes');nl=b'\r\n' if b'\r\n' in raw else b'\n';p.write_bytes(raw+(b'' if raw.endswith(b'\n') else nl)+b'tasks/022_competition_aware_support_calibration/** -text'+nl)
    # Append task mapping next to021 without relying on an outdated exact row.
    p=c.ROOT/'README.md';raw=p.read_bytes();lines=raw.splitlines(keepends=True);matches=[i for i,line in enumerate(lines) if line.startswith(b'| `021_bge_localization`')]
    c.require(len(matches)==1,'021 task table anchor');i=matches[0];nl=b'\r\n' if lines[i].endswith(b'\r\n') else b'\n'
    lines.insert(i+1,'| `022_competition_aware_support_calibration` | 阶段A停止；待独立审计 | [任务](tasks/022_competition_aware_support_calibration/README.md) · [报告](outputs/022_competition_aware_support_calibration/report.md) · [交审](outputs/022_competition_aware_support_calibration/audit_handoff.md) |'.encode()+nl);p.write_bytes(b''.join(lines))
    print('Current navigation/API policy synced; .gitignore untouched.')
