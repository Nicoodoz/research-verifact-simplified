"""Read first receipts for the fixed687 development check, without imputation."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / '.local_models/120_full_pool_sft/internal687'
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as c
sys.path.insert(0, str(ROOT / 'tasks/120_full_pool_sft'))
from analyze120 import collect
from final_compare120 import metrics, paired, LABELS


def merge_first(*groups):
    result = {}
    for group in groups:
        for row in group:
            if row['id'] in result:
                raise ValueError('Duplicate first receipt: '+row['id'])
            result[row['id']] = row
    return result


def main():
    keys = c.rows(P / 'keys.jsonl')
    expected = {r['id'] for r in keys}
    if len(keys) != 687 or len(expected) != 687:
        raise ValueError('Frozen687 changed')
    inputs = {r['id']: r for r in c.rows(P/'bundle/data/internal687/internal120_inputs.jsonl')}
    a = merge_first(c.rows(P/'baseline107_cached.jsonl'), collect([P/'evidence/internal107']))
    b = merge_first(collect([P/'evidence/internal120']))
    jobs = {name: c.read(P/'bundle/data/internal687'/('internal'+name+'.json')) for name in ('107', '120')}
    coverage = {}
    for name, data in (('107', a), ('120', b)):
        if not set(data) <= expected:
            raise ValueError('Unexpected evaluation ID')
        for i, row in data.items():
            if row['source_adapter_sha256'] != jobs[name]['adapter_sha256']:
                raise ValueError('Wrong retained checkpoint')
            if row['source_prompt_sha256_104'] != inputs[i]['expected_prompt_sha256']:
                raise ValueError('Original full-reference input changed')
        coverage[name] = dict(expected_N=len(expected), received_N=len(data),
            valid_N=sum(r['valid'] for r in data.values()),
            invalid_N=sum(not r['valid'] for r in data.values()), missing_N=len(expected-set(data)))
    joint = [r for r in keys if a.get(r['id'], {}).get('valid') and b.get(r['id'], {}).get('valid')]
    result = dict(task=120,check='internal687',coverage=coverage,joint_valid_N=len(joint),
        original_GT_unchanged=True,no_training=True,confirmation40_used=False,
        cohort_role='Historically exposed8 development patients;43 other107 training IDs excluded.',
        no_independent_holdout_claim=True, missing_not_imputed=True,
        cached107_N=69,new107_requested_N=618,new120_requested_N=687)
    if joint:
        result['paired'] = paired(joint,a,b,'107_label_only',bootstrap=len(joint)==687)
        result['scores'] = dict(paper_r1=metrics(joint,{r['id']:r['paper_r1'] for r in joint}),
            label_only107=metrics(joint,{r['id']:a[r['id']]['verdict'] for r in joint}),
            full_pool_sft120=metrics(joint,{r['id']:b[r['id']]['verdict'] for r in joint}))
        result['by_author'] = {author:paired([r for r in joint if r['author']==author],a,b,'107_label_only')
            for author in sorted({r['author'] for r in joint})}
    out = ROOT / 'outputs/120_full_pool_sft'
    c.put(out/'internal687_comparison.json',result)
    c.putl(out/'internal687_predictions_sanitized.jsonl',[
        dict(r, baseline107=a.get(r['id'],{}).get('verdict'), candidate120=b.get(r['id'],{}).get('verdict'),
            baseline_valid=a.get(r['id'],{}).get('valid',False), candidate_valid=b.get(r['id'],{}).get('valid',False),
            baseline_missing=r['id'] not in a,candidate_missing=r['id'] not in b)
        for r in keys])
    lines=['# 120：原8名内部验证患者的687条复核','',
        '排除107已训练的43个ID；8名患者本身仍有历史暴露及其他训练命题，不是独立未接触测试。没有新增训练或选参。','',
        '|配置|共同有效数|MCC|PA|正确数|false-S/真实非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---:|---|']
    for name,m in result.get('scores',{}).items():
        recalls='/'.join(f"{100*m['per_class'][g]['recall']:.2f}%" for g in LABELS)
        lines.append(f"|{name}|{len(joint)}|{m['mcc']:.4f}|{100*m['percent_agreement']:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|{recalls}|")
    if joint:
        v=result['paired']; ch=v['changes']
        lines+=['',f"相对107：ΔMCC {v['delta_MCC']:+.4f}，正确数{v['delta_correct']:+d}，false-S {v['delta_false_S']:+d}。",'',
            '|真实类别|救回|误伤|','|---|---:|---:|']
        for label in LABELS:
            x=ch['by_class'][label];lines.append(f"|{label}|{x['rescued']}|{x['harmed']}|")
        lines+=['',f"false-S新增{ch['false_S_new']}，避免{ch['false_S_avoided']}。"]
    lines+=['','覆盖、混淆矩阵、患者与来源方向及描述性患者bootstrap见JSON；无效及缺失未补旧答案。',
        'paper_r1为不同模型与设置的作者历史参照；107为同9B底座和相同推理接口的微调对照。','']
    (out/'internal687_comparison.md').write_bytes('\n'.join(lines).encode())
    print(c.canonical(dict(coverage=coverage,joint_valid_N=len(joint),
        scores={k:{x:m[x] for x in ('mcc','percent_agreement','correct','false_S','non_S')}
                for k,m in result.get('scores',{}).items()})))


if __name__ == '__main__':
    main()
