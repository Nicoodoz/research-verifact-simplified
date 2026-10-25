"""Reproduce main metrics, paired intervals and R1 fit from public artifacts only."""
import sys,socket
from unittest.mock import patch
import common096 as c
from bounded_fit096 import fit_g
from calibration096 import decode
sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import evaluate,paired_compare
BACKEND='valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k';O=c.OUT/BACKEND
def main():
    checks=[]
    def ok(name,value):assert value,name;checks.append(name)
    rr=c.lines(O/'unified_predictions.jsonl');metrics=c.read(O/'main_metrics.json');pairs=c.read(O/'paired_bootstrap.json');model=c.read(O/'R1_calibration_model.json');native=c.lines(O/'R1_parsed_predictions.jsonl');labels={r['id']:r for r in c.lines(c.OUT/'calibration_manifest.jsonl')}
    cal=[dict(id=r['id'],GT=labels[r['id']]['GT'],scores=r['label_scores']) for r in native if r['stage']=='calibration' and r['core_valid']];fitted,check=fit_g(cal)
    ok('R1theta public replay',fitted['theta']==model['R1_model']['theta'] and abs(fitted['objective']-model['R1_model']['objective'])<1e-12)
    for panel in ['natural','diagnostic']:
        rows=[r for r in rr if r['panel']==panel]
        for scope in ['raw_common','all_methods_common']:
            valid=rows if scope=='raw_common' else [r for r in rows if r['B_core_valid'] and r['R1_core_valid']]
            cohort=[dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in valid]
            for name,v in metrics[panel][scope].items():
                z=evaluate(cohort,[dict(proposition_id=r['id'],verdict=r['predictions'][name]) for r in valid],profile='none')
                ok('metrics '+panel+scope+name,all(abs(v[a]-z[b])<1e-12 for a,b in [('PA','percent_agreement'),('MCC','mcc'),('AC1','gwet_ac1')]) and v['confusion_matrix']==z['confusion_matrix'])
        for key,v in pairs[panel].items():
            a=v['base'];b=v['candidate'];valid=[r for r in rows if r['predictions'].get(a) in c.LABELS and r['predictions'].get(b) in c.LABELS];cohort=[dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in valid]
            z=paired_compare(cohort,[dict(proposition_id=r['id'],verdict=r['predictions'][a]) for r in valid],[dict(proposition_id=r['id'],verdict=r['predictions'][b]) for r in valid],iterations=1000)
            ok('paired bootstrap '+panel+key,z==v['official_paired_compare'])
    c.put(O/'public_replay_verification.json',dict(status='PASS',checks=checks,private_files_read=False,network_calls=0,independent_audit=False,scope='public scores/labels/predictions sufficient for R1 fit and reported point/paired metrics; original clinical input identity requires private receipt replay'))
    print('PUBLIC_REPLAY_PASS',len(checks))
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Public replay has no network')):main()
