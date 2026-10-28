"""Recompute only the affected 104 derived association from raw doctor votes."""
from collections import Counter
from copy import deepcopy
import duckdb
import common105 as c

def main():
    out104=c.ROOT/'outputs/104_supervision_evidence';private104=c.ROOT/'.local_models/104_supervision_evidence'
    source=c.ROOT/'data/00_raw/verifact-bhc/1.1.0/propositions/human_verdicts.csv.gz'
    train=c.rows(private104/'train512_original.jsonl');original={r['id']:r for r in train}
    with duckdb.connect() as db:
        db.execute('CREATE TEMP TABLE wanted(id VARCHAR)')
        db.executemany('INSERT INTO wanted VALUES (?)',[(r['id'],) for r in train])
        values=db.execute('SELECT proposition_id,round1_num_raters_agree,verdict1,verdict2,verdict3,human_gt FROM read_csv_auto(?,all_varchar=true) JOIN wanted ON proposition_id=id',[str(source)]).fetchall()
    assert len(values)==512
    agreement={}
    for identifier,raw,*rest in values:
        votes=rest[:3];GT=rest[3];counts=Counter(votes)
        computed=0 if len(counts)==3 else max(counts.values())
        assert computed==int(raw) and GT==original[identifier]['GT']
        agreement[identifier]=computed
    old=c.read(out104/'supervision_summary.json');corrected=deepcopy(old)
    joined=c.rows(private104/'review_joined.jsonl')
    for state,stats in corrected['annotation_and_teacher_association'].items():
        selected=[r for r in joined if r['final_status']==state]
        stats['initial_three_agree']=sum(agreement[r['id']]==3 for r in selected)
        for GT,sub in stats['by_GT'].items():sub['initial_three_agree']=sum(r['GT']==GT and agreement[r['id']]==3 for r in selected)
    assert corrected['annotation_and_teacher_association']['gt_explained']['N']==196
    assert corrected['annotation_and_teacher_association']['gt_explained']['initial_three_agree']==92
    assert corrected['annotation_and_teacher_association']['unresolved']['N']==78
    assert corrected['annotation_and_teacher_association']['unresolved']['initial_three_agree']==21
    c.put(out104/'supervision_summary_corrected.json',corrected)
    note=dict(scope='derived association counts only; raw GT/pairs/receipts unchanged',
              cause='CSV round1_num_raters_agree is str; old code compared directly with int 3',
              source_vote_reconstruction=True,train512_N=512,
              states={k:dict(N=v['N'],initial_three_agree=v['initial_three_agree']) for k,v in corrected['annotation_and_teacher_association'].items()},
              source_file_sha256=c.sha(source),original_summary_sha256=c.sha(out104/'supervision_summary.json'),
              corrected_summary_sha256=c.sha(out104/'supervision_summary_corrected.json'),
              frozen_label_only_sha256=c.sha(private104/'paired/label_only.jsonl'),
              frozen_evidence_brief_sha256=c.sha(private104/'paired/evidence_brief.jsonl'),GT_modified=False)
    c.put(out104/'agreement_correction_105.json',note)
    c.put(c.OUT/'agreement_correction.json',note)
    (out104/'agreement_correction_105.md').write_bytes(('''# 105接手时的104派生统计更正

原CSV一致数字段是字符串，旧`analyze104.py`直接与整数3比较，导致`annotation_and_teacher_association`的三医生一致数被误计为0。105从原human_verdicts.csv.gz逐条重建前三名医生投票，并核对原GT，得到：保留196条中92条三人一致；unresolved 78条中21条三人一致。其余分层与指纹见`agreement_correction_105.json`。

已修正分析器的类型比较。原冻结`supervision_summary.json`和`complete.json`保留；更正阅读件为`supervision_summary_corrected.json`。196条两臂、医生GT、原始回执、其他104结论与费用均不改变。
''').encode('utf-8'))
    print(c.canonical(note['states']))

if __name__=='__main__':main()
