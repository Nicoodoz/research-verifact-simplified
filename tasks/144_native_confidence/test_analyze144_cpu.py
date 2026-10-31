"""Synthetic CPU checks only; no actual scoring, labels, patient text or GPU."""
from pathlib import Path
from unittest.mock import patch
import copy

import analyze144 as a


def main():
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
    print('PASS: fixed grid/floor/ties, GT-independent ranking, real zero scores, invalid/missing rejection, conservation, pilot and partial no-effects')


if __name__=='__main__':
    main()
