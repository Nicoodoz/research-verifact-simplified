"""Append current 087 navigation after title, preserving all existing bytes/EOL."""
from common087 import *

def main():
    q=read(OUT/'analysis.json');check=read(OUT/'selfcheck.json')
    assert check['status']=='PASS' and q['n']==110
    for rel in ('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/REPRODUCIBILITY.md'):
        p=ROOT/rel;data=p.read_bytes();assert b'**087' not in data
        prefix='../' if rel.startswith('docs/') else ''
        link=prefix+'outputs/087_f4_evidence_intervention/'
        if rel.endswith('API_POLICY.md'):
            entry=f'**087专项结项（2026-09-26）：** 四臂110条/22患者共440次HTTP200，0重试/未知；未优惠原价¥14.419416/20，未沿用086的30元或历史余额。没有新增检索/校准/理由API，后续默认20元不变。[账本]({link}cost_ledger.json) · [报告]({link}report.md)。'
        elif rel.endswith('REPRODUCIBILITY.md'):
            entry=f'**087只读复查入口（2026-09-26）：** 087已完成四臂同期评价与086零API归因追加更正。使用独立087 verifier及全新输出JSON，不运行旧086生成器覆盖历史。[交审与安全命令]({link}audit_handoff.md) · [086补正]({link}086_correction.md)。本入口不授权新调用，085A/R1/AWS仍暂停。'
        elif rel.endswith('RESEARCH_EXECUTION.md'):
            entry=f'**087更新（2026-09-26）：** B/F4/CL4/X4固定四臂完成；原生共同有效105条F4比X4净+4，属未校正多比较的单轮对应关系敏感性信号，不能全当正向教学。完整110条PriorG正确95/96/92/93；CL4省38.22%费用但比F4少4正确、多2错误支持，未证明等效。用户接受小幅风险取舍，仍全报类别代价。默认B不变，不自动088；086 fallback误归因只追加更正，不回写原主结果。[087报告]({link}report.md) · [086补正]({link}086_correction.md)。'
        else:
            entry=f'**087最新（2026-09-26）：** F4证据信息干预完成，22名development患者110条同期B/F4/CL4/X4＋Frozen PriorG正确95/96/92/93、MCC0.6588/0.6817/0.5920/0.6264、错误支持5/5/7/5。共同核心有效105条raw正确81/84/82/80，F4对X4有有限单轮对应关系敏感性信号，不证明具体推理技能；CL4输入少62.47%、费用少38.22%，未证明等效或可替代。440次HTTP200、原价¥14.419416/20，自检4227 PASS、独立审计未执行。086补正为有效评分1救回/3伤害＋fallback相关1救回，原主结果不变。默认B＋Frozen PriorG不变，085A/R1/AWS继续暂停；不使用reserved、不改.gitignore，不自动088，完成后按用户授权提交推送。[087报告]({link}report.md) · [086补正]({link}086_correction.md)。'
        pos=data.index(b'\n')+1;eol=b'\r\n' if data[:pos].endswith(b'\r\n') else b'\n'
        added=eol+entry.encode('utf-8')+eol
        p.write_bytes(data[:pos]+added+data[pos:])
    text(OUT/'README.md','''# 087结果入口

[中文主报告](report.md) · [完整性能/类别/配对表](performance_tables.md) · [成本及token/时长分布](cost_tables.md)

[机器分析](analysis.json) · [逐例原生解析/最终标签](predictions.jsonl) · [全比较归因台账](attribution_cases.jsonl) · [7例输出措辞抽查](case_review_materials.jsonl)

[事前冻结](freeze.json) · [覆盖与患者隔离](coverage.json) · [固定reference置换](reference_permutation.json) · [模板diff](template_changes.diff) · [预算](budget.json)

[086追加补正](086_correction.md) · [费用账本](cost_ledger.json) · [执行者自检](selfcheck.json) · [审计交接](audit_handoff.md)

440次HTTP200、¥14.419416/20，独立审计未执行。默认B不变，CL4不升级；085A/R1/AWS暂停，不自动下一任务。历史086工件未改。
''')
    print('Updated six current navigation files; all original bytes retained.')

if __name__=='__main__':main()
