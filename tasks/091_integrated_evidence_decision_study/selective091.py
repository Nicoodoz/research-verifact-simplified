"""Executable feasibility operator. No API, model fitting, or GT inputs."""
from common091 import LABELS,logs,h
from c_materials091 import witness

def action(claim,reference,final_label):
    if final_label not in LABELS:raise ValueError('invalid original label')
    w=witness(claim,reference)
    return dict(action='defer' if final_label==LABELS[0] and w['missing'] else 'retain_baseline',original_label=final_label,
                evidence_sufficiency='unknown',**w)

def matched_margin_ids(records,k,eligible_only=False):
    # records contain id, scores, final_label and eligible, never GT.
    pool=[x for x in records if x['final_label']==LABELS[0] and (x['eligible'] or not eligible_only)]
    if not 0<=k<=len(pool):raise ValueError('unmatched review budget')
    return [x['id'] for x in sorted(pool,key=lambda x:(float(logs(x['scores'])[0]-max(logs(x['scores'])[1:])),h('091/tie/'+x['id'])))[:k]]
