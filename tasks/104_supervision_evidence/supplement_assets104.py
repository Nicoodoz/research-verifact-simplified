"""Clarify physician-agreement provenance and mechanical teacher quote coverage.

No new semantic judgments, labels, source documents, or model requests.
"""
from collections import Counter, defaultdict
from itertools import combinations
import re

import common104 as c
from build104 import evidence_spans


def normal(text):
    return ' '.join(re.findall(r'[a-z]+|\d+(?:\.\d+)?',text.lower()))


def explicit_strings(text):
    return [m.group(1) or m.group(2) for m in re.finditer(r'"([^"\n]{8,1000})"|“([^”\n]{8,1000})”',text or '')]


def main():
    train=c.lines(c.PRIVATE/'train512_original.jsonl')
    lookup={r['id']:r for r in train}
    doctors={r['proposition_id']:r for r in c.lines(c.PRIVATE/'doctor_annotations_train512.jsonl')}
    teachers=c.lines(c.PRIVATE/'teachers_same_reference.jsonl')
    annotations=[]
    for row in train:
        d=doctors[row['id']]
        initial=[d[f'verdict{i}'] for i in range(1,4)]
        initial_counts=Counter(initial)
        computed=0 if len(initial_counts)==3 else max(initial_counts.values())
        assert int(d['round1_num_raters_agree'])==computed
        final_source='adjudicated_verdict' if d['adjudicated_verdict'] else 'round1_majority_vote'
        assert d['human_gt']==d[final_source]==row['GT']
        annotations.append(dict(id=row['id'],sid=row['sid'],GT=row['GT'],author=row['author'],
                                initial_round_votes=dict(initial_counts),
                                initial_num_agree_raw=int(d['round1_num_raters_agree']),
                                initial_all_three_disagree=computed==0,
                                initial_majority_present=bool(d['round1_majority_vote']),
                                initial_majority_label=d['round1_majority_vote'],
                                round2_decision_present=bool(d['round2_decision']),
                                adjudicated_verdict_present=bool(d['adjudicated_verdict']),
                                final_GT_source=final_source,
                                final_human_gt=d['human_gt'],
                                missing_initial_votes=sum(not v for v in initial),
                                missing_final_GT=not bool(d['human_gt'])))
    c.putl(c.OUT/'annotation_inventory512.jsonl',annotations)
    by_gt={}
    for GT in c.LABELS:
        rr=[r for r in annotations if r['GT']==GT]
        by_gt[GT]=dict(N=len(rr),initial_agreement=dict(Counter(r['initial_num_agree_raw'] for r in rr)),
                      final_GT_source=dict(Counter(r['final_GT_source'] for r in rr)),
                      missing_initial_votes=sum(r['missing_initial_votes'] for r in rr),
                      missing_final_GT=sum(r['missing_final_GT'] for r in rr))
    agreement=dict(N=512,by_GT=by_gt,
                   total_initial_agreement=dict(Counter(r['initial_num_agree_raw'] for r in annotations)),
                   total_final_GT_source=dict(Counter(r['final_GT_source'] for r in annotations)),
                   interpretation={'0':'All three initial labels differ; not zero raters and not missing data.',
                                   '2':'Two of the three initial labels agree.',
                                   '3':'All three initial labels agree.'},
                   adjudication_absence_is_expected_when_initial_majority_exists=True,
                   final_human_gt_missing=0,initial_vote_missing=0,
                   raw_doctor_labels_preserved=True)
    c.put(c.OUT/'annotation_summary.json',agreement)

    per_teacher=[]
    for teacher in teachers:
        if not teacher['prediction_matches_GT'] or not teacher.get('reason'):
            continue
        row=lookup[teacher['proposition_id']]
        strings=explicit_strings(teacher['reason'])
        spans,issues=evidence_spans(row['reference'],strings)
        per_teacher.append(dict(id=row['id'],GT=row['GT'],rater_alias=teacher['rater_alias'],model=teacher['model'],
                                double_quoted_strings=len(strings),
                                exactly_locatable_strings=sum(s['occurrence_count']>0 for s in spans),
                                strings_with_multiple_locations=sum(s['occurrence_count']>1 for s in spans),
                                source_rendered_units_covered=sum(any(x['sources'] for x in s['occurrences']) for s in spans),
                                reason_present=True,reasoning_chain_present=bool(teacher.get('reasoning_chain')),
                                reasoning_final_answer_present=bool(teacher.get('reasoning_final_answer')),
                                semantic_approval=False))
    c.putl(c.OUT/'teacher_quote_mechanical.jsonl',per_teacher)
    quote_summary={}
    for GT in c.LABELS:
        rr=[r for r in per_teacher if r['GT']==GT]
        quote_summary[GT]=dict(correct_label_reason_records=len(rr),
                              candidate_case_coverage=len({r['id'] for r in rr}),
                              records_with_double_quoted_strings=sum(r['double_quoted_strings']>0 for r in rr),
                              strings_total=sum(r['double_quoted_strings'] for r in rr),
                              strings_exactly_locatable=sum(r['exactly_locatable_strings'] for r in rr),
                              strings_multiple_locations=sum(r['strings_with_multiple_locations'] for r in rr),
                              strings_with_rendered_source_units=sum(r['source_rendered_units_covered'] for r in rr))
    c.put(c.OUT/'teacher_quote_summary.json',dict(by_GT=quote_summary,
            quote_detection='Only explicit double-quoted spans of 8..1000 characters; these may be terminology, not claimed citations.',
            location_policy='Every exact occurrence retained; no fuzzy quote or arbitrary first source selection.',
            unquoted_paraphrase_not_automatically_wrong=True,
            label_agreement_not_semantic_validation=True,
            source_display_number_not_original_note_ID=True,
            semantic_approval_count=0,new_API_calls=0))

    groups=defaultdict(list)
    normalized=defaultdict(list)
    for row in train:
        groups[row['claim']].append(row)
        normalized[normal(row['claim'])].append(row)
    conflicts=lambda groups:[dict(ids=[r['id'] for r in rr],labels=sorted({r['GT'] for r in rr})) for rr in groups.values() if len({r['GT'] for r in rr})>1]
    near=c.read(c.OUT/'near_duplicate_candidates.json')['pairs']
    c.put(c.OUT/'duplicate_summary.json',dict(N=512,
             exact_claim_duplicate_groups=sum(len(rr)>1 for rr in groups.values()),
             normalized_claim_duplicate_groups=sum(len(rr)>1 for rr in normalized.values()),
             exact_same_claim_different_GT=conflicts(groups),
             normalized_same_claim_different_GT=conflicts(normalized),
             near_duplicate_candidate_pairs=len(near),
             near_duplicate_different_GT=sum(not r['same_GT'] for r in near),
             candidate_rule='Same patient only; claim token-set Jaccard>=0.8. Not semantic duplicate certification.',
             automatic_removals=0))
    notes='''# 104资产清单字段解释

`asset_inventory512.jsonl`保留原512条的程序化清单，正文在私有同名文件；本说明及三个补充表不改变原inventory_freeze或任何103输入/标签。

- `round1_num_raters_agree`是初轮三名医生的标签一致数：3为三人一致，2为两人一致，0为三种标签各一票，不是没有医生标注。它不是最终GT置信概率。
- 512条初轮投票及最终human_gt均无缺失。480条以初轮多数为最终GT；32条初轮三种标签不同，经后续裁定形成原human_gt。480条adjudicated_verdict为空是未触发该流程，不能算最终标签缺失。
- `doctor_vote_counts`原清单累计非空的1—5轮投票，不能当作初轮一致数；明确拆分的初轮票与最终GT来源见`annotation_inventory512.jsonl`和`annotation_summary.json`。
- 教师`same_reference`严格要求命题ID、claim、reference ID及实际正文SHA相同；教师预测=GT只是理由候选条件。其他reference的解释不进入复用候选。
- `teacher_quote_mechanical.jsonl`/`teacher_quote_summary.json`仅对正确标签候选理由中的显式双引号片段做精确定位，保存所有重复位置的数量；没有引号不等于理由错误，有来源位置也不认证关系、对象、时间或标签正确。完整reason/reasoning字段继续私有。
- 原reference通常发布显示编号、日期、类别及描述，未发布原始note ID时不得把显示编号冒充note ID；构建配对包时保留null和缺失说明。
- `duplicate_summary.json`区分同claim不同GT与近重复候选。词集合近似只用于盘点，不能当成临床关系判断或自动删除理由。
'''
    (c.OUT/'asset_inventory_notes.md').write_bytes(notes.encode('utf-8'))
    print(c.canonical(dict(annotation=agreement,quotes=quote_summary,duplicates=c.read(c.OUT/'duplicate_summary.json'))))


if __name__=='__main__':main()
