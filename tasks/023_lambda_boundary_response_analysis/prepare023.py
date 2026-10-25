"""Anchor gate against audited019/020 before any response curves exist."""
from pathlib import Path
import subprocess
import common023 as c

def prepare():
    out=c.OUT/'preparation_001';c.require(not out.exists(),'Preparation exists')
    old=c.ROOT/'outputs/022_competition_aware_support_calibration/preparation_001';c.check(old)
    original=c.jl(old/'rows.jsonl');c.require(len(original)==2408,'Expected2408 scoring observations')
    rows=[{k:r[k] for k in ('proposition_id','subject_id','author_type','human_gt','source','repeat','scores','B','V_raw','O','scoring_request_id','scoring_body_sha256','normalized_source','invalid','proposition_type')} for r in original]
    c.require(len({(r['proposition_id'],r['repeat']) for r in rows})==2408 and len({r['proposition_id'] for r in rows})==1529,'Duplicate observation')
    c.require(all(r['invalid']=='False' and r['proposition_type']=='claim' for r in rows),'Not valid claim')
    normal={p:{r['request_id']:r for r in c.jl(c.ROOT/p)} for p in {r['normalized_source'] for r in rows}}
    for r in rows:c.require(normal[r['normalized_source']][r['scoring_request_id']]['scores']==r['scores'],'Scoring source differs')
    deps=[old/'manifest.json',old/'rows.jsonl',c.OUT/'protocol_001.md'];checks=[]
    for group,size,patients in [('019',650,6),('020_R0',879,10),('020_R1',879,10)]:
        rr=c.subset(rows,group);c.require(len(rr)==size and len({r['subject_id'] for r in rr})==patients,'Cohort extent')
        base=c.ROOT/'outputs'/('019_support_boundary_screen/selection/analysis_001' if group=='019' else '020_lambda2_patient_validation/analysis_001')
        rep=1 if group=='020_R1' else 0;ppath=base/f'predictions_r{rep}.csv';mpath=base/'metrics.json';man=base/'manifest.json'
        recorded=c.read(man)['sha256']
        for p in (ppath,mpath):c.require(c.sha(p)==recorded[p.relative_to(c.ROOT).as_posix()],'Historical result changed');deps.append(p)
        deps.append(man);pp=c.csvrows(ppath);byid={r['proposition_id']:r for r in pp};metrics=c.read(mpath)
        c.require(len(pp)==len(byid)==size and set(byid)=={r['proposition_id'] for r in rr},'Anchor IDs')
        z=c.logs([r['scores'] for r in rr])
        for lam in c.ANCHORS if group=='019' else [0,2]:
            arm='U0' if lam==0 else f'U_lambda_{lam:g}' if group=='019' else 'U2';pred=c.decode(z,lam)
            c.require(all(byid[r['proposition_id']][arm]==c.LABELS[pred[i]] for i,r in enumerate(rr)),'Anchor label mismatch')
            for author in ('all','human','llm'):
                ix=[i for i,r in enumerate(rr) if author=='all' or r['author_type']==author];cc=[rr[i] for i in ix]
                m=c.evaluate(cc,c.prediction(cc,pred[ix]),profile='none',missing='error');historical=metrics[f'r{rep}/{author}/{arm}']
                for field in ('n','confusion_matrix','percent_agreement','mcc','gwet_ac1','per_class'):c.require(m[field]==historical[field],'Anchor metric mismatch: '+group+'/'+arm+'/'+author+'/'+field)
                checks.append(dict(group=group,author=author,lambda_value=lam,n=len(ix),arm=arm,labels_exact=True,metrics_exact=True))
    out.mkdir(parents=True);c.lines(out/'scores.jsonl',rows);c.csvwrite(out/'cohort.csv',[{k:v for k,v in r.items() if k!='scores'} for r in rows]);c.write(out/'anchor_checks.json',checks)
    c.write(out/'source_manifest.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),scoring_observations=2408,unique_claims=1529,patients=16,all_anchor_checks_pass=True,new_API_calls=0,cost_cny=0,fixed_lambda=2,source='audited019/020 via audited022 alignment'))
    c.seal(out,deps,[Path(__file__),c.TASK/'common023.py']);print('PASS:',len(checks),'author/anchor metric checks; all historical labels exact.')

if __name__=='__main__':prepare()
