"""Join already source-read diagnostic cases to the final same-ID predictions."""
import common095 as c

def main():
    rows={r['id']:r for r in c.lines(c.OUT/'unified_9065_predictions.jsonl')};source=c.lines(c.OUT/'source_review_80.jsonl');wanted=['boundary_relation','C48_visible_raw_missed','correct_time_protection','missing_date_unknown','event_plan_completion','scope_time_ambiguity'];selected=[]
    for category in wanted:
        candidates=[r for r in source if r.get('category')==category]
        if candidates:selected.append(candidates[0])
    text=['# 095 B基准中的代表性救回与伤害','','这些病例来自事前冻结的发现性80例，不是新方法的确认样本。来源已人工阅读，以下仅把最终同ID标签与原说明连接；不据模型reason推定内部因果。原作者与B的pipeline不同，不能仅凭标签差推断作者出错原因。','','|ID|GT|原作者|B raw→G|相对作者|raw→G|自报分数S/NS/NA|','|---|---|---|---|---|---|---|']
    for s in selected:
        r=rows[s['id']];g=r['GT'];p=r['predictions'];raw,fin=p['B_raw'],p['B_PriorG'];o=p['Original'];comp='救回' if o!=g and fin==g else '伤害' if o==g and fin!=g else '正确数无变化';boundary='救回' if raw!=g and fin==g else '伤害' if raw==g and fin!=g else '正确数无变化';sc=r['B']['parsed']['scores'];score=[sc[k] for k in ['Supported','Not Supported','Not Addressed']] if sc else None
        assert raw==s['B_raw'] and fin==s['B_G'] and g==s['GT']
        text.append(f"|{r['id']}|{g}|{o}|{raw}→{fin}|{comp}|{boundary}|{score}|")
    text+=['','## 来源解释及边界','']
    for s in selected:text+=[f"- `{s['id']}`：{s['interpretation']} 已读来源编号{s['reviewed_reference_ids']}，哈希见80例原记录。"]
    text+=['','其中包内有可定位的有限范围或时间信息，支持做具体对应诊断；有些日期或过程尚未建立，必须保留unknown。G导致的救回/伤害是固定评分映射的可观察作用，不能说G重新找到了原文。完整病历标签不因本页阅读重新定义。','', '[全部逐例转移](baseline_case_transitions.jsonl) · [来源80例](source_review_80.jsonl) · [补充回查](source_review_supplement.json)']
    with (c.OUT/'baseline_cases.md').open('w',encoding='utf-8',newline='\n') as f:f.write('\n'.join(text)+'\n')
if __name__=='__main__':main()
