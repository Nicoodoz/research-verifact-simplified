"""Coverage sanity check: empty-reference failures never borrow full answers."""
from analyze129 import summarize


def main():
    labels=('Supported','Not Supported','Not Addressed')
    keys=[dict(id=str(i),sid='synthetic',GT=label) for i,label in enumerate(labels)]
    full={r['id']:dict(valid=True,verdict=r['GT']) for r in keys}
    new={'0':dict(valid=True,verdict='Supported'),'1':dict(valid=False,verdict=None)}
    result=summarize(keys,full,new)
    assert result['paired_valid_N']==1
    assert (result['new_missing_N'],result['new_invalid_N'])==(1,1)
    assert result['full_with_original_GT']['n']==1
    assert result['empty_with_original_GT_diagnostic_only']['n']==1
    assert result['full_predictions_not_used_to_fill_missing'] is True
    print('PASS: partial diagnostic receipts preserve invalid/missing, no model call')


if __name__=='__main__':main()
