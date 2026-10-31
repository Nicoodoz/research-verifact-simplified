"""Preserve all AI suggestions; build only a source-checked NA replacement."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2];P=R/'.local_models/162_train_demo_pool'
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def main():
    data={r['id']:r for r in rows(P/'candidates.jsonl')};assert len(data)==6
    decisions=[]
    candidate='8a1b103a-a336-0f0b-fd7e-27a9e485d527'
    for i,r in data.items():
        review=json.loads((P/'review'/i/'result.json').read_text());receipts=[]
        for f in (P/'review'/i).glob('attempt*/receipt.json'):
            receipt=json.loads(f.read_text());native=json.loads(receipt['body_text']) if receipt.get('http_status')==200 else None
            if native:receipts.append(native)
        assert receipts and receipts[-1]['choices'][0]['finish_reason']=='stop'
        reason='AI_unsuitable_for_clear_demo'
        if i=='f151201f-1899-5871-319d-bde96fe83e30':reason='AI_selected_units_omit_material_same_reference_units'
        if i==candidate:reason='retained_NA_temporal_example_with_added_complete_anchor_unit37'
        decisions.append(dict(id=i,GT=r['GT'],GT_changed=False,AI_suitable=bool(review.get('parsed',{}).get('suitable')),local_retained=i==candidate,local_decision=reason,material_omitted_units=[25,26,31,32,33,49,53] if i=='f151201f-1899-5871-319d-bde96fe83e30' else []))
    r=data[candidate];assert r['GT']=='Not Addressed' and r['role']=='original120_train32'
    selected=[36,37,41,42];units={u['number']:u['text'] for u in r['units']};excerpt=r['prefix']+'\n'.join(units[n].rstrip() for n in selected);assert len(excerpt)<=2200
    previous=rows(R/'.local_models/152_demo_na/examples.jsonl');examples=[previous[0],previous[1],dict(id=r['id'],sid=r['sid'],GT=r['GT'],claim=r['claim'],reference=excerpt,answer=json.dumps({'verdict':r['GT']},separators=(',',':')))]
    assert [e['GT'] for e in examples]==['Supported','Not Supported','Not Addressed'] and len({str(e['sid']) for e in examples})==3
    (P/'examples.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in examples),encoding='utf-8')
    ledger=[r for r in rows(R/'.local_models/night_20261031/api_ledger.jsonl') if r.get('task')=='162_train_demo_pool'];received=[r for r in ledger if r['event']=='received']
    budget=dict(attempts=len(received),HTTP200=sum(r['http_status']==200 for r in received),unknown=sum(r['outcome_unknown'] for r in received),reserved_CNY=sum(r.get('reservation_CNY',0) for r in ledger),known_peak_CNY=sum(r.get('estimated_CNY_peak_no_discount') or 0 for r in received),input_tokens=sum((r.get('usage') or {}).get('prompt_tokens',0) for r in received),output_tokens=sum((r.get('usage') or {}).get('completion_tokens',0) for r in received),attempt_seconds=sum(r['seconds'] for r in received))
    O=R/'outputs/162_train_demo_pool';(O/'preparation.json').write_text(json.dumps(dict(N_candidates=6,decisions=decisions,retained_new_demo_N=1,changed_example_label='Not Addressed',original_S_NS_unchanged=True,source_units=selected,added_complete_unit_after_local_read=37,excerpt_characters=len(excerpt),excerpt_sha256=hashlib.sha256(excerpt.encode()).hexdigest(),GT_changed=False,new_classification_calls=0,budget=budget),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 162 train_demo_pool：训练侧选例准备结果','',
        '原训练32人512条预测中固定选了六个不同患者的强错误候选，S/NS/NA各2；不使用评价或确认患者。V4读取完整原reference及固定训练GT。它认为2例可抽取、4例不适合清楚演示。研发模型继续核对完整原文，发现其中一个NS建议遗漏了同reference内的重要相关单元，拒绝把它作为清楚的NS示例；保留教师首答及原GT，不凭教师或研发模型改标。','',
        '最终只保留一个新的NA示例，替换152第三例；原S/NS两例完全不变。保留源单元36/37/41/42，其中37是研发模型阅读完整原文后补入的完整时间锚点，避免节选中丢失先后关系。全部摘录为原文，不总结、不改写；目标病例reference仍完整。此核对不是医生新标注或独立审计。','',
        f"7次API尝试、6次HTTP200、1次HTTP0未知；V4 thinking-high/max8192、并发2，输入{budget['input_tokens']}、输出{budget['output_tokens']} tokens，已知未优惠忙时原价估算¥{budget['known_peak_CNY']:.6f}，全部预留¥{budget['reserved_CNY']:.4f}保留。HTTP200没有按内容重发；各尝试合计{budget['attempt_seconds']:.2f}秒不是并发墙钟。GPU新分类调用0，连续租金仍计整个窗口。",'',
        '结论：极端训练错误不自动等于适合的示例；不能用删证据使原标签显得成立。只准备一个固定NA替换候选，待完整152及训练主线后决定是否执行160初筛；目前没有分类收益证明，不外推或升级系统。所有医生GT、训练原文、教师意见、完整源单元和失败私有保留。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8');print(json.dumps(dict(new_demo_N=1,excerpt_characters=len(excerpt),budget=budget),ensure_ascii=False))

if __name__=='__main__':main()
