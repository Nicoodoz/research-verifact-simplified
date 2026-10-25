"""One-time current navigation sync; preserve all existing bytes outside inserts."""
import common018 as c

def insert(path,anchor,text,after=True):
    p=c.ROOT/path;data=p.read_bytes();newline=b'\r\n' if b'\r\n' in data else b'\n'
    marker=anchor.encode('utf-8');addition=text.replace('\n','\r\n' if newline==b'\r\n' else '\n').encode('utf-8')
    c.require(data.count(marker)==1,'Navigation anchor not unique: '+path)
    c.require(addition not in data,'Navigation already synced: '+path)
    p.write_bytes(data.replace(marker,marker+addition if after else addition+marker,1))

if __name__=='__main__':
    msg='018完成010/016两批12名已暴露患者1251条离线差距诊断：原VeriFact独对156、C48＋V4独对84，净差+72主要来自S召回，同时false-S为79/27且原系统MCC点估计更低。010固定V4后发布reference净−15，不支持将发布系统PA优势主要归于reference。优先研究Judge支持边界；真实可优化净headroom仍unknown。78例深读，186条方向性机制未充分深读，保留unknown；0新增API，无新优化或新患者实验。'
    insert('README.md','# Research-VeriFact','\n\n**当前018：** '+msg+'执行完成、待独立审计。见[唯一中文主报告](outputs/018_verifact_gap_attribution/report.md)与[交审入口](outputs/018_verifact_gap_attribution/audit_handoff.md)。')
    p=c.ROOT/'README.md';data=p.read_bytes();p.write_bytes(data.replace('**当前017：**'.encode(),'**017历史结果：**'.encode(),1))
    anchor='| `017_verification_supervised_evidence_utility` | 快速独立审计PASS；第一阶段未达门槛，停止 | [任务](tasks/017_verification_supervised_evidence_utility/README.md) · [中文主报告](outputs/017_verification_supervised_evidence_utility/report.md) · [独立审计](reviews/017_verification_supervised_evidence_utility.md) |'
    insert('README.md',anchor,'\n| `018_verifact_gap_attribution` | 离线诊断完成；待独立审计 | [任务](tasks/018_verifact_gap_attribution/README.md) · [中文主报告](outputs/018_verifact_gap_attribution/report.md) · [交审](outputs/018_verifact_gap_attribution/audit_handoff.md) |')
    insert('AGENTS.md','## 当前研究状态','\n\n018已完成跨队列离线诊断，待独立审计；[唯一主报告](outputs/018_verifact_gap_attribution/report.md)。'+msg+'018不构成新方法验证，不自动启动后续实验。')
    insert('docs/PROJECT_STATUS.md','## 当前结论','\n\n**018当前：** '+msg+'执行完成、待独立审计。见[中文主报告](../outputs/018_verifact_gap_attribution/report.md)与[交审材料](../outputs/018_verifact_gap_attribution/audit_handoff.md)。')
    p=c.ROOT/'docs/PROJECT_STATUS.md';data=p.read_bytes();p.write_bytes(data.replace('**017最新：**'.encode(),'**017历史结果：**'.encode(),1))
    insert('reviews/README.md','# 独立审计记录与后续状态','\n\n**018待独立审计：** 1251条离线机器分析与78例重点深读已完成，0新增API。原VeriFact高PA伴随更多false-S及更低MCC点估计；执行者优先建议研究Judge支持边界，但最大可实现净headroom未知。见[主报告](../outputs/018_verifact_gap_attribution/report.md)与[审计交接](../outputs/018_verifact_gap_attribution/audit_handoff.md)。当前没有018独立审计PASS结论。')
    insert('.gitattributes','outputs/** -text','\n\n# Preserve frozen 018 source and diagnosis bytes.\ntasks/018_verifact_gap_attribution/** -text')
    print('Updated only current navigation and018 byte-preservation attributes; historical task reports unchanged.')
