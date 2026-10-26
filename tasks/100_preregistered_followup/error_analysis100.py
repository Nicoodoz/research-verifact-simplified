"""Completed-output transfers and interpretation checks only; no new labels or API."""
from collections import Counter
import statistics
import common100 as c
def main():
 a=c.read(c.OUT/'confirmation_analysis.json');dev=c.read(c.OUT/'development_analysis.json');rows=c.lines(c.OUT/'confirmation_predictions.jsonl');usage=c.lines(c.OUT/'confirmation_usage.jsonl');build={r['id']:r for r in c.lines(c.OUT/'construction_ledger.jsonl')}
 out={}
 for name,pp in a['panels'].items():
  out[name]={}
  for base in ['O','C','S24']:
   p=pp['paired']['L24__vs__'+base]
   out[name][base]={k:p[k] for k in ['N','rescue','harm','net','rescue_by_GT','harm_by_GT','false_S_added','false_S_prevented','false_S_rate_delta','false_S_rate_delta_CI95','patient_win_loss_tie','class_transitions']}
   out[name][base]['delta_MCC_CI95']=p['paired']['metrics']['mcc']
 aliases={};lengths={}
 for panel in ['natural','pressure']:
  rr=[r for r in rows if r['panel']==panel];same=[r for r in rr if build[r['id']]['S_equals_L']]
  assert all(r['predictions'].get('S24')==r['predictions'].get('L24') for r in same)
  valid=[r for r in rr if r['predictions'].get('S24') in c.LABELS and r['predictions'].get('L24') in c.LABELS]
  aliases[panel]=dict(frozen_N=len(rr),same_S_L_body=len(same),different_S_L_body=len(rr)-len(same),valid_S_L=len(valid),S_L_label_difference=sum(r['predictions']['S24']!=r['predictions']['L24'] for r in valid),label_differences_by_GT=dict(Counter(r['GT'] for r in valid if r['predictions']['S24']!=r['predictions']['L24'])))
  uu=[u for u in usage if u['panel']==panel and not u['repeat']]
  lengths[panel]={arm:dict(N=sum(u['arm']==arm for u in uu),mean_actual_input=statistics.mean(u['prompt_tokens'] for u in uu if u['arm']==arm),mean_actual_output=statistics.mean(u['completion_tokens'] for u in uu if u['arm']==arm),mean_no_cache_cny=statistics.mean(u['no_cache_deployment_cny'] for u in uu if u['arm']==arm)) for arm in ['O','C','S24','L24']}
 n=a['panels']['natural']['tables'];old=dev['panels']['natural']['tables'];st=a['stability']
 summary=dict(natural_new_correct_by_GT={lab:sum(r['GT']==lab and r['predictions'].get('L24')==lab for r in rows if r['panel']=='natural' and all(r['predictions'].get(z) in c.LABELS for z in ['O','C','S24','L24']))-sum(r['GT']==lab and r['predictions'].get('O')==lab for r in rows if r['panel']=='natural' and all(r['predictions'].get(z) in c.LABELS for z in ['O','C','S24','L24'])) for lab in c.LABELS},
  development_delta_MCC_L_O=old['L24']['mcc']-old['O']['mcc'],confirmation_delta_MCC_L_O=n['L24']['mcc']-n['O']['mcc'],
  no_practical_route_passed=True,decision_stability_pass_is_not_positive_evidence=True,
  repeat_common_N=st['common_N'],repeat_flips=st['flips'],repeat_second_delta_MCC_L_O=st['second_delta_MCC'],
  stability_clarification='Primary MCC/risk practical routes both failed. The decision stability_pass flag is inapplicable as a positive claim; L-O repeat MCC is negative and O/L labels did not flip. Do not label this a stable advantage.',
  correct_final_status='失败停止',no_new_API=True,no_GT_or_decision_changes=True)
 c.put(c.OUT/'error_transfer_analysis.json',dict(transfers=out,body_identity_and_label_changes=aliases,matched_costs_by_panel=lengths,interpretation=summary))
 text=f'''# 100错误转移与判定说明

确认自然共同{a['panels']['natural']['common_N']}条，L24比O净多对1条，却使MCC从{n['O']['mcc']:.4f}降到{n['L24']['mcc']:.4f}、错误支持从{n['O']['false_S']}/{n['O']['true_non_S']}增至{n['L24']['false_S']}/{n['L24']['true_non_S']}。正确数变化按GT为{summary['natural_new_correct_by_GT']}：Supported改善掩盖了NS/NA损失，不能用PA单列包装为成功。

开发L−O ΔMCC为{summary['development_delta_MCC_L_O']:+.4f}，独立患者确认变为{summary['confirmation_delta_MCC_L_O']:+.4f}。方法、24K、规模和判据均未重调，未为延续开发阳性追加样本或候选。

确认同长度S/L实质相同与标签变化：{aliases}。L没有超过S24的MCC或实用门槛，完整note机制未成立；相对更便宜C也没有实用优势。普通BM25、完整note检索和长度配平本来就不是新算法，本轮最多检验其任务适配，不能改名包装。

重复共同{st['common_N']}/16，翻转{st['flips']}，第二次L−O ΔMCC={st['second_delta_MCC']:+.4f}。主实用路线均未通过，没有可声称稳定的核心优势；confirmation_decision.json中的stability_pass字段不能单独解读为总体稳定性通过。完整首/重复表保留原样；最终“失败停止”不变。

压力的false-S减少不抵消自然MCC/类别损失。原GT、原始回执和首次答案未更改，没有新收费调用。逐GT转移、救回/伤害、患者输赢与费用见error_transfer_analysis.json。
'''
 (c.OUT/'error_transfer_analysis.md').write_bytes(text.encode());print(c.canonical(summary))
if __name__=='__main__':main()
