"""Finalize task navigation and audit fingerprints after successful independent replay."""
import argparse,subprocess,json
from pathlib import Path
import common036 as c
def prepend(path,paragraph):
    raw=path.read_bytes();bom=raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig');newline='\r\n' if b'\r\n' in raw else '\n';lines=text.splitlines();text='\n'.join(lines[:1])+ '\n\n'+paragraph+'\n\n'+'\n'.join(lines[2:])+'\n'
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+text.replace('\n',newline).encode('utf-8'))
def main(verification):
    vpath=Path(verification).resolve();v=c.read(vpath);assert v['status']=='EXECUTOR_SELF_CHECK_PASS';assert vpath.is_relative_to(c.ROOT/'outputs/replays');out=c.OUT
    for name in ['report.md','paper_handoff.md','paper_tables.md','methods_and_settings.md','accounting_002/summary.json','artifact_packages.json']:assert (out/name).exists(),name
    c.put(out/'verification_001.json',dict(source=str(vpath.relative_to(c.ROOT)),source_sha256=c.sha(vpath),**v))
    metrics=c.read(out/'analysis_001/R0/metrics.json');u=metrics['all/U2'];zero=metrics['all/U0'];g=metrics['all/Gate_A'];cost=c.read(out/'accounting_002/summary.json')
    summary=f"036已执行reserved40全部3573条最终验证，2条核心无效，共同有效主分析{u['n']}条。U2较U0净正确{u['correct']-zero['correct']:+d}、false-S {u['false_S']-zero['false_S']:+d}；A Gate较U2净正确{g['correct']-u['correct']:+d}、false-S {g['false_S']-u['false_S']:+d}。标准M/V总体PA/MCC更高，但类别代价明显，λ2不是最强后处理；论文应定位边界/置信度/风险的实证研究。另有事前冻结4人444条重复。累计费用及未知预留{cost['total_used_or_reserved_cny']:.6f}/150元；执行者自检PASS，独立审计待进行。reserved已用于最终评价，不再用于开发；不自动037。按本轮用户授权，完成后直接推送，不等待独立审计。"
    c.write_text(out/'CURRENT_STATUS.md','# 036 当前状态\n\n'+summary+'\n\n[中文总报告](report.md) · [论文写作交接](paper_handoff.md) · [方法设置](methods_and_settings.md) · [交审](audit_handoff.md)\n')
    c.write_text(c.TASK/'CURRENT_STATUS.md','# 036 当前状态\n\n'+summary+'\n\n[结果入口](../../outputs/036_final_validation/CURRENT_STATUS.md)\n')
    for path,prefix in [(c.ROOT/'README.md',''),(c.ROOT/'AGENTS.md',''),(c.ROOT/'docs/PROJECT_STATUS.md','../')]:
        prepend(path,'**036当前：** '+summary+f' [中文总报告]({prefix}outputs/036_final_validation/report.md) · [论文写作交接]({prefix}outputs/036_final_validation/paper_handoff.md)。034/035中的“不启动reserved40”为历史任务边界，036由本轮用户另行授权，长期80元API政策不变。')
    prepend(c.ROOT/'docs/REPRODUCIBILITY.md','**036安全复查：** `pwsh -NoProfile -File scripts/run_research.ps1 tasks/036_final_validation/verify036.py --output outputs/replays/036_check_002`。新目录必须不存在；不新增API。若克隆后存在gzip交付包，先运行同启动器下的`tasks/036_final_validation/package036.py restore`。见[036任务入口](../tasks/036_final_validation/README.md)。')
    prepend(c.ROOT/'docs/RUN_ENVIRONMENT.md','**036执行记录：** 本轮已获用户另行授权，并以本页指定`research-verifact-029`及启动器完成reserved40。下方“不授权启动”是环境说明自身的权限边界，不撤销036明确授权；本轮未修改任何环境依赖。见[036结果](../outputs/036_final_validation/report.md)。')
    prepend(c.ROOT/'docs/API_POLICY.md','**036本轮特例：** 用户明确批准本任务累计150元（含所有API、失败、未知及在途预留），执行完即停止；不将长期默认80元上限改成150元。仍为BGE硅基流动、Judge阿里云。账本见[036费用记录](../outputs/036_final_validation/accounting_002/summary.json)。')
    prepend(c.ROOT/'reviews/README.md','**036待独立审计：** 执行者已完成标准对照、reserved40最终评价及自检。用户授权自检完成后直接推送，不代表审计PASS。见[交审材料](../outputs/036_final_validation/audit_handoff.md)。独立审计文件尚未生成。')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip()
    handoff=f'''# 036 独立审计交接

状态：执行者完成；独立审计待进行。用户明确授权完成后直接提交/推送，不等待审计。不要把本文件或自检称独立PASS。

## 审查起点

提交前基准HEAD `{head}`；本轮代码与产物指纹在`handoff_manifest.json`，最终提交由Git定位本文件所在commit。报告和写作交接优先阅读，其次`tasks/036_final_validation/protocol.md`、三套freeze、development指标及R0/R1原始回执。

## 必查事项

1. 036用户授权reserved40及150元特殊上限；最终配置与参数、重复4人名单先于任何收费请求和GT连接。033撤回准备未继承；无reserved训练。
2. development补022 T/G/M/V是否沿原035折和参数定义；四折患者隔离；U4/Joint核对；035 MCC_T勘误是否准确。
3. Gate是否逐字复用033全40模型和原始12维score，Q缺失是否回退U0；所有概率后处理是否共享一次评分，温度是否保持标签。
4. 原API-BGE C48、原024模型0731/Qwen、body、token上限不变；请求不含GT/BHC/作者；B与scoring分清。
5. 全40/3573冻结覆盖及缺失ID、complete-case与总N敏感性；R1四人444条不作新增患者；不能静默筛成功样本。
6. 002指标、1000患者paired bootstrap；false-S与R/H/W、Gate的恢复H/阻止W/丢R是否区分；全标准方法和作者/患者/类别是否完整。
7. 所有回执SHA绑定、费用未知/在途预留、无重复HTTP200、总额{cost['total_used_or_reserved_cny']:.6f}≤150；原始费用非账单。
8. 报告不预设模块成功、不声称理论最优、NLL≠临床安全，原VeriFact对比不作单组件因果推断。自检与独立审计分清。

## 已做自检

7项单元测试，其中完整3675条旧推理数值锚点与370候选Gate原实现一致；发送前21项检查。最终安全重放{v['checks_n']}项PASS，详见`verification_001.json`；含原回执、全部模型输出、002指标、主要bootstrap和错误转移恒等式。测试发现的common模块名冲突在reserved评价前修复，原/后指纹与失败说明在`evaluation_freeze_001/implementation_repair.json`。原历史源码未改。

费用导出的附加修正见`accounting_CURRENT.md`和`accounting_002/verification.json`：旧001金额完全正确，rerank token列因只看usage而漏掉meta字段；逐条复核4228份BGE回执补正，原001、费用与科研预测全部不变。Figure2在figures_002补入已评价的Vector scaling，以展示其NS召回代价；旧图及旧绘图源码保留。标签等价和444条跨轮同ID核对见`final_label_equivalence.csv`，MCC_T不纳入不变标签的泛化断言。

## 复查与禁止操作

使用`research-verifact-029`和项目启动器；安全入口见任务README。不要运行旧历史生成器；不要重新发送成功API、删除失败/未知记录、重新训练或用reserved调参。大文件仅gzip无损运输，本地原字节保留；恢复后hash一致，未改.gitignore。单元测试和安全复查0 API。

审计应独立形成`reviews/036_final_validation.md`，执行者未创建或代写独立审计结论。完成后停止，不自动实验。
'''
    c.write_text(out/'audit_handoff.md',handoff)
    paths=[p for folder in (c.TASK,out) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='handoff_manifest.json']
    c.put(out/'handoff_manifest.json',dict(created_utc=c.now(),base_HEAD=head,independent_audit='pending',files={str(p.relative_to(c.ROOT)):c.sha(p) for p in paths}))
    print(summary)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verification',required=True);main(p.parse_args().verification)
