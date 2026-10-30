"""Check whether120's quality/risk tradeoff is confined to disputed doctor labels.

Uses existing predictions and original label metadata only. No relabeling,
training selection, new inference or clinical-text export.
"""
from pathlib import Path
from collections import Counter
import csv,gzip,json,sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'))
from final_compare120 import paired,LABELS


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def doctor_metadata():
    source=ROOT/'data/00_raw/verifact-bhc/1.1.0/propositions/human_verdicts.csv.gz'
    result={}
    with gzip.open(source,'rt',encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            votes=[row['verdict'+str(i)] for i in range(1,4)]
            if not all(v in LABELS for v in votes):
                raise ValueError('Unexpected original first-round physician verdict')
            largest=max(Counter(votes).values())
            # The source encodes three different votes as zero agreeing raters.
            expected_stored=0 if largest==1 else largest
            if expected_stored!=int(row['round1_num_raters_agree']):
                raise ValueError('Stored and recomputed agreement differ')
            key=row['proposition_id']
            if key in result:raise ValueError('Duplicate physician metadata ID')
            result[key]=dict(GT=row['human_gt'],first_round_agreement=largest,
                first_round_unanimous=largest==3,
                any_first_round_uncertain=any(row['uncertain_flag'+str(i)].strip().lower()=='true' for i in range(1,4)),
                adjudicated=bool(row['adjudicated_verdict'].strip()),
                adjudication_changes_majority=bool(row['adjudicated_verdict'].strip() and row['human_gt']!=row['round1_majority_vote']))
    return result


def evaluate(cohort,metadata):
    if len(cohort)!=len({r['id'] for r in cohort}):raise ValueError('Duplicate cohort ID')
    for row in cohort:
        if row['id'] not in metadata or row['GT']!=metadata[row['id']]['GT']:
            raise ValueError('Missing original annotation metadata or changed GT')
        if row['baseline107'] not in LABELS or row['verdict'] not in LABELS:
            raise ValueError('This completed cohort requires valid cached predictions')
    groups={'all':cohort,
        'first_round_unanimous':[r for r in cohort if metadata[r['id']]['first_round_unanimous']],
        'first_round_disagreement':[r for r in cohort if not metadata[r['id']]['first_round_unanimous']],
        'adjudicated':[r for r in cohort if metadata[r['id']]['adjudicated']],
        'not_adjudicated':[r for r in cohort if not metadata[r['id']]['adjudicated']],
        'any_first_round_uncertain':[r for r in cohort if metadata[r['id']]['any_first_round_uncertain']]}
    assert len(groups['first_round_unanimous'])+len(groups['first_round_disagreement'])==len(cohort)
    result={}
    for name,group in groups.items():
        if not group:continue
        old={r['id']:dict(verdict=r['baseline107']) for r in group}
        new={r['id']:dict(verdict=r['verdict']) for r in group}
        value=paired(group,old,new,'107_label_only',bootstrap=False)
        value.update(N=len(group),GT_counts=dict(Counter(r['GT'] for r in group)),
            uncertainty_is_not_label_error=True)
        result[name]=value
    return result


def main():
    meta=doctor_metadata()
    full=rows(ROOT/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')
    original_keys={r['id']:r for r in rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    full=[dict(r,paper_r1=original_keys[r['id']]['paper_r1']) for r in full]
    internal=[dict(r,verdict=r['candidate120']) for r in rows(ROOT/'outputs/120_full_pool_sft/internal687_predictions_sanitized.jsonl')]
    assert len(full)==1817 and len(internal)==687
    assert not {r['id'] for r in full}&{r['id'] for r in internal}
    cohorts={'selection1817':full,'internal687':internal}
    result=dict(method='Original first-round doctor agreement strata; original finalGT retained',
        new_model_calls=0,new_training=0,new_API=0,groups_chosen_without_model_scores=True,
        no_label_exclusion=True,no_reweighting=True,original_GT_unchanged=True,
        first_round_unanimity_not_certified_ground_truth=True,
        groups_overlap_except_declared_partitions=True,
        cohorts={name:evaluate(values,meta) for name,values in cohorts.items()})
    out=ROOT/'outputs/120_full_pool_sft'
    (out/'annotation_strata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 120：医生原始标注分歧与分类得失','',
        '仅用原始三位医生首轮投票与现成107／120预测分层；保留最终医生GT，所有样本留在原主表。首轮一致不等于标注无误，分歧也不等于标签错误。分层互有重叠，不能相加；只有首轮一致／有分歧、是否经过裁定分别构成完整划分。','',
        '|队列／首轮标注|N（S/NS/NA）|107 MCC→120 MCC|107正确→120正确|107 false-S→120 false-S／非S|S救回/误伤|NS救回/误伤|NA救回/误伤|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    summary={}
    for name,groups in result['cohorts'].items():
        summary[name]={}
        for key in ('all','first_round_unanimous','first_round_disagreement','adjudicated'):
            if key not in groups:continue
            value=groups[key];a=value['scores']['107_label_only'];b=value['scores']['candidate']
            classes=value['GT_counts'];change=value['changes']['by_class']
            count='/'.join(str(classes.get(c,0)) for c in LABELS)
            transition=[f"{change[c]['rescued']}/{change[c]['harmed']}" for c in LABELS]
            lines.append(f"|{name}/{key}|{value['N']}（{count}）|{a['mcc']:.4f}→{b['mcc']:.4f}|{a['correct']}→{b['correct']}|{a['false_S']}→{b['false_S']}/{b['non_S']}|"+'|'.join(transition)+'|')
            summary[name][key]=dict(N=value['N'],delta_correct=value['delta_correct'],delta_MCC=value['delta_MCC'],
                falseS107=a['false_S'],falseS120=b['false_S'],non_S=b['non_S'])
    lines+=['','原始GT与预测均按ID精确关联，1817与687各自完整且无交叉。无重新推理、训练、改标、删除有分歧样本或搜索临床成本权重。详细PA、三类指标与混淆矩阵见JSON。','']
    (out/'annotation_strata.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
