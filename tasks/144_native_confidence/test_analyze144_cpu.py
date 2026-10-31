"""Synthetic CPU checks only; no actual scoring, labels, patient text or GPU."""
from pathlib import Path
from unittest.mock import patch
import copy

import analyze144 as a


def main():
    nested=[dict(started_epoch=1793438249.8062503,completed_epoch=1793438412.63986),
            dict(started_epoch=1793438249.805574,completed_epoch=1793438412.7356665)]
    merged=a.interval_union(nested)
    assert len(merged)==1 and abs(merged[0]['seconds']-162.93009328842163)<1e-6
    disjoint=a.interval_union([dict(started_epoch=x,completed_epoch=y) for x,y in [(0,10),(2,9),(9,20),(30,35)]])
    assert [(x['started_epoch'],x['completed_epoch']) for x in disjoint]==[(0,20),(30,35)]
    assert sum(x['seconds'] for x in disjoint)==25
    rows = [dict(id=f'{i:02}', sid=str(i//5), GT=a.LABELS[i % 3]) for i in range(30)]
    native = {r['id']: 'Supported' if i < 20 else 'Not Supported' for i,r in enumerate(rows)}
    scores = {f'{i:02}': 0.0 for i in range(20)}
    points = a.ranked_points(rows, native, scores)
    assert [p['review']['N'] for p in points] == [0, 1, 2, 4, 6]
    for point in points:
        count = point['review']['N']
        assert point['review_ids'] == [f'{i:02}' for i in range(count)]
        assert point['automatic_N'] + count == len(rows)
        assert point['remaining_automatic_false_S'] + point['review']['intercepted_false_S'] == point['native']['false_S']
        assert point['review']['intercepted_false_S'] + point['review']['deferred_correct_S'] == count
        assert point['additional107_calls'] == 0 and 'logical_inference_calls' not in point
    changed = [dict(row, GT='Supported') for row in reversed(rows)]
    assert [p['review_ids'] for p in a.ranked_points(changed,native,scores)] == [p['review_ids'] for p in points]
    missing = dict(scores)
    del missing['00']
    try:
        a.ranked_points(rows,native,missing)
        raise AssertionError('Missing score was imputed')
    except ValueError:
        pass
    for bad in (float('nan'), float('inf'), None, False):
        invalid = dict(scores, **{'00':bad})
        try:
            a.ranked_points(rows,native,invalid)
            raise AssertionError('Invalid score was accepted')
        except ValueError:
            pass
    original_labels=dict(a='Supported',b='Supported',c='Supported',d='Not Supported')
    original_margins=dict(a=-.02,b=0.0,c=1.0,d=-4.0)
    before=(dict(original_labels),dict(original_margins))
    check=a.native_branch_consistency(original_labels,original_margins)
    assert check['scored_native_S_N']==3 and check['negative_N']==check['zero_N']==1
    assert check['negative_records']==[dict(id='a',margin=-.02)]
    assert check['zero_records']==[dict(id='b',margin=0.0)]
    assert (original_labels,original_margins)==before
    expected = {('native120',str(i)): {} for i in range(9)}
    job = dict(scope='pilot', evaluation_scope='full1817', variants=['native120'],
               score_ids_by_variant={'native120':[str(i) for i in range(9)]},
               evaluation_metrics_allowed=True)
    full = {key: {'logit_S_minus_Not': 0.0} for key in expected}
    #Even an erroneously permissive flag cannot turn a pilot into performance.
    with patch.object(a,'read_job',return_value=(job,expected,Path('.'))), patch.object(a,'collect',return_value=(full,{},[],full,[],{})), patch.object(a,'cost_summary',return_value={}), patch.object(a.c,'sha',return_value='fixture'):
        result = a.analyze(Path('.'),[])
        assert result['status']=='PILOT_COMPLETE_NO_PERFORMANCE'
        assert result['effect_metrics_generated'] is False and 'effects' not in result
    partial = copy.copy(full)
    removed = partial.pop(next(iter(partial)))
    missing_key = next(key for key in full if key not in partial)
    with patch.object(a,'read_job',return_value=(job,expected,Path('.'))), patch.object(a,'collect',return_value=(partial,{},[missing_key],partial,[],{})), patch.object(a,'cost_summary',return_value={}), patch.object(a.c,'sha',return_value='fixture'):
        result = a.analyze(Path('.'),[])
        assert result['status']=='COVERAGE_ONLY' and result['effect_metrics_generated'] is False
        assert 'effects' not in result
    print('PASS: interval union for nested/overlapping/disjoint runs, fixed grid/floor/ties, GT-independent ranking, real zero scores, invalid/missing rejection, conservation, branch consistency, pilot and partial no-effects')


if __name__=='__main__':
    main()
