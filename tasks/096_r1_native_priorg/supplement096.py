"""Contextual fixed comparisons; no new model or parameter selection."""
import sys
import common096 as c
import marlin096 as m
sys.path.insert(0,str(c.ROOT/'src'));sys.path.insert(0,str(c.ROOT/'tasks/095_anchored_minimal_contrast'))
from metrics095 import paired
from diagnostics096 import shape
def main():
    rr=c.lines(m.O/'unified_predictions.jsonl');out={}
    for panel in ['natural','diagnostic']:
        core=[r for r in rr if r['panel']==panel and r['B_core_valid'] and r['R1_core_valid']]
        out[panel]=dict(current_V4_final_vs_Original=paired(core,'Original','V4_PriorG'),scores_common={k:shape(core,k) for k in ['R1_scores','V4_scores']})
    c.put(m.O/'fixed_comparison_supplement.json',out);print('FIXED_COMPARISON_SUPPLEMENT_COMPLETE')
if __name__=='__main__':main()
