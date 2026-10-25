"""Final 021 API-vs-local structural equivalence analysis; never reads GT/Judge labels."""
from pathlib import Path
import argparse, csv, hashlib, json, math, sys
import numpy as np
import common021 as c

sys.path.insert(0,str(c.ROOT/'tasks/009_retrieval_baselines'))
import study009 as baseline

def rank(ids,scores):
    return sorted(ids,key=lambda x:(-float(scores[x]),x))

def corr(a,b):
    return float(np.corrcoef(np.asarray(a,float),np.asarray(b,float))[0,1])

def spearman_order(a,b):
    pa={x:i for i,x in enumerate(a)}; pb={x:i for i,x in enumerate(b)}
    return corr([pa[x] for x in a],[pb[x] for x in a])

def jac(a,b):
    a,b=set(a),set(b)
    return len(a&b)/max(1,len(a|b))

def sha_text(x):
    return hashlib.sha256(x.encode('utf-8')).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--vectors',default='local_vectors_fp32.npy')
    ap.add_argument('--candidates',default='local_candidates_fp32.jsonl')
    ap.add_argument('--scores',default='local_rerank_scores_fp32emb_fp16rr_b32.jsonl')
    a=ap.parse_args()

    api_ids=c.read(c.CAN20/'embedding_ids.json')
    local_ids=c.read(c.OUT/'local_embedding_ids.json')
    if api_ids!=local_ids:
        raise ValueError('embedding ID order mismatch')

    api_vec=np.load(c.CAN20/'vectors.npy',allow_pickle=False).astype(np.float64)
    loc_vec=np.load(c.OUT/a.vectors,allow_pickle=False).astype(np.float64)
    if api_vec.shape!=(2057,1024) or loc_vec.shape!=(2057,1024):
        raise ValueError('vector shape')

    an=np.linalg.norm(api_vec,axis=1); ln=np.linalg.norm(loc_vec,axis=1)
    ecos=np.sum(api_vec*loc_vec,axis=1)/(an*ln)
    emax=np.max(np.abs(api_vec-loc_vec),axis=1)

    cans={x['proposition_id']:x for x in c.jsonlines(c.OUT/a.candidates)}
    scores={x['proposition_id']:x['scores'] for x in c.jsonlines(c.OUT/a.scores)}
    base={x['proposition_id']:x for x in c.jsonlines(c.BASE20/'inputs.jsonl')}
    prep={x['proposition_id']:x for x in c.jsonlines(c.PREP20/'inputs.jsonl')}
    passages={x['passage_id']:x for x in c.jsonlines(c.PREP20/'corpus.jsonl')}
    if set(scores)!=set(base) or len(base)!=879:
        raise ValueError('incomplete 879 rerank scores')

    rows=[]; api_all=[]; raw_all=[]; sig_all=[]
    for pid in sorted(base):
        old=base[pid]; can=cans[pid]; local_score=scores[pid]
        api_score={k:float(v) for k,v in old['scores'].items()}
        api_ids_rr=list(api_score)
        if not set(api_ids_rr)<=set(local_score):
            raise ValueError('missing API pair local score')
        ao=rank(api_ids_rr,api_score); lo=rank(api_ids_rr,local_score)
        for x in api_ids_rr:
            v=float(local_score[x])
            api_all.append(api_score[x]); raw_all.append(v); sig_all.append(1/(1+math.exp(-v)))
        iso=baseline.core.select_evidence(can['api_C48'],local_score,passages,prep[pid]['admission'])
        end=baseline.core.select_evidence(can['local_C48'],local_score,passages,prep[pid]['admission'])
        top=min(16,len(ao))
        rows.append({
            'proposition_id':pid,
            'B48_order_exact':can['api_B48']==can['local_B48'],
            'B48_set_exact':set(can['api_B48'])==set(can['local_B48']),
            'B48_jaccard':jac(can['api_B48'],can['local_B48']),
            'C48_order_exact':can['api_C48']==can['local_C48'],
            'C48_set_exact':set(can['api_C48'])==set(can['local_C48']),
            'C48_jaccard':jac(can['api_C48'],can['local_C48']),
            'rerank_full_order_exact':ao==lo,
            'rerank_spearman':spearman_order(ao,lo),
            'rerank_top16_order_exact':ao[:top]==lo[:top],
            'rerank_top16_set_overlap':len(set(ao[:top])&set(lo[:top]))/max(1,top),
            'isolated_reranker_selected_exact':iso['selected_ids']==old['selected_ids'],
            'isolated_reranker_reference_exact':iso['reference']==old['reference'],
            'end_selected_order_exact':end['selected_ids']==old['selected_ids'],
            'end_selected_set_exact':set(end['selected_ids'])==set(old['selected_ids']),
            'end_selected_jaccard':jac(end['selected_ids'],old['selected_ids']),
            'end_reference_exact':end['reference']==old['reference'],
            'api_reference_sha256':sha_text(old['reference']),
            'local_reference_sha256':sha_text(end['reference']),
        })

    emb={
        'vectors':len(ecos),'dimension':api_vec.shape[1],
        'cosine_mean':float(np.mean(ecos)),'cosine_median':float(np.median(ecos)),
        'cosine_p01':float(np.quantile(ecos,.01)),'cosine_min':float(np.min(ecos)),
        'max_abs_diff_median':float(np.median(emax)),'max_abs_diff_max':float(np.max(emax)),
        'api_norm_mean':float(np.mean(an)),'local_norm_mean':float(np.mean(ln)),
    }
    cand={
        'B48_order_exact':sum(x['B48_order_exact'] for x in rows),
        'B48_set_exact':sum(x['B48_set_exact'] for x in rows),
        'B48_jaccard_mean':float(np.mean([x['B48_jaccard'] for x in rows])),
        'C48_order_exact':sum(x['C48_order_exact'] for x in rows),
        'C48_set_exact':sum(x['C48_set_exact'] for x in rows),
        'C48_jaccard_mean':float(np.mean([x['C48_jaccard'] for x in rows])),
    }
    rr={
        'api_pairs':len(api_all),
        'full_order_exact':sum(x['rerank_full_order_exact'] for x in rows),
        'spearman_mean':float(np.mean([x['rerank_spearman'] for x in rows])),
        'spearman_min':float(np.min([x['rerank_spearman'] for x in rows])),
        'top16_order_exact':sum(x['rerank_top16_order_exact'] for x in rows),
        'top16_set_overlap_mean':float(np.mean([x['rerank_top16_set_overlap'] for x in rows])),
        'api_vs_raw_pearson':corr(api_all,raw_all),
        'api_vs_sigmoid_pearson':corr(api_all,sig_all),
        'api_vs_sigmoid_mae':float(np.mean(np.abs(np.asarray(api_all)-np.asarray(sig_all)))),
        'isolated_selected_exact':sum(x['isolated_reranker_selected_exact'] for x in rows),
        'isolated_reference_exact':sum(x['isolated_reranker_reference_exact'] for x in rows),
    }
    end={
        'selected_order_exact':sum(x['end_selected_order_exact'] for x in rows),
        'selected_set_exact':sum(x['end_selected_set_exact'] for x in rows),
        'selected_jaccard_mean':float(np.mean([x['end_selected_jaccard'] for x in rows])),
        'reference_exact':sum(x['end_reference_exact'] for x in rows),
    }
    gate=end['selected_order_exact']==879 and end['reference_exact']==879

    with (c.OUT/'claim_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    summary={
        'implementation':{
            'embedding':'BAAI/bge-m3 HF revision 5617a9f61b028005a4858fdac845db406aefb181, FP32',
            'reranker':'BAAI/bge-reranker-v2-m3 HF revision 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e, FP16, batch32, max_length512',
        },
        'claims':879,'embedding':emb,'candidate':cand,'reranker':rr,'end_to_end':end,
        'frozen_equivalent_pass':gate,
        'pass_rule':'879/879 ordered selected_ids AND 879/879 exact reference',
        'new_paid_api_calls':0,'reserved_test_used':False,'gt_or_judge_performance_read':False,
    }
    c.save(c.OUT/'comparison_summary.json',summary)

    report=[
        '# 021：BGE本地化与API版冻结等价性检查','',
        '## 结论','',
        '**严格冻结等价性：'+('PASS' if gate else 'FAIL')+'。**','',
        '021成功实现两个BGE模型的本地GPU推理，并对020冻结输入进行全量879条claim的API→本地结构等价性检查。全程没有新收费API调用，没有使用reserved 40人，也没有读取GT或Judge正确率来选择实现。','',
        '## 本地实现','',
        '- Embedding：BAAI/bge-m3，固定HF commit 5617a9f61b028005a4858fdac845db406aefb181，官方LFS SHA-256已校验，FP32、CLS pooling、L2 normalize。',
        '- Reranker：BAAI/bge-reranker-v2-m3，固定HF commit 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e，官方LFS SHA-256已校验，FP16；冻结020 pair最大319 tokens，因此本地max_length=512不截断任何输入。',
        '- GPU：RTX 3060 Laptop GPU 6GB。','',
        '## 等价性结果','',
        f'- Embedding cosine：mean {emb["cosine_mean"]:.8f}，min {emb["cosine_min"]:.8f}。',
        f'- B48：有序完全一致 {cand["B48_order_exact"]}/879，集合完全一致 {cand["B48_set_exact"]}/879，平均Jaccard {cand["B48_jaccard_mean"]:.6f}。',
        f'- C48：有序完全一致 {cand["C48_order_exact"]}/879，集合完全一致 {cand["C48_set_exact"]}/879，平均Jaccard {cand["C48_jaccard_mean"]:.6f}。',
        f'- Reranker：API候选上的平均Spearman {rr["spearman_mean"]:.6f}，Top-16集合平均重合 {rr["top16_set_overlap_mean"]:.6f}。',
        f'- API relevance score vs sigmoid(local logit)：Pearson {rr["api_vs_sigmoid_pearson"]:.6f}，MAE {rr["api_vs_sigmoid_mae"]:.6f}。',
        f'- 固定API C48、仅替换reranker：final reference完全一致 {rr["isolated_reference_exact"]}/879。',
        f'- embedding+reranker全本地：selected IDs有序完全一致 {end["selected_order_exact"]}/879，最终reference完全一致 {end["reference_exact"]}/879，selected-ID平均Jaccard {end["selected_jaccard_mean"]:.6f}。','',
        '## 科学/工程解释','',
    ]
    if gate:
        report.append('本地实现满足021事前定义的严格冻结等价条件，因此可作为020 API BGE链路的等价替代实现。')
    else:
        report += [
            '本地模型本身与API高度相近，但未达到逐claim最终证据完全相同的严格标准。因此不能把本地版静默视作020原BGE服务的同一冻结实现。',
            '后续若在reserved test采用本地BGE，应把它视为一个新的实现条件：在进入reserved test前冻结本地模型commit、precision、tokenization、候选/selection规则，并建立对应的同期baseline；不要继承020 API链路的结果当作本地链路性能。',
        ]
    report += ['', '逐claim比较见 claim_comparison.csv；机器可读汇总见 comparison_summary.json。']
    (c.OUT/'report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
