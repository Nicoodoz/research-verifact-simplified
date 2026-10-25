"""Append current navigation; retain prior bytes and seal final execution status."""
import common031 as c

def run():
    out=c.OUT/'closeout_001';c.require(not out.exists(),'Closeout exists');out.mkdir()
    for p in [c.ROOT/'README.md',c.ROOT/'AGENTS.md',c.ROOT/'docs/PROJECT_STATUS.md',c.ROOT/'docs/REPRODUCIBILITY.md',c.TASK/'README.md',c.OUT/'README.md',c.OUT/'execution_status.json']:
        dest=out/'prior_documents'/p.relative_to(c.ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    summary='**031当前（2026-09-20）：** 固定信息组合的训练扩充/患者隔离确认完成执行及自检，待独立审计。原16人扩至28人，另12人1148条完整确认；扩充后A/B正确数不变，C/D各+1。主要同风险混合差C−A为−3.50R、D−B为−5.14R，未确认新增核查信息的实质增量，停止当前版本；A仅保留简单参照。费用及未知预留37.70924338/80元，不使用reserved40、不自动032、不commit/push。031由用户另行授权，不回写030边界；长期API政策和主环境未改。'
    for rel in ('README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'):
        p=c.ROOT/rel;data=p.read_bytes();c.require(b'**031' not in data,'031 navigation already present');nl=b'\r\n' if b'\r\n' in data else b'\n';prefix='../' if rel.startswith('docs/') else '';links=f' [主报告]({prefix}outputs/031_training_expansion_confirmation/report.md) · [交审与离线复查]({prefix}outputs/031_training_expansion_confirmation/audit_handoff.md)。';pos=data.index(b'\n')+1;p.write_bytes(data[:pos]+nl+(summary+links).encode('utf-8')+nl+data[pos:])
    c.write_text(c.TASK/'README.md','''# 031 固定信息组合训练扩充与患者隔离确认

执行、评价、中文报告和执行者自检完成，待独立审计。

- [唯一主报告](../../outputs/031_training_expansion_confirmation/report.md)
- [当前状态](../../outputs/031_training_expansion_confirmation/CURRENT_STATUS.md)
- [冻结协议](../../outputs/031_training_expansion_confirmation/protocol_001.md)
- [交审与安全离线复查](../../outputs/031_training_expansion_confirmation/audit_handoff.md)

固定029 A/B/C/D Logistic、训练内80%阈值及λ2；原16人、新增12扩充/12确认；API-BGE C48、阿里云各角色原配置。费用及未知预留37.70924338/80元。没有确认明显扩充或新增核查信息收益，停止本版本。

日常只读复查（新目录、禁网、0 API、0拟合）：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/031_training_expansion_confirmation/offline_verify031.py --output verification_audit_001
```

必须通过独立环境的conda run取得Windows原生依赖路径。主环境不改。reliable_continue031.py是本次恢复的历史入口，使用任务账号授权及IO修订；任务已完成，不要以收费runner代替离线复查。旧resume/continue/workflow及失败日志均保留，不重复启动。

科学冻结见analysis_contract_001/execution_freeze_001；未改prompt、特征、λ、Logistic或阈值目标。不commit/push、reserved40或自动032。
''')
    c.write_text(c.OUT/'README.md','''# 031 成果入口

**执行及执行者自检完成，待独立审计。** 以[中文主报告](report.md)和[CURRENT_STATUS](CURRENT_STATUS.md)为准：没有确认扩大训练或repeat/trace的实质增量，停止当前版本，不自动后续。

- [冻结协议](protocol_001.md)、[患者划分](planning_001/split.json)、[输入配置](freeze_001/manifest.json)
- [八模型及确认预测冻结](inference_001/manifest.json)、[完整评价](analysis_001/manifest.json)
- [角色/异常/时段](execution_diagnostics_001/summary.json)、[费用账本](costs_001/costs.json)
- [图表](figures_002/risk_rescue.png)、[执行者自检](verification_001/checks.json)
- [audit handoff及离线入口](audit_handoff.md)、[最终指纹](handoff_001/manifest.json)

attempts保留全部原生请求和回执；失败、粗预算、环境及IO修订、初次绘图和运行中状态均保留。历史快照中的running/pending只代表形成时状态，当前以本页和closeout_001为准。
''')
    cost=c.read(c.OUT/'costs_001/costs.json')['total_used_or_reserved_cny'];checks=c.read(c.OUT/'verification_001/checks.json')
    c.put(c.OUT/'execution_status.json',dict(state='completed',stage='report_selfcheck_handoff',pending=0,inflight=0,used_cny=cost,inflight_reserved_cny=0,scientific_conclusion='No material training expansion or added repeat/trace benefit confirmed; stop current version',independent_audit='pending',updated_utc=c.now()))
    c.put(out/'completion.json',dict(created_utc=c.now(),all_8_methods_complete=True,confirmation_n=1148,confirmation_valid_n=1148,report=c.sha(c.OUT/'report.md'),executor_checks=checks['passed'],independent_audit=False,API_cost_cny=cost,no_reserved_or_next_task=True,no_commit_or_push=True))
    print('Current navigation and closeout saved; previous documents retained')

if __name__=='__main__':run()
