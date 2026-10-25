"""Publish READY only after offline tests and all preparation artifacts exist."""
import json,subprocess
import common096 as c
from prepare096 import strata_sample
def main():
    assert c.read(c.OUT/'offline_selfcheck.json')['status']=='PASS'
    assert not list((c.PRIVATE/'attempts').glob('*/*/request.json'))
    ledger=c.lines(c.OUT/'candidate_ledger.jsonl');main600,_=strata_sample([r for r in ledger if r['eligible']],600,'096/main/v1/');variants=c.read(c.OUT/'panel_variants.json')
    assert [r['id'] for r in main600]==variants['main600_stress100']['main_ids'];c.putl(c.OUT/'main600_panel.jsonl',main600)
    wanted=set(variants['main600_stress100']['stress_ids']);c.putl(c.OUT/'stress100_panel.jsonl',[r for r in c.lines(c.OUT/'stress_panel.jsonl') if r['id'] in wanted])
    c.write(c.OUT/'optional_bridge_feasibility.md','''# 可选Original-style@V4：尚未接入，不冒充已运行

本轮只做离线可行性盘点，120条主面板候选ID已冻结。未向原作者服务、R1或阿里云发送请求。

已读本地原作者快照`docs/sources/007_context_retrieval/packages/llm_judge/src/llm_judge/judge.py`：83–84行要求reasoning模型提供辅助LLM；385行起的reasoning路径先生成reasoning_content/content，再调用aux_llm做结构化提取，并有自己的格式失败重试规则。这与085直接解析原生JSON、成功不重发不同。010的source_notes与发布模型元数据记录辅助模型为量化Llama-3.1-8B。

010/078已运行的桥接是“原作者reference＋本研究Judge”，不是原Judge流程换V4。本地`scripts/replay_completed_research.py`也仅重放019–021保存结果，并非任意model profile的原作者在线Judge适配器；发布结果评价器按已有model/rater配置取数，不能凭换服务名产生新的Original-style结果。

因此当前不生成Original-style请求，也不部署Qdrant/BGE或另租辅助GPU。后续只有原提示、辅助提取接口、模型profile与成功/无效契约能完整且轻量冻结，并在用户确认API预算内，才可启动这项可选工作。替换辅助模型或跳过提取步骤均须明确记为管线差异，不称精确重现。不能据这里未接入就说原流程无法适配。

48条V4-B同期桥接另有可运行脚本与私有冻结请求，默认关闭；其目标仅是批次诊断，不冒充Original-style，不替换095原缓存。
''')
    sample=c.read(c.OUT/'sampling_summary.json');token=c.read(c.OUT/'tokenizer_manifest.json');recipe=c.read(c.OUT/'calibration_recipe.json');cost=c.read(c.OUT/'cost_plan.json')
    scenarios='\n'.join(f"|{r['name']}|{r['clinical']}＋1虚构|{r['historical_B_serial_hours']:.2f}|{r['ideal_two_concurrent_hours']:.2f}|{r['planning_two_concurrent_hours_1_5_margin']:.2f}|" for r in cost['R1_scenarios'])
    report=f'''# 096 零API准备报告：READY_FOR_R1

**准备已完成，等待用户服务就绪消息。** 本轮未访问任何R1端点，未发送收费API；没有新R1输出、适配参数或评价成绩。旧096构造修复按用户指示停止且不恢复，默认仍V4-B＋Frozen PriorG。

起始HEAD：`28daf95e9b12270d8089246176023c66c4cf298e`。本轮指令来源为docs/01_codex_execution_prompt.md，本次明确只准备；完整研究结项及commit/push不在尚未执行的推理之前冒充完成。用户其他未提交改动保留。

## 校准与配方

精确复用原051/052的143个T-S训练ID、16患者，S/NS/NA为48/47/48；逐条保留原C48及原051分数，不从095另挑更好回执。参考先验由这16患者1378条母体复核为1108/100/170，不从新评价估计。

沿052平均NLL＋0.01 theta²、[-6,6]、log(max(score/100,1e-6))，053解码tie-break为NS/NA/S。CPU重现theta={recipe['reproduced_model']['theta'][0]:.16f}，旧冻结theta={recipe['old_theta']:.16f}；数值差约6.02e-7来自求解精度，143训练与8997历史共同core的最终标签均一致。另用独立标量优化器核同一目标，未更换配方或选工作点。旧字面参数继续保留。

未来R1如部分校准core无效，拟合脚本固定共同交集，并用相同ID同步重拟合V4，交集校准比例重算，参考比例不变。原V4 Frozen仍单列。新参数在评价GT连接前冻结；raw成绩不好不自动取消适配。分数不称真实token概率或已校准概率。

## 冻结母体与抽样

|范围|N|患者|S/NS/NA|human/LLM|
|---|---:|---:|---|---|
|原095目标母体|9065|100|7035/693/1337|5624/3441|
|本轮合格母体|7507|84|5777/582/1148|4642/2865|
|主面板|800|84|616/62/122|495/305|
|压力面板|200|69|0/100/100|180/20|

排除1378条校准患者命题和085旧180个具体ID。主面板按作者×GT比例最大余数配额、层内哈希抽取，无患者配额、无历史正确性/分数筛选；保存N_h/n_h纳入权重。主面板包括8条095核心无效回答，不只抽8997子集。压力与主面板互斥，不能拼成自然总体PA。reference来源与作者分布见[sampling_summary.json](sampling_summary.json)。全体已暴露，不称独立外部测试。

1143个R1临床请求已冻结：143校准＋800主＋200压力。另1个虚构预检；3个校准技术预检的成功回答直接计入143，原成功不重发。600/100及仅主面板备选ID也已预登记，各自权重独立保存。实际服务预检后，以费用/截止时间一次选择规模：优先800＋200，其次保800主面板，再600＋100、600-only；不根据早期胜负变更。

## 输入与服务门槛

沿085正式B语义模板与评分接口，temperature0、top_p1、8192，不携带V4专有thinking字段。推理payload只含proposition/reference，不含GT、原作者或V4判断。临床请求及标签分别存忽略私有目录，不向GPU机复制数据库或标签表。

本地旧085 Valdemardi tokenizer离线计算1144个请求，最大输入{token['max_input']}，加8192最多{token['max_total_context']}<20000；未下载权重。该结果不是当前远端身份或chat template的认证。HF已知revision不等于ModelScope revision；运行前需要实际权重来源/revision、config/tokenizer哈希、vLLM/torch/CUDA/driver/GPU和完整服务参数的私有manifest。

`control096.py`默认dry-run。只有用户服务就绪确认、明确R1执行授权、实际租金起点/单价/上限、截止时间、manifest均通过后，才允许包括`/models`在内的访问。当前授权标记为false，金额/时点未填。空reasoning不能单独证明未推理；真实预检才观察原生字段、think标记、usage/finish和实际输入token，普遍截断/循环/格式破坏先技术停止，不当医学负结果。

## 费用估算，不是租金账单

095额度不继承，30元GPU和10元按token API仅是用户提示词建议，尚未确认。没有查询余额或购买资源，当前新增按token调用0、费用0；真实GPU账单未知。

历史085无示例B平均单请求{cost['historical_B_mean_seconds']:.2f}秒，下面仅作准备情景，不能假定新GPU或真实推理长度相同；双并发线性加速并未实测。

|预登记方案|请求数|历史串行小时|理想双并发小时|双并发×1.5规划小时|
|---|---:|---:|---:|---:|
{scenarios}

实际费用公式为“整实例单价×从用户计费起点到平台关机的墙钟”，加载、等待和准备也计入。预检以后用实际批次墙钟更新预测；发送前预留900秒在途与关机余量，达到预算/截止条件停止新发送。不能用请求耗时相加当租金，不能声称停止Python或vLLM已停止AutoDL计费。

可选48条V4桥接按历史usage忙时无缓存约1.16–1.18元，首轮每请求最大预留合计约5.46元；不含未知重试时仍必须共享实际确认的API硬上限。价格要在后续真实发送前重新核实，当前不发。Original-style@V4未接入，具体辅助结构化模型/重放契约缺口见[可选桥接说明](optional_bridge_feasibility.md)。

## 校验与下一步

9项离线功能测试通过，7组执行者自检通过：训练来源/配方、抽样重放、1143请求GT隔离和哈希、token预算、禁止未授权端点/计费、历史/隐私边界。属于自检，不冒充独立审计，也未测试真实端点。测试中的模拟HTTP200成功不重发、未知在途不直接重发、收费桥接回执已落盘而数据库更新中断后的去重恢复均已通过；远端运行仍须预检。

恢复命令、实际运行配置模板与远端manifest脚本见[README](../../tasks/096_r1_native_priorg/README.md)。服务就绪后按“技术预检→一次规模冻结→143校准→CPU适配冻结→主/压力推理→R1_INFERENCE_DONE”执行；推理回执完整落盘后立即通知用户平台关机，余下CPU分析不依赖GPU。

当前等待GPU型号/数量、整实例时价、计费起点、两项明确预算、最迟发送时间及本地manifest路径。不会轮询R1，不自动发送或租用资源。
'''
    c.write(c.OUT/'report_preparation.md',report);c.write(c.OUT/'CURRENT_STATUS.md','# READY_FOR_R1\n\n096 R1原生比较与同配方PriorG适配已完成零API准备，等待用户服务就绪。0端点探测、0收费请求；默认不变。\n\n[准备报告](report_preparation.md) · [恢复入口](../../tasks/096_r1_native_priorg/README.md) · [执行者自检](offline_selfcheck.json)。')
    code={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in c.TASK.glob('*.py')}
    artifacts={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in c.OUT.iterdir() if p.is_file() and p.name not in ['offline_freeze.json','READY_FOR_R1.json']}
    c.put(c.OUT/'offline_freeze.json',dict(status='OFFLINE_PREPARATION_FROZEN',code_sha256=code,artifact_sha256=artifacts,private_jobs_sha256=c.sha(c.PRIVATE/'jobs.jsonl'),network_calls=0,waiting_for_service_ready=True))
    c.put(c.OUT/'READY_FOR_R1.json',dict(status='READY_FOR_R1',created_utc=c.now(),new_R1_requests=0,endpoint_probes=0,new_metered_API_requests=0,calibration_N=143,main_N=800,stress_N=200,clinical_jobs=1143,fictional_jobs=1,runtime_budgets_confirmed=False,remote_identity_verified=False,independent_audit_performed=False,offline_freeze_sha256=c.sha(c.OUT/'offline_freeze.json'),user_service_ready_message_required=True))
    print('READY_FOR_R1')
if __name__=='__main__':main()
