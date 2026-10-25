"""Update mutable navigation after a headroom stop; preserve old reports and reviews."""
import common017 as c

SLUG='017_verification_supervised_evidence_utility'

def edit(name,transform):
    path=c.ROOT/name;raw=path.read_bytes();text=raw.decode('utf-8');newline='\r\n' if '\r\n' in text else '\n'
    # Only text targeted by the transformation changes; original newline convention stays.
    new=transform(text.replace('\r\n','\n')).replace('\n',newline)
    c.require(new!=text,'Navigation edit did not apply: '+name)
    path.write_bytes(new.encode('utf-8'))

def run():
    gate=c.read(c.OUT/'analysis_001/gate.json');summary=c.read(c.OUT/'analysis_001/summary.json')
    c.require(not gate['passed'] and (c.OUT/'report.md').exists(),'Headroom stop report required')
    conclusion=f"017完成12名已暴露患者192条GT盲证据干预：{gate['stable_errors']}条稳定错误中稳定救回{gate['stable_rescued']}条，{gate['stable_correct']}条稳定正确中破坏{gate['stable_harmed']}条；未达事前headroom门槛，停止，不训练selector、不使用剩余10人确认。"
    link=f'[017中文主报告](outputs/{SLUG}/report.md)'
    def root(t):
        c.require('## 24. 017' not in t,'Navigation already synchronized')
        t=t.replace('# Research-VeriFact\n\n',f'# Research-VeriFact\n\n**当前017：** {conclusion}尚未独立审计；唯一必读{link}，审计材料已准备。\n\n',1)
        t=t.replace('当前唯一必读[016中文主报告]','016正式[中文主报告]')
        t=t.replace('当前阶段：001–016执行与相应独立审计均已完成。',f'当前阶段：{conclusion}017待独立审计。001–016执行与相应独立审计均已完成。')
        row=f'| `{SLUG}` | 第一阶段未达门槛，停止；待独立审计 | [任务](tasks/{SLUG}/README.md) · [中文主报告](outputs/{SLUG}/report.md) · [交审材料](outputs/{SLUG}/audit_handoff.md) |'
        lines=t.splitlines();i=next(i for i,x in enumerate(lines) if x.startswith('| `016_disagreement_triggered_review_validation`'));lines.insert(i+1,row)
        t='\n'.join(lines)+'\n'
        return t+f'\n## 24. 017医生verdict监督的证据utility（第一阶段停止，待审）\n\n{conclusion}有限单段替换结果不是全局selection不可能性的证明。1572份有效回答，累计费用估算与未知预留¥{summary["used_or_reserved_cny"]:.8f}/¥80；原始回执、失败与历史001–016保持。见{link}。\n'
    edit('README.md',root)
    edit('AGENTS.md',lambda t:t.replace('## 当前研究状态\n\n',f'## 当前研究状态\n\n{conclusion}017尚未独立审计，当前主报告见{link}；不能将自查写成独立PASS，也不自动训练或扩大该版本。\n\n',1).replace('当前唯一必读[016主报告]','016[主报告]'))
    rel=f'../outputs/{SLUG}'
    edit('docs/PROJECT_STATUS.md',lambda t:t.replace('## 当前结论\n\n',f'## 当前结论\n\n**017最新：** {conclusion}尚未独立审计；[唯一中文主报告]({rel}/report.md)与[交审入口]({rel}/audit_handoff.md)。\n\n',1).replace('| 016 | 新6人601条，review452，低于Qwen457，仅比普通repeat451多1；未达到原门槛，停止当前方向，不确认剩余患者 |',
        '| 016 | 新6人601条，review452，低于Qwen457，仅比普通repeat451多1；未达到原门槛，停止当前方向，不确认剩余患者 |\n| 017 | GT盲单段替换headroom门槛未通过；仅第一阶段执行，未训练utility selector，待独立审计 |'))
    def reviews(t):
        t=t.replace('# 独立审计记录与后续状态\n\n',f'# 独立审计记录与后续状态\n\n**017待审：** {conclusion}执行者自查和交审材料已经准备，尚无独立结论。见[主报告]({rel}/report.md)与[审计交接]({rel}/audit_handoff.md)。\n\n',1)
        lines=t.splitlines();i=next(i for i,x in enumerate(lines) if x.startswith('| [016：'))
        lines.insert(i+1,f'| [017：verdict监督证据utility]({rel}/audit_handoff.md) | 待独立审计；执行者自查不等于PASS | headroom未达门槛，停止；未训练、未新患者确认 |')
        return '\n'.join(lines)+'\n'
    edit('reviews/README.md',reviews)
    c.require(summary['providers']=={'siliconflow':1572},'Review provider narrative for actual transition')
    edit('docs/API_POLICY.md',lambda t:t.replace('当前最近的016硅基流动调用仍由account_2完成；尚未确认全号池耗尽，也没有查询实时余额。因此目前不宣称“额度已经用完”，不发送虚假的耗尽通知。',
        '当前最近的017全部1572份有效回答仍由硅基流动account_2完成；未出现全号池明确耗尽记录，也没有查询实时余额，因此不宣称“额度已经用完”。017任务执行器已登记号池耗尽后的持久阿里云路由，但本次未触发或实测切换。')
        .replace('本次文档同步不发送API请求、不查询余额，也不修改冻结研究代码或历史回执。',
        '本页仅记录现行规则；017已按独立80元任务登记执行真实调用，详情见其主报告。文档同步本身不发送请求、不查询余额，不修改历史001–016研究代码或回执。'))
    print(c.canonical(dict(updated=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','reviews/README.md','docs/API_POLICY.md'],historical_reports_unchanged=True)))

if __name__=='__main__':run()
