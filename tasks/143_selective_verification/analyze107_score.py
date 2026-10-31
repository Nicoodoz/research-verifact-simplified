import json,math,sys
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[2];O=R/"outputs/143_selective_verification"
assert (R/"tasks/143_selective_verification/NATIVE_SCORE107_PROTOCOL.md").is_file()
sys.path.insert(0,str(R/"tasks/120_full_pool_sft"))
from final_compare120 import metrics,LABELS
def rows(p):return [json.loads(x) for x in (R/p).read_text(encoding="utf-8").splitlines() if x.strip()]
cfg=json.loads((R/".local_models/113_label_path/config.json").read_text(encoding="utf-8"))
assert cfg["checkpoint"]=="107_label_only" and cfg["calibration"] is False
assert cfg["adapter_sha256"]=="096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8"
assert cfg["branch_ids"]=={"S":33490,"Not":2536} and cfg["first_value_index"]==4
keys={r["id"]:r for r in rows(".local_models/113_label_path/keys.jsonl")}
base={r["id"]:r for r in rows(".local_models/113_label_path/baseline107.jsonl")}
files=list((R/".local_models/113_label_path/evidence/results/scores").glob("*.json"))
scores=[json.loads(p.read_text(encoding="utf-8")) for p in files]
ss={r["id"]:r for r in scores};pilot=set(cfg["pilot_ids"])
assert len(ss)==len(scores)==180 and set(ss)==pilot
confidence={};branch_mass={}
for i,r in ss.items():
 assert i in keys and i in base
 b=base[i];assert b["valid"] is True and b["verdict"] in LABELS
 assert b["checkpoint_adapter_sha256"]==r["adapter_sha256"]==cfg["adapter_sha256"]
 assert r["prompt_token_sha256"]==b["prompt_token_sha256"] and bool(r["prompt_token_sha256"])
 assert r["input_tokens"]==b["input_tokens"]
 assert all(str(b[k])==str(keys[i][k]) for k in ("sid","GT","author"))
 f=r["first_branch"];assert set(f)=={"S","Not"}
 a,z=f["S"],f["Not"];assert type(a) in (float,int) and type(z) in (float,int)
 assert math.isfinite(a) and math.isfinite(z) and 0<=a<=1 and 0<=z<=1 and 0<a+z<=1+1e-6
 confidence[i]=a/(a+z);branch_mass[i]=a+z
panels={"natural":[i for i in sorted(pilot) if keys[i]["pilot_panel"]=="natural"],"pressure":[i for i in sorted(pilot) if keys[i]["pilot_panel"]=="pressure"],"enriched_all180":sorted(pilot)}
assert len(panels["natural"])==120 and len(panels["pressure"])==60
result={"status":"FIXED_GRID_COMPLETE_NO_THRESHOLD_SELECTED","protocol":"../../tasks/143_selective_verification/NATIVE_SCORE107_PROTOCOL.md","source_config":".local_models/113_label_path/config.json","identity_checks":{"N":180,"unique_IDs":180,"source_adapter_matches":True,"prompt_SHA_matches":True,"input_lengths_match":True,"GT_sid_author_match":True,"native_first_branch_fields_verified":True},"score_definition":"first_branch.S / (first_branch.S + first_branch.Not); raw full-vocabulary branch scores at same prefix, not calibrated","original_greedy_retained":True,"fractions_percent":[0,5,10,20,30],"rounding":"floor(original_predicted_S_N * percent / 100)","selection_uses_GT":False,"panels":{},"no_GPU_API_training":True,"no_human_outcome_imputed":True,"no_conformal_guarantee":True,"no_best_threshold_selected":True}
for name,ids in panels.items():
 sids=[i for i in ids if base[i]["verdict"]=="Supported"];ordered=sorted(sids,key=lambda i:(confidence[i],i));M=len(ordered)
 nonS=sum(keys[i]["GT"]!="Supported" for i in ids);K=sum(keys[i]["GT"]!="Supported" for i in sids)
 data={"N":len(ids),"patients":len({str(keys[i]["sid"]) for i in ids}),"GT":dict(Counter(keys[i]["GT"] for i in ids)),"original_predicted_S_N":M,"original_false_S_N":K,"original_nonS_N":nonS,"diagnostic_only":name=="enriched_all180","points":[]}
 for pct in (0,5,10,20,30):
  k=M*pct//100;review=ordered[:k];reviewset=set(review);auto=[i for i in ids if i not in reviewset]
  pred={i:base[i]["verdict"] for i in auto};m=metrics([keys[i] for i in auto],pred)
  fs=sum(keys[i]["GT"]!="Supported" and base[i]["verdict"]=="Supported" for i in auto)
  tps=sum(keys[i]["GT"]=="Supported" for i in review);captured=K-fs;remaining_S=M-k
  random_captured=k*K/M if M else 0.;random_trueS=k*(M-K)/M if M else 0.
  point={"requested_percent_of_original_S":pct,"referred_N":k,"actual_fraction_of_original_S":k/M if M else 0.,"referred_IDs":review,"automatic_N":len(auto),"automatic_coverage":len(auto)/len(ids),"automatic_nonS_N":sum(keys[i]["GT"]!="Supported" for i in auto),"residual_false_S_N":fs,"original_nonS_denominator":nonS,"residual_false_S_over_original_nonS":fs/nonS if nonS else None,"automatic_predicted_S_N":remaining_S,"automatic_S_false_discovery_rate":fs/remaining_S if remaining_S else None,"automatic_MCC":m["mcc"],"automatic_PA":m["percent_agreement"],"automatic_correct_N":m["correct"],"automatic_confusion_matrix":m["confusion_matrix"],"referred_true_S_N":tps,"referred_GT":dict(Counter(keys[i]["GT"] for i in review)),"captured_false_S_N":captured,"random_same_size_hypergeometric_expectation":{"referred_false_S_N":random_captured,"residual_false_S_N":K-random_captured,"residual_false_S_over_original_nonS":(K-random_captured)/nonS if nonS else None,"referred_true_S_N":random_trueS},"empirical_score_boundary":{"max_referred":confidence[review[-1]] if review else None,"min_retained_S":confidence[ordered[k]] if k<M else None}}
  assert k==len(review)==len(reviewset) and fs+captured==K and captured+tps==k
  data["points"].append(point)
 result["panels"][name]=data
result["inference_cost"]={"cache_reuse_new_GPU_calls":0,"cache_reuse_new_API_calls":0,
 "historical_scoring_N":len(ss),"historical_input_tokens_total":sum(r["input_tokens"] for r in ss.values()),
 "historical_input_tokens_mean":sum(r["input_tokens"] for r in ss.values())/len(ss),
 "historical_three_path_scoring_seconds_sum":sum(r["seconds"] for r in ss.values()),
 "historical_pilot_elapsed_seconds":json.loads((R/".local_models/113_label_path/evidence/results/pilot_complete.json").read_text(encoding="utf-8"))["seconds"],
 "timing_scope":"Historical113 scores all three complete label paths; not the marginal cost of capturing two branch logits during native generation. Overall rental/transfer money not recorded here."}
result["limitations"]=["Historical180 development cohort, not a fresh holdout;pressure cohort is enriched and not exchangeable with deployment traffic.","Accepted-subset MCC/PA are conditional on retained cases;they are not full-cohort three-class improvements.","Only original107 Supported labels may be referred;all automatic labels remain unchanged.","107 branch confidence is not calibrated and does not represent120/136 models or prompts.","Hypergeometric figures are expectations for uniform random referral, not simulated outcomes or an oracle human result."]
(O/"native_score107.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
lines=["# 107原生分支分数：固定比例送审历史粗筛","","固定规则见[协议](../../tasks/143_selective_verification/NATIVE_SCORE107_PROTOCOL.md)；全部180条的ID、原greedy标签、权重及prompt指纹核对通过。下表每个比例均保留，不选择最佳点。MCC/PA只评价仍自动处理的子集，不能当作原全量分类提升。",""]
for name,panel in result["panels"].items():
 title={"natural":"自然120","pressure":"压力60","enriched_all180":"全180：仅富集诊断"}[name]
 lines+=["## "+title,"",f'原判S={panel["original_predicted_S_N"]}；false-S={panel["original_false_S_N"]}/{panel["original_nonS_N"]}原non-S。',"","|送审原S比例|实际送审N|自动覆盖|残留FS/原non-S|自动S假发现率|自动MCC|自动PA|送审真实S|随机期望残留FS|随机期望送审真实S|","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
 for q in panel["points"]:
  fdr="—" if q["automatic_S_false_discovery_rate"] is None else f'{q["automatic_S_false_discovery_rate"]:.2%}'
  lines.append(f'|{q["requested_percent_of_original_S"]}%|{q["referred_N"]}|{q["automatic_coverage"]:.2%}|{q["residual_false_S_N"]}/{q["original_nonS_denominator"]}|{fdr}|{q["automatic_MCC"]:.4f}|{q["automatic_PA"]:.2%}|{q["referred_true_S_N"]}|{q["random_same_size_hypergeometric_expectation"]["residual_false_S_N"]:.2f}|{q["random_same_size_hypergeometric_expectation"]["referred_true_S_N"]:.2f}|')
 lines+=[""]
cost=result["inference_cost"]
lines+=["随机参照是同数量、仅在原判S中均匀无放回送审的超几何期望；不模拟人工正确率。分数是p(S)/(p(S)+p(Not))，不是校准概率，也不代表120或136。","","压力60的原判S共7条且全部错误；任意等量送审都一样，不能证明此面板的排序优势。自然120部分点剩余FS为0也不是部署零风险保证。", "", "本次新增GPU/API为0，复用113已有评分；未来部署应在原生生成中记录分支分数，当前没有实测其额外时延，不把重新提取分数的成本当作0。", "", "|历史评分覆盖|原输入平均tokens|三路径评分累计秒|记录的评分阶段秒|", "|---:|---:|---:|---:|", f'|{cost["historical_scoring_N"]}|{cost["historical_input_tokens_mean"]:.1f}|{cost["historical_three_path_scoring_seconds_sum"]:.2f}|{cost["historical_pilot_elapsed_seconds"]:.2f}|', "", "旧113计时包含三条完整标签路径；不等于未来只记录原生分支logits的边际成本。全程租赁、加载和回传费用在此未记录，不填0。", "", "此180面板已用于历史开发，自然与压力分别解释；不与1817混合，不称Conformal或正式风险保证。没有新推理、训练、API、bootstrap或GT选阈值；所有送审仍记为待人工，不默认修正。"]
(O/"native_score107.md").write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
print(json.dumps({name:{"N":p["N"],"predicted_S":p["original_predicted_S_N"],"false_S":p["original_false_S_N"],"points":[{"pct":q["requested_percent_of_original_S"],"review":q["referred_N"],"residual_FS":q["residual_false_S_N"],"trueS_review":q["referred_true_S_N"],"random_residual_FS":q["random_same_size_hypergeometric_expectation"]["residual_false_S_N"]} for q in p["points"]]} for name,p in result["panels"].items()},ensure_ascii=False))
