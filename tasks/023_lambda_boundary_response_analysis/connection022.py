"""Describe the already-frozen022 range on023 curves; no fit or new parameter choice."""
from pathlib import Path
import common023 as c

if __name__=='__main__':
    old=c.ROOT/'outputs/022_competition_aware_support_calibration/stageA_002';c.check(old)
    fits=c.read(old/'fitted_parameters.json');gs=[r['theta'][0] for r in fits if r['method']=='G']
    pp={(r['proposition_id'],r['repeat'],r['method']):r['verdict'] for r in c.jl(old/'oof_predictions.jsonl')}
    rows=c.jl(c.OUT/'preparation_001/scores.jsonl');pred=c.decode(c.logs([r['scores'] for r in rows]),1.75)
    result=dict(global_lambda_range=[min(gs),max(gs)],lambda_1_75_is_existing_prespecified_local_diagnostic=True,old_G_different_from_fixed_1_75=sum(pp[(r['proposition_id'],r['repeat'],'G')]!=c.LABELS[pred[i]] for i,r in enumerate(rows)),old_C_different_from_G=sum(pp[(r['proposition_id'],r['repeat'],'G')]!=pp[(r['proposition_id'],r['repeat'],'C')] for r in rows),score_observations=len(rows),fixed_lambda_remains=2,new_fit=False,new_API_calls=0,source_hashes={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in (old/'fitted_parameters.json',old/'oof_predictions.jsonl')})
    c.write(c.OUT/'connection022.json',result);print(c.canonical(result))
