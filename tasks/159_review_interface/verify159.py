"""Verify reusable policy against frozen144/148 flags; not a new efficacy test."""
from pathlib import Path
import sys,json,time
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,five_table,markdown_table
from review159 import mark_for_review,selfcheck

def main():
    started=time.perf_counter();selfcheck();keys,pred,raw=assets();p=pred['claim_repeat136'];margin={}
    for scope in ('pilot','screen160','old500_fixpath','full1817'):
        for f in (R/'.local_models/144_native_confidence'/scope/'evidence/results/claim_repeat136').glob('*.json'):
            r=read(f);margin[r['id']]=r['logit_S_minus_Not']
    records=[dict(id=i,verdict=p[i],native_margin=margin.get(i),patient_id=str(keys[i]['sid'])) for i in sorted(keys)]
    flags=read(R/'.local_models/148_patient_score/review_flags.json');checks=[]
    for mode in ('global_margin','patient_rank'):
        for k in (178,290):
            out,s=mark_for_review(records,fraction=k/1817,mode=mode)
            chosen={r['id'] for r in out if r['review_required']}
            assert chosen==set(flags[mode][str(k)]) and len(chosen)==k
            assert [r['verdict'] for r in out]==[r['verdict'] for r in records]
            checks.append(dict(mode=mode,k=k,exact_frozen_flag_match=True,summary=s))
    five=five_table(keys,keys,pred,raw);O=R/'outputs/159_review_interface'
    save(O/'analysis.json',dict(task=159,checks=checks,new_GPU_calls=0,new_API_calls=0,new_API_CNY=0,CPU_seconds=time.perf_counter()-started,label_changes=0,five_baselines=five))
    lines=['# 159 review_interface：可复用的保留原标签送审接口','',
        '已交付独立Python/JSONL接口，输入id、verdict、原生native_margin；可选patient_id和reason状态。输出原verdict、送审标记、缺分数状态和实际自动覆盖，原输入文件不覆盖。理由状态单独保留，不因解释冲突就改分类或默认增加分类送审。','',
        '```text','python tasks/159_review_interface/review159.py INPUT.jsonl OUTPUT.jsonl --fraction .10','python tasks/159_review_interface/review159.py INPUT.jsonl OUTPUT.jsonl --fraction .16 --mode patient_rank','```','',
        '复核比例基于全部输入；优先原生S中低margin。S缺分数单列并送审，因此真实负担可能超过请求数量，summary明确报告。patient_rank需同患者的一批命题，不宣称单文档或单条流式效果。无独立校准或Conformal保证。','',
        '合成检查通过；1817条缓存输入在global_margin/patient_rank、178/290四个固定点均逐ID匹配148原标记，且标签未变。这只验证接口实现了既有规则，不是独立的临床/分类有效性证明。实际风险/工作量取舍沿用144与148；157失败的理由优先组合没有放入默认排序。','',
        '## 固定五条分类参照','',markdown_table(five),'',
        '新增模型/API调用0、API费用0；CPU时间见analysis.json。部署仍需既有模型取得实际margin，可选理由另加151成本；缓存分析免费不代表系统免费。五基线成本缺项不补0，原生MCC/PA没有因复核标记改变。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps(dict(exact_real_flag_checks=len(checks),label_changes=0,new_model_calls=0)))

if __name__=='__main__':main()
