"""Finalize025 after offline self-checks; do not mark independent audit passed."""
import re,subprocess,sys
from datetime import datetime,timezone
import common025 as c
def current(path,text):
    raw=path.read_bytes();s=raw.decode('utf-8');nl='\r\n' if '\r\n' in s else '\n';pattern=r'\*\*025当前[^\r\n]*'
    if re.search(pattern,s):s=re.sub(pattern,lambda _:text,s,count=1)
    else:pos=s.index(nl)+len(nl);s=s[:pos]+nl+text+nl+s[pos:]
    path.write_bytes(s.encode('utf-8'))
def run():
    checks=[]
    for name in ('test025.py','test_numeric025.py','verify025.py'):
        p=subprocess.run([sys.executable,str(c.TASK/name)],cwd=c.ROOT,capture_output=True,text=True)
        checks.append(dict(script=name,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr));c.require(p.returncode==0,'Self-check failed: '+name)
    c.write(c.OUT/'verification_001/checks.json',dict(results=checks,new_API_calls=0))
    c.require(c.read(c.OUT/'verification_001/replay.json')['all_equal'],'Replay failed')
    # Add precision of the original matched-risk endpoint; no new operating point selection.
    path=c.OUT/'report.md';s=path.read_text(encoding='utf-8')
    s=s.replace('仅观察false-S下降会错误夸大evidence的价值。**','仅观察false-S下降会错误夸大evidence的价值。** 即便只看确定性global，SE多救回5条的患者区间也是[-2,+29]，并未排除无增量；补充区间见interpretation_001/operating_uncertainty.json。')
    path.write_text(s,encoding='utf-8',newline='\n')
    status='''# 025 当前状态：执行与自检完成，待独立审计

零API/零费用，019/020/024冻结数据，固定λ=2、Judge和证据未改，reserved40未使用。

- 当前E特征路线没有稳定增量，停止，不追加v2/v3。
- 024D的SE为R61/risk16，对global混合包络仅+0.22 R，患者区间跨0；对S增量区间也跨0。
- 第二Judge信号SD为R64/risk10，对global混合+15 R、区间[2.70,23.29]；10/10去掉单患者后仍正。可保留有限开发线索，但不能归功于E、不能称已验证正式方法。
- 025完整事前门槛无winner：SD其余主门槛通过，历史跨模型条件因019/020无D不可评估；Qwen未重复优势。这与“第二Judge有真实OOF信号”是两个层面的判断。
- 8项测试，138个外层fit患者/标准化/概率核验，32组全队列预测指标、LP全局包络与独立逐条LOO核验；15份核心机器结果离线重放一致。执行者自检不是独立审计PASS。
- 正式结果analysis_003；analysis_001/002及两项工程修复保持。未改模型/特征/阈值救结果。

[唯一主报告](report.md) · [审计交接](audit_handoff.md)。本轮停止，不自动启动后续或reserved test。
'''
    (c.OUT/'CURRENT_STATUS.md').write_text(status,encoding='utf-8',newline='\n')
    (c.TASK/'CURRENT_STATUS.md').write_text('''# 025 当前状态

执行及自检完成，待独立审计。证据E未证明稳定增量，停止当前实现；第二Judge风险信号仅保留有限开发线索，不是正式方法。见[报告](../../outputs/025_lambda_flip_risk_separability/report.md)及输出CURRENT_STATUS。

当前分析入口为analyze025_numeric.py；原analyze025.py及analyze025_fixed.py保留工程修复历史。安全离线：

```
python tasks/025_lambda_flip_risk_separability/verify025.py
python tasks/025_lambda_flip_risk_separability/analyze025_numeric.py --output outputs/replays/<new-directory>
```

执行分析和核查时网络连接被禁用；新目录重放，不覆盖正式analysis_003。025没有收费入口。
''',encoding='utf-8',newline='\n')
    (c.OUT/'README.md').write_text('''# 025 成果入口

唯一必读[中文主报告](report.md) · [当前状态](CURRENT_STATUS.md) · [审计交接](audit_handoff.md)。执行及自检完成，尚未独立审计。

- [事前协议](protocol_001.md)、[冻结输入与特征](preparation_001/source_manifest.json)。
- 正式结果analysis_003：[全队列指标](analysis_003/full_metrics.csv)、[操作点及区间](analysis_003/summary.json)、[完整global-λ曲线](analysis_003/global_lambda_curves.csv)、[OOF排序曲线](analysis_003/gate_curves.csv)、[OOF逐候选](analysis_003/candidate_oof.csv)、[训练隔离记录](analysis_003/fit_audit.json)。
- [主图](figures_002/024_D_risk_rescue.png)、[Qwen辅助图](figures_002/024_Q_risk_rescue.png)，同目录SVG可用于论文。
- [门槛可评估性说明](interpretation_001/gate_scope.json)、[补充确定性/混合区间](interpretation_001/operating_uncertainty.json)。
- [自检](verification_001/checks.json)、[离线重放](verification_001/replay.json)。analysis_001/002和figures_001是保留的工程中间版本，不是当前正式结果。

无API、无reserved40、不改变λ、不自动后续。
''',encoding='utf-8',newline='\n')
    audit='''# 025 独立审计交接

025执行和执行者自检完成，**未宣布独立审计PASS**。正式机器版本analysis_003，唯一主报告report.md。本轮停止。

## 研究判断及必要区分

E无稳定额外价值：024D SE R61/risk16，相对global确定性+5（CI[-2,29]）、混合包络+0.22（CI[-9.12,9.86]）；SE−S在同风险多5（CI跨0），SED−SD无正增量。停止当前E实现。

SD是额外正向线索：R64/risk10，相对完整global混合+15（CI[2.70,23.29]）；10/10去掉患者仍正；但Qwen不复现。**原完整门槛无winner**：SD历史复现项false源于019/020无跨模型D，不能评估，并非实测历史SD失败。gate_scope.json显式区分不可评价与反证；没有事后改原门槛，也不应以不可评价项否认已测得的OOF增量。只允许保留有限开发线索，不包装正式方法。

## 输入与范围

- preparation_001/source_manifest.json严格绑定019/020/024冻结输入、评分和预测。全部S评分合法，024使用879条S-only完整队列，与024 B缺一条无关。
- 019六人与020/024十人共16不同患者、1529不同claim，4166 score观察分组保留。没有reserved40病例读取，没有新API/费用，没有修改Judge/λ/证据。
- E特征只由冻结claim/reference和现存检索数值产生；禁用GT/author/患者ID作为特征。019缺3维rerank明细时恒0，不能把它的迁移当完整检索特征跨队列验证。
- 双模型probe根据用户本轮明确规则在025新建：peer.U2=S才保留主λ候选。D=46/5、Q=18/2与用户检查值独立一致；不是024已有审计方法或上界。

## 必审方法点

1. S/SE/SD/SED同一C=.1线性logistic，不搜索分类器/超参数。外层患者LOPO，内层训练患者LOPO只决定80%训练R阈值；所有标准化/系数/阈值排除测试患者。固定λ2只被gate否决，不重选λ。
2. 020 R1只能使用R0训练、排除同一个测试患者；R1不训练不选阈值。019→后10人的transfer绝不共享患者。fit_audit可逐项复核。
3. 完整global非负λ全部浮点切换直到全S；含0/2与历史锚点，不局限于旧7网格或[0,2]。deterministic阶梯和期望风险的随机混合上包络必须分别呈现，后者不是实现新λ或新随机方法。
4. 仅预先登记的嵌套阈值操作点用于继续门槛。OOF概率全曲线、raw score margin AUC仅描述；不得从曲线挑新winner。
5. R/H/W分别核算，risk=H+W、净正确=R−H；全队列指标调用002，不仅报告候选二分类。global基准用评价GT形成强事后参考，不能直接部署。
6. bootstrap为1000患者cluster、固定OOF输出条件区间，不含重训不确定性；不把同10患者的020/024当独立复制。不把廉价文本覆盖或系数解释当新医学gold。

## 两项工程修复（不是新方法版本）

- analysis_001完成数值计算后，decision.json因NumPy bool_不能序列化失败；原文件/原代码保持，serialization_repair_001登记Python bool转换。
- 自检识别布尔LOO权重在NumPy @运算中导致逻辑结果。frontier025_numeric仅把权重转float，模型/阈值/预测/主要指标/曲线/bootstrap未改；count_repair_001记录。analysis_002保持，正式analysis_003修正LOO及依赖门槛。13份不受影响内容逐字节一致。
- figures_001是视觉初稿（连线会让离散global看似可插值），figures_002改为明确阶梯和混合包络；数值不变，主报告只链接正式图。

## 自检与重放

- 8项单元测试通过，包括独立患者标签扰动不影响自己的OOF预测、内外层隔离、相同score精确浮点切换、完整λ覆盖、混合包络、单类训练退回、布尔权重计数。
- verify025：冻结来源/原执行代码/正式依赖hash；138个外层拟合的训练患者、标准化均值及概率；32组预测全队列002指标；R/H/W独立逐条计算；global混合包络由独立线性规划验证；所有LOO由逐条标量解码重算。
- verification_001/replay.json：15个核心输出在outputs/replays/025_self_replay_001重放逐字节一致；新目录不覆盖正式结果，网络connect被禁用。该replay目录沿既有gitignore排除，没有改.gitignore。
- 当前HEAD、未提交状态、全文件SHA见handoff.json；现行导航允许后续审计状态同步，正式协议/结果/源数据保持。

## 安全入口

```
python tasks/025_lambda_flip_risk_separability/verify025.py
python tasks/025_lambda_flip_risk_separability/analyze025_numeric.py --output outputs/replays/<new-directory>
```

分析和核查均离线，不需key。本任务不自动启动后续、重调λ或reserved test。
'''
    (c.OUT/'audit_handoff.md').write_text(audit,encoding='utf-8',newline='\n')
    line='**025当前（2026-09-19）：** 离线风险可分性分析完成，待独立审计。E未证明超出score/global λ的稳定增量，停止当前E路线；024D第二Judge信号有正向OOF增量，仅保留有限开发线索，历史D不可评估、Qwen未复现。固定λ=2、0新增API、未用reserved40，不自动后续。'
    for rel,prefix in [('README.md',''),('AGENTS.md',''),('docs/PROJECT_STATUS.md','../')]:current(c.ROOT/rel,line+f' [主报告]({prefix}outputs/025_lambda_flip_risk_separability/report.md) · [状态]({prefix}outputs/025_lambda_flip_risk_separability/CURRENT_STATUS.md)。')
    current(c.ROOT/'docs/REPRODUCIBILITY.md','**025当前离线入口：** `python tasks/025_lambda_flip_risk_separability/verify025.py`；重放`analyze025_numeric.py --output outputs/replays/<new-directory>`，网络禁用，不覆盖正式analysis_003。0API，固定λ不变。')
    with (c.TASK/'README.md').open('a',encoding='utf-8',newline='\n') as f:f.write('\n执行与自检完成，待审；[当前状态](CURRENT_STATUS.md) · [唯一主报告](../../outputs/025_lambda_flip_risk_separability/report.md)。当前分析入口analyze025_numeric.py，正式结果analysis_003。\n')
    paths=[p for d in (c.TASK,c.OUT) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    nav=[c.ROOT/p for p in ('README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md')]
    c.write(c.OUT/'handoff.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),independent_audit=False,new_API_calls=0,sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},navigation={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in nav}))
    print(c.canonical(dict(status='completed_pending_independent_audit',files=len(paths),new_API_calls=0)))
if __name__=='__main__':run()
