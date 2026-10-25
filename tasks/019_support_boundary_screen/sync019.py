"""Update only mutable navigation; preserve frozen task protocol and history."""
from pathlib import Path
import common019 as c

MARK='019执行完成：第一阶段停止'

def sync():
    folder=c.OUT/'documentation_sync_001';folder.mkdir(exist_ok=False)
    note=('**019执行完成：第一阶段停止（2026-09-18，尚未独立审计）。** '
          '650条完整同期比较：B正确530；lambda1.5/2正确558/567，但false-S由21增至32/43，NS判对由22降至13/10。'
          '七个参数均未满足保护门槛，无选定lambda；601条第二阶段未启动，未用剩余10名开发和40名reserved test。'
          'PA有可调信号，不等于低代价修复或泛化成功。累计17.504163元/80元；全部真实回答来自硅基流动account_2，未切平台。')
    policy=('本会话最新API路由优先：先硅基流动启用key池，只有全池真实明确额度耗尽后才转阿里云单key；'
            '保留成功回答和未知费用，跨阶段/账号/平台累计80元。此前其他路由描述按历史版本理解。')
    targets={'README.md': 'outputs/019_support_boundary_screen/report.md',
             'AGENTS.md': 'outputs/019_support_boundary_screen/report.md',
             'docs/PROJECT_STATUS.md': '../outputs/019_support_boundary_screen/report.md',
             'docs/API_POLICY.md': '../outputs/019_support_boundary_screen/report.md'}
    records=[]
    for name,link in targets.items():
        path=c.ROOT/name;old=path.read_bytes();text=old.decode('utf-8-sig')
        c.require(MARK not in text,'019 navigation already added')
        backup=folder/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old)
        first,sep,rest=text.partition('\n')
        new=first+'\n\n'+note+' [019主报告]('+link+')。\n\n'+policy+'\n\n以下旧状态按形成时理解；当前019以本段及其成果入口为准。\n'+rest
        path.write_text(new,encoding='utf-8',newline='\n')
        records.append(dict(path=name,before_sha256=c.file_hash(backup),after_sha256=c.file_hash(path)))
    current=c.OUT/'CURRENT.md'
    (folder/'019_CURRENT_before.md').write_bytes(current.read_bytes())
    current.write_text('# 019当前结果\n\n'+note+'\n\n'+policy+
        '\n\n[唯一中文主报告](report.md) · [完整统计](statistics.md) · [交审入口](audit_handoff.md)\n\n'
        'selection_freeze.json中passed=false、selected_lambda=null。所有收费发送停止；不自动续跑、调整门槛或替换core。\n\n'
        '执行自查：223项已有测试、29项019测试；回执/费用复算、22文件断网重放及11例完整阅读完成。执行自查不是独立审计PASS。\n\n'
        '中断恢复、21条429、1次无回执和原成功回答均保留。原CURRENT版本见documentation_sync_001/019_CURRENT_before.md。未提交或推送GitHub。\n',encoding='utf-8')
    (c.TASK/'CURRENT.md').write_text('# 019当前入口\n\n'+note+
        '\n\n[主报告](../../outputs/019_support_boundary_screen/report.md) · [交审材料](../../outputs/019_support_boundary_screen/audit_handoff.md)\n\n'
        'README.md为执行前冻结协议，保持原字节；本文件仅更新当前状态。\n',encoding='utf-8')
    c.write_json(folder/'changes.json',dict(created_utc=c.now(),changes=records,
        allowed_navigation_only=True,frozen_protocol_unchanged=True,new_API_calls=0))
    print(c.canonical(records),flush=True)

if __name__=='__main__':
    sync()
