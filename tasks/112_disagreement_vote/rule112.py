"""Fixed label-only majority vote; a three-way tie keeps the107 baseline."""
LABELS=('Supported','Not Supported','Not Addressed')
def disagreement_vote(baseline,half,third=None):
    if baseline not in LABELS or half not in LABELS:
        raise ValueError('107 and half must have valid frozen predictions')
    if baseline==half:return baseline,'agreement'
    if third not in LABELS:return baseline,'third_invalid_fallback'
    if third==half:return half,'third_matches_half'
    if third==baseline:return baseline,'third_matches_baseline'
    return baseline,'three_way_tie'
