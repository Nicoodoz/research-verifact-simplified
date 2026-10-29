"""Focused paired uncertainty and strata after a larger-development signal."""
from pathlib import Path
import sys,argparse
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics
sys.path.insert(0,str(R/'tasks/110_update_interpolation'));from analyze110 import changes
sys.path.insert(0,str(R/'tasks/107_support_aux'));from evaluate107 import risk_deltas
sys.path.insert(0,str(R/'src'));from verifact_research.evaluation import paired_compare
from sklearn.metrics import matthews_corrcoef,accuracy_score
P=R/'.local_models/116_research_cycle';O=R/'outputs/116_research_cycle'

def compact(rows):
    scores={arm:metrics(rows,{r['id']:r['pred'][arm] for r in rows}) for arm in ['base','candidate']}
    for arm,score in scores.items():
        truth=[r['GT'] for r in rows];pred=[r['pred'][arm] for r in rows]
        assert abs(matthews_corrcoef(truth,pred)-score['mcc'])<1e-10 and abs(accuracy_score(truth,pred)-score['percent_agreement'])<1e-10
    delta=changes(rows,'base','candidate')
    avoided=[r for r in rows if r['GT']!='Supported' and r['pred']['base']=='Supported' and r['pred']['candidate']!='Supported']
    delta.update(false_S_avoided_but_still_wrong=sum(r['pred']['candidate']!=r['GT'] for r in avoided),NA_S_to_NS=sum(r['GT']=='Not Addressed' and r['pred']['candidate']=='Not Supported' for r in avoided))
    return dict(N=len(rows),scores=scores,changes=delta)

def main(name):
    data=c.rows(O/(name+'_predictions.jsonl'));keys={r['id']:r for r in c.rows(P/'keys_selection1817.jsonl')}
    base={r['id']:r for r in c.rows(P/'baseline107_selection1817.jsonl')}
    rows=[dict(keys[r['id']],tokens=base[r['id']]['input_tokens'],pred={'base':r['baseline107'],'candidate':r['verdict']}) for r in data if r['valid']]
    groups={'natural':[r for r in rows if r['old_panel']=='natural'],'pressure':[r for r in rows if r['old_panel']=='pressure']}
    if len(rows)==1817:groups.update(selection1817=rows,new1317=[r for r in rows if r['subset']=='new'])
    sections={}
    for label,part in groups.items():
        s=compact(part);s['authors']={a:compact([r for r in part if r['author']==a]) for a in sorted({r['author'] for r in part})}
        ordered=sorted(part,key=lambda r:(r['tokens'],r['id']));n=len(ordered)
        s['length_quartiles']={str(k+1):compact(ordered[k*n//4:(k+1)*n//4]) for k in range(4) if (k+1)*n//4>k*n//4}
        s['patients']=[dict(sid=sid,**compact([r for r in part if r['sid']==sid])) for sid in sorted({r['sid'] for r in part})]
        cohort=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in part]
        pred=lambda arm:[dict(proposition_id=r['id'],verdict=r['pred'][arm]) for r in part]
        s['patient_paired']=paired_compare(cohort,pred('base'),pred('candidate'),iterations=1000)
        s['risk_CI']=risk_deltas(part,'base','candidate');sections[label]=s
    c.put(O/(name+'_strata.json'),dict(job=name,sections=sections,bootstrap_iterations=1000,length_bins='within-panel token-rank quartiles; no outcome-dependent boundaries',no_confirmatory_claim_from_development=True,independent_sklearn_metrics_match=True))
    print(c.canonical(dict(job=name,panels=list(sections),bootstrap_iterations=1000)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('job');main(p.parse_args().job)
