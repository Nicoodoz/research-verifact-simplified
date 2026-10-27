"""Chinese stage-one report; GPU measurements stay explicitly pending."""
import common103 as c
def pct(x):return '—' if x is None else f'{100*x:.2f}%'
def table(panel):
 s=['|配置|MCC|PA|正确/N|false-S/non-S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for m,t in panel['tables'].items():
  name='paper_r1' if m=='Original' else m.replace('__native','').replace('__label','')
  recall='/'.join(pct(t['per_class'][k]['recall']) for k in c.LABELS)
  s.append(f"|{name}|{t['mcc']:.4f}|{pct(t['percent_agreement'])}|{t['correct']}/{panel['common_N']}|{t['false_S']}/{t['true_non_S']}|{t['Macro_F1']:.4f}|{recall}|")
 return '\n'.join(s)
def main():
 a=c.read(c.OUT/'analysis.json');sensitivity=c.read(c.OUT/'label_format_sensitivity.json');cost=c.read(c.OUT/'api_cost_ledger.json');d=c.read(c.OUT/'recommendation.json');lengths=c.read(c.OUT/'length_summary.json');plan=c.read(c.OUT/'gpu_plan.json');records=c.lines(c.OUT/'predictions.jsonl');candidate=d['larger_candidate']
 s=['# 103：微调模型选型与小规模可训练性验证（第一阶段）','',f"**READY_FOR_GPU：API筛查与本地准备完成，推荐小训练比较Qwen3.5-9B和{candidate}。** GPU尚未购买、连接或执行，训练后优劣未检验，不宣布论文确认成功。",'',d['rationale'],'','## 已完成范围与工程更正','',
 '40训练/20选型/40后续确认沿原development/exploration/reserved_test；100人均有历史研究暴露。本轮仅在20选型患者上新增API，后续40人未新增评价。冻结自然160＋额外NS40/NA40，各模型同240条；直接模式48条三类各16，嵌套本地180条为自然120＋NS30/NA30。512训练S320/NS96/NA96，前256为160/48/48，来自全部40训练患者。', '',
 '所有配置用完整发布reference与原医生最终标签、原作者式简洁任务；不使用C48、PriorG、示例或教师思维链。API权重revision/精度与本地公开BF16不保证相同；paper_r1是作者历史参照。native统一thinking_budget4096、最终768、temperature0/top_p1/repetition_penalty1；3.8由官方映射low。', '',
 '首24条仅核usage/格式，不看正确率。初始预算取消可选重复以保留240；实际usage结算后，在仍未分析正确率时恢复原已冻结的24条/模型重复。重复不替代首次。', '',
 '直接模式原上限128遇到3.6-35B一条解释性回答截断；统一四模型同48条改为768，所有原回执保留。旧128诊断最终各42条，未补无必要剩余调用；正式直接模式各48条768。修正后无截断，3.6仍7条非规定JSON，其他三模型全有效，不将其补NA或当医学错误。[修正记录](../../tasks/103_lora_selection/label_capacity_amendment.md)。', '',
 '## 原生API自然面板','',f"共同有效{a['natural']['common_N']}/{a['natural']['frozen_N']}，患者{a['natural']['patients']}，GT分布{a['natural']['GT']}。",'',table(a['natural']),'','## 原生API少数类压力面板','',f"共同有效{a['pressure']['common_N']}/{a['pressure']['frozen_N']}，与自然面板分开。",'',table(a['pressure']),'','## 直接模式及同ID排名变化','',
 f"48条是类别分散诊断，不是自然比例。四模型直接模式共同有效{a['direct48']['common_N']}条；各自覆盖和完整48条已知正确下界如下，不能仅凭删掉7条后的排名选唯一底座。",'',
 '|模型|直接模式有效/48|已知正确/48|同有效子集MCC|','|---|---:|---:|---:|']
 for m in c.MODELS:
  cv=a['direct48']['coverage'][m+'__label'];t=a['direct48']['own_valid_metrics'][m+'__label'];s.append(f"|{m}|{cv['valid']}/48|{cv['known_correct']}/48|{t['mcc']:.4f}|")
 s+=['',f"下面只在两个模式、四模型全部有效的相同{a['mode_common_native']['common_N']}条上检查排名反转：",'','|模型|native MCC|label MCC|native正确|label正确|','|---|---:|---:|---:|---:|']
 for m in c.MODELS:
  n=a['mode_common_native']['tables'][m+'__native'];l=a['mode_common_label']['tables'][m+'__label'];s.append(f"|{m}|{n['mcc']:.4f}|{l['mcc']:.4f}|{n['correct']}|{l['correct']}|")
 s+=['',d['direct_mode_interpretation'],'','完整48条、仅规范化整条纯标签的评分后敏感性（不替换以上严格主表）：','',table(sensitivity['results']),'','[格式边界与GPU前判读冻结](../../tasks/103_lora_selection/format_sensitivity.md)。','','## 配对变化与患者不确定性','','自然集六个同ID比较，方向为候选减参照；区间为1000次患者cluster bootstrap。','', '|候选−参照|救回/误伤/净正确|ΔMCC [95%CI]|false-S新增/避免|','|---|---:|---|---:|']
 for p in a['natural']['paired'].values():
  v=p['paired']['metrics']['mcc'];s.append(f"|{p['candidate'].replace('__native','')}−{p['base'].replace('__native','')}|{p['rescue']}/{p['harm']}/{p['net']:+d}|{v['delta']:+.4f} [{v['ci95'][0]:+.4f},{v['ci95'][1]:+.4f}]|{p['false_S_added']}/{p['false_S_prevented']}|")
 s+=['',f'以下以推荐候选{candidate}为候选，列出自然集各GT类别救回/误伤及患者净变化：','','|参照|S救回/误伤|NS救回/误伤|NA救回/误伤|患者胜/负/平|','|---|---:|---:|---:|---:|']
 for base in c.MODELS:
  if base==candidate:continue
  rr=[r for r in records if r['panel']=='natural' and r['predictions'].get(base+'__native') in c.LABELS and r['predictions'].get(candidate+'__native') in c.LABELS];vals=[];patient={r['sid']:0 for r in rr}
  for lab in c.LABELS:
   rescued=[r for r in rr if r['GT']==lab and r['predictions'][base+'__native']!=lab and r['predictions'][candidate+'__native']==lab];harmed=[r for r in rr if r['GT']==lab and r['predictions'][base+'__native']==lab and r['predictions'][candidate+'__native']!=lab];vals.append(f'{len(rescued)}/{len(harmed)}')
   for r in rescued:patient[r['sid']]+=1
   for r in harmed:patient[r['sid']]-=1
  s.append('|'+base+'|'+'|'.join(vals)+f"|{sum(v>0 for v in patient.values())}/{sum(v<0 for v in patient.values())}/{sum(v==0 for v in patient.values())}|")
 s+=['','完整三类P/R/F1、混淆矩阵、false-S分母和S假发现率、human/LLM分层、逐例救回/伤害ID及患者净差均见analysis.json和predictions.jsonl。区间只反映固定已暴露患者面板，不覆盖历史选择、种子、服务漂移或新医院泛化。','','## 同请求重复','','|模型|重复N|标签翻转|首次正确|再次正确|','|---|---:|---:|---:|---:|']
 for m,r in a['repeats'].items():s.append(f"|{m}|{r['N']}|{r['label_flips']}|{r['first_correct']}|{r['second_correct']}|")
 s+=['','## API费用与实际推理开销','',f"全部{cost['attempts']}次尝试、{cost['HTTP200']}个HTTP200；按无缓存官方目录价保守计¥{cost['uncached_budget_used_cny']:.6f}/30，含旧容量诊断、统一修正和重复。按实际官方缓存字段计¥{cost['official_usage_cny']:.6f}；未知/失败预留¥{cost['unknown_or_failure_reserved_cny']:.6f}。不使用渠道折扣。GPU当前0次/0元。",'', '|模型|native每例输入/输出tokens|native平均秒|240条native原价费用|48条label原价费用|思考用满4096次数|','|---|---:|---:|---:|---:|---:|']
 for m,v in a['cost_by_model'].items():
  n=v['native'];l=v['label'];s.append(f"|{m}|{n['mean_input']:.1f}/{n['mean_output']:.1f}|{n['mean_seconds']:.2f}|¥{n['total_uncached_cny']:.4f}|¥{l['total_uncached_cny']:.4f}|{n['thought_at_cap']}|")
 s+=['','## GPU准备、预计成本与尚未测量的项目','',
 '推荐单PRO6000 Blackwell96GB、Ubuntu22.04/24.04、Python3.12/CUDA12.8开发镜像，CPU≥16核/RAM≥128GB/可用磁盘≥320GB；A80080GB后备使用9B＋3.8-27B分支，不能保证该MoE在相同r16/BF16条件下放入80GB；详见resource_advisory.md。新venv与旧vLLM隔离；完整依赖已成功解析并hash锁定，但还没有GPU导入、kernel或吞吐实测。实际安装成功后再保存installed_gpu.lock。', '',
 '按用户参考6.98元/小时，先为约5—8小时规划GPU费用34.90—55.84元，另计实际存储且合计不得超60。此为待验证资源规划范围，不是跑完512的承诺；真实9B生成长度、27B/MoE吞吐和编译下载耗时可能使512不适合。4步真实长度预跑后，先留两候选全部180×3评价与25%余量，再统一选512或256；仍不够则保存资源边界，不删对照硬训。', '',
 'GPU默认BF16普通LoRA r16/alpha32/lr1e-4、micro1/accum8、单轮、普通梯度检查点；冻结视觉及原始权重，不默认4bit或CPU卸载。只监督真实verdict，prompt/padding loss屏蔽。已通过真实官方tokenizer的35项mask/完整输入检查；MoE专家覆盖和实际权重更新在GPU预跑强制核查。', '', '|候选|native_base|label_base|lora_label|训练token/s、显存|','|---|---|---|---|---|']
 for m in plan['candidates']:s.append(f'|{m}|待GPU|待GPU|待GPU|待实测|')
 s+=['',f"训练40人全体3675条的真实输入约{lengths[candidate]['all_training']['sum']:,} tokens；512条约{lengths[candidate]['train512']['sum']:,} tokens，最长{lengths[candidate]['train512']['max']:,}。单轮全训练计算量约为512试训的{lengths[candidate]['all_training']['sum']/lengths[candidate]['train512']['sum']:.2f}倍（另加标签与加载）。GPU阶段将用实测token/s换算正式LoRA费用，并分别外推native_base、label_base、lora_label的确认评价成本；当前不能伪报实测费用。后续40人3573条若全覆盖，评价条数是180的19.85倍，长度分布差异仍未在本轮确认患者上测量。",'',
 '私有数据包已生成并核对SHA，未上传实例。[启动、恢复、预算与关机命令](../../tasks/103_lora_selection/GPU_RUNBOOK.md)。预跑丢弃适配器，正式从同revision重新开始；256仅保存过程检查点。保存/回传完成后只关本次实例，核对计费停止，再离线分析。', '',
 '## 阶段决定与边界','',d['next_step'],'',
 '本轮第一阶段停止在READY_FOR_GPU，等待用户提供实例连接；不购买GPU，不启动第二阶段、全量训练或下一任务。102及历史结论、原GT、默认系统保持不变。执行者自检不是独立审计。公开成果不含临床原文、完整回执、密钥或权重。完成必要提交并推送完整/精简两个仓库，提交号以发布回执为准。']
 (c.OUT/'report.md').write_text('\n'.join(s)+'\n',encoding='utf-8')
 print('report written')
if __name__=='__main__':main()
