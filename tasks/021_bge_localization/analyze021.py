"""Offline API-vs-local BGE equivalence analysis. Never reads GT/Judge labels."""
from pathlib import Path
import csv, json, math, sys
import numpy as np
import common021 as c

sys.path.insert(0,str(c.ROOT/'tasks/009_retrieval_baselines'))
import study009 as baseline

def rank_order(ids,scores):
    return sorted(ids,key=lambda x:(-float(scores[x]),x))
def overlap(a,b):
    sa,sb=set(a),set(b)
    return len(sa&sb)/max(1,len(sa|sb))
def pearson(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    return float(np.corrcoef(a,b)[0,1]) if len(a)>1 else float('nan')
def spearman_orders(a,b):
    pa={x:i for i,x in enumerate(a)}; pb={x:i for i,x in enumerate(b)}
    ids=list(a)
    return pearson([pa[x] for x in ids],[pb[x] for x in ids])
def digest(text):
    import hashlib
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def main():
    api_ids=c.read(c.CAN20/'embedding_ids.json')
    local_ids=c.read(c.OUT/'local_embedding_ids.json')
    if api_ids!=local_ids: raise ValueError('Embedding ID order mismatch')
    api_vec=np.load(c.CAN20/'vectors.npy',allow_pickle=False).astype(np.float64)
    loc_vec=np.load(c.OUT/'local_vectors_fp16.npy',allow_pickle=False).astype(np.float64)

    api_norm=np.linalg.norm(api_vec,axis=1); loc_norm=np.linalg.norm(loc_vec,axis=1)
    cos=np.sum(api_vec*loc_vec,axis=1)/(api_norm*loc_norm)
    absdiff=np.max(np.abs(api_vec-loc_vec),axis=1)
    emb={
        'n':len(api_ids),'cosine_min':float(cos.min()),
        'cosine_p01':float(np.quantile(cos,.01)),
        'cosine_median':float(np.median(cos)),'cosine_mean':float(cos.mean()),
        'max_abs_diff_median':float(np.median(absdiff)),
        'max_abs_diff_max':float(absdiff.max()),
        'api_norm_mean':float(api_norm.mean()),'local_norm_mean':float(loc_norm.mean()),
    }
    local_can={x['proposition_id']:x for x in c.jsonlines(c.OUT/'local_candidates.jsonl')}
    api_base={x['proposition_id']:x for x in c.jsonlines(c.BASE20/'inputs.jsonl')}
    local_scores={x['proposition_id']:x['scores'] for x in c.jsonlines(c.OUT/'local_rerank_scores.jsonl')}
    prep={x['proposition_id']:x for x in c.jsonlines(c.PREP20/'inputs.jsonl')}
    passages={x['passage_id']:x for x in c.jsonlines(c.PREP20/'corpus.jsonl')}
    rows=[]; all_api=[]; all_raw=[]; all_sig=[]

    for pid in sorted(api_base):
        base=api_base[pid]; can=local_can[pid]; ls=local_scores[pid]
        api_scores={k:float(v) for k,v in base['scores'].items()}
        api_union=list(api_scores)
        ao=rank_order(api_union,api_scores); lo=rank_order(api_union,ls)
        top=min(16,len(api_union))
        for x in api_union:
            all_api.append(api_scores[x]); all_raw.append(float(ls[x]))
            all_sig.append(1/(1+math.exp(-float(ls[x]))))
        isolated=baseline.core.select_evidence(
            can['api_C48'],ls,passages,prep[pid]['admission']
        )
        local=baseline.core.select_evidence(
            can['local_C48'],ls,passages,prep[pid]['admission']
        )
        api_selected=base['selected_ids']; api_ref=base['reference']
        rows.append({
            'proposition_id':pid,
            'B48_exact':can['api_B48']==can['local_B48'],
            'C48_exact':can['api_C48']==can['local_C48'],
            'B48_set_exact':set(can['api_B48'])==set(can['local_B48']),
            'C48_set_exact':set(can['api_C48'])==set(can['local_C48']),
            'rerank_full_order_exact':ao==lo,
            'rerank_spearman':spearman_orders(ao,lo),
            'rerank_top16_order_exact':ao[:top]==lo[:top],
            'rerank_top16_set_overlap':len(set(ao[:top])&set(lo[:top]))/max(1,top),
            'isolated_selected_exact':isolated['selected_ids']==api_selected,
            'isolated_reference_exact':isolated['reference']==api_ref,
            'end_selected_exact':local['selected_ids']==api_selected,
            'end_selected_set_exact':set(local['selected_ids'])==set(api_selected),
            'end_selected_jaccard':overlap(local['selected_ids'],api_selected),
            'end_reference_exact':local['reference']==api_ref,
            'api_reference_sha256':digest(api_ref),
            'local_reference_sha256':digest(local['reference']),
        })

    n=len(rows)
    candidate={
        'B48_order_exact':sum(r['B48_exact'] for r in rows),
        'B48_set_exact':sum(r['B48_set_exact'] for r in rows),
        'C48_order_exact':sum(r['C48_exact'] for r in rows),
        'C48_set_exact':sum(r['C48_set_exact'] for r in rows),
    }
    rerank={
        'full_order_exact':sum(r['rerank_full_order_exact'] for r in rows),
        'spearman_mean':float(np.mean([r['rerank_spearman'] for r in rows])),
        'spearman_min':float(np.min([r['rerank_spearman'] for r in rows])),
        'top16_order_exact':sum(r['rerank_top16_order_exact'] for r in rows),
        'top16_set_overlap_mean':float(np.mean([r['rerank_top16_set_overlap'] for r in rows])),
        'api_vs_local_raw_pearson':pearson(all_api,all_raw),
        'api_vs_local_sigmoid_pearson':pearson(all_api,all_sig),
        'api_vs_local_sigmoid_mae':float(np.mean(np.abs(np.asarray(all_api)-np.asarray(all_sig)))),
        'isolated_selected_exact':sum(r['isolated_selected_exact'] for r in rows),
        'isolated_reference_exact':sum(r['isolated_reference_exact'] for r in rows),
    }
    end={
        'selected_order_exact':sum(r['end_selected_exact'] for r in rows),
        'selected_set_exact':sum(r['end_selected_set_exact'] for r in rows),
        'selected_jaccard_mean':float(np.mean([r['end_selected_jaccard'] for r in rows])),
        'reference_exact':sum(r['end_reference_exact'] for r in rows),
    }
    gate=(end['selected_order_exact']==n and end['reference_exact']==n)

    fields=list(rows[0])
    with (c.OUT/'claim_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    summary={
        'claims':n,'embedding':emb,'candidate':candidate,'reranker':rerank,
        'end_to_end':end,'frozen_equivalent_pass':gate,
        'pass_rule':'879/879 ordered selected_ids AND 879/879 reference exact',
        'gt_or_judge_performance_read':False,'reserved_test_used':False,'new_paid_api_calls':0,
    }
    c.save(c.OUT/'comparison_summary.json',summary)
    lines=[
        '# 021：BGE本地化与API冻结等价性检查','',
        '结论：**'+('PASS' if gate else 'FAIL')+'**（冻结等价性严格门槛）。','',
        '021没有调用新的收费API，没有使用GT/Judge正确率选择实现，也没有使用40名reserved test。','',
        '## 核心结果','',
        f'- Embedding逐向量cosine：mean {emb["cosine_mean"]:.8f}，min {emb["cosine_min"]:.8f}。',
        f'- B48有序完全一致：{candidate["B48_order_exact"]}/{n}；C48有序完全一致：{candidate["C48_order_exact"]}/{n}。',
        f'- Reranker在API候选上的完整排序完全一致：{rerank["full_order_exact"]}/{n}；平均Spearman {rerank["spearman_mean"]:.8f}。',
        f'- 仅替换reranker后的最终reference完全一致：{rerank["isolated_reference_exact"]}/{n}。',
        f'- embedding+reranker全本地后的selected_ids完全一致：{end["selected_order_exact"]}/{n}。',
        f'- embedding+reranker全本地后的最终reference完全一致：{end["reference_exact"]}/{n}。','',
        '## 判定','',
    ]
    if gate:
        lines.append('本地BGE链路满足021事前冻结的严格等价条件，可作为020 BGE API链路的冻结等价实现。')
    else:
        lines.append('本地BGE可以运行，但不满足“020冻结等价”定义；未来若切换，应视为新的实现条件并建立同期baseline。')
    lines += ['', '详细逐claim结果见 claim_comparison.csv；机器摘要见 comparison_summary.json。']
    (c.OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
