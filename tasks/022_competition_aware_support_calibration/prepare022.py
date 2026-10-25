"""Bind already-audited019/020 R0/R1 responses; never read reserved cases."""
from pathlib import Path
from collections import Counter
import json,subprocess
import common022 as c
from calibration022 import scores_to_z,labels,transform

def prepare():
    out=c.OUT/'preparation_001';c.require(not out.exists(),'Preparation exists')
    rows=[];deps=[c.OUT/'protocol_001.md',c.ROOT/'docs/022_竞争感知支持边界校准_任务计划.md'];seen=set();counts={}
    for name,n,reps in [('019_support_boundary_screen',650,1),('020_lambda2_patient_validation',879,2)]:
        root=c.ROOT/'outputs'/name;old=name.startswith('019');analysis=root/('selection/analysis_001' if old else 'analysis_001')
        ap=root/('selection/preparation' if old else 'new10/base_preparation_001');cp=root/('selection/cohort.csv' if old else 'new10/preparation_002/cohort.csv')
        manifest=c.read(analysis/'manifest.json')['sha256']
        normal=analysis/'normalized.jsonl';c.require(c.sha(normal)==manifest[normal.relative_to(c.ROOT).as_posix()],'Normalized output SHA')
        cc=c.csvrows(cp);c.require(len(cc)==n and len({r['proposition_id'] for r in cc})==n,'Cohort size')
        if old:
            fullpath=c.ROOT/'outputs/010_verifact_baseline_alignment/preparation_001/cohort.csv';deps.append(fullpath)
            full={r['proposition_id']:r for r in c.csvrows(fullpath)}
            c.require(set(full)=={r['proposition_id'] for r in cc},'019 vs010 IDs')
            for r in cc:
                original=full[r['proposition_id']]
                c.require(all(r[k]==original[k] for k in ('subject_id','author_type','human_gt')),'019 vs010 GT')
                r.update({k:original[k] for k in ('invalid','proposition_type')})
        c.require(not (seen&{r['proposition_id'] for r in cc}),'Cross-task overlapping claims');seen.update(r['proposition_id'] for r in cc)
        nn=c.jl(normal);byid={r['request_id']:r for r in nn};c.require(len(nn)==len(byid),'Duplicate normalized answer')
        assign=c.csvrows(ap/'assignments.csv');aa={(r['proposition_id'],int(r['repeat']),r['arm']):r for r in assign}
        c.require(len(aa)==n*reps*2,'Incomplete assignments')
        deps.extend([cp,normal,ap/'assignments.csv',analysis/'manifest.json',ap/'manifest.json'])
        for rep in range(reps):
            pp=c.csvrows(analysis/f'predictions_r{rep}.csv');pmap={p['proposition_id']:p for p in pp}
            deps.append(analysis/f'predictions_r{rep}.csv')
            for r in cc:
                pid=r['proposition_id'];ba=aa[(pid,rep,'B')];sa=aa[(pid,rep,'S')];b=byid[ba['request_id']];s=byid[sa['request_id']]
                c.require(b['status']==s['status']=='success','Unsuccessful source response')
                parsed=json.loads(s['output_text']);c.require(parsed['label_scores']==s['scores'] and parsed['verdict']==s['verdict'],'Scores not bound to actual output')
                z=scores_to_z([s['scores']]);p=pmap[pid]
                c.require(p['U0']==c.LABELS[labels(z)[0]],'Historical U0 differs')
                u2=p.get('U2',p.get('U_lambda_2'));c.require(u2==c.LABELS[labels(transform(z,'U2'))[0]],'Historical U2 differs')
                c.require(p['B']==b['verdict'] and p['V_raw']==s['verdict'],'Historical B/Vraw differs')
                c.require(r['invalid']=='False' and r['proposition_type']=='claim','Not valid claim')
                rows.append(dict(r,source=name[:3],repeat=rep,B=b['verdict'],V_raw=s['verdict'],O=p.get('O'),scores=s['scores'],scoring_request_id=sa['request_id'],baseline_request_id=ba['request_id'],scoring_body_sha256=sa['body_sha256'],normalized_source=normal.relative_to(c.ROOT).as_posix()))
        counts[name]=dict(claims=n,rounds=reps)
    patients=sorted({r['subject_id'] for r in rows},key=lambda sid:c.digest('022/fold/v1:'+sid));c.require(len(patients)==16,'Expected16 patients')
    folds={sid:i%4 for i,sid in enumerate(patients)}
    for r in rows:r['fold']=folds[r['subject_id']]
    c.require(len(rows)==2408 and len(seen)==1529,'Expected complete distinct and repeated denominator')
    out.mkdir(parents=True);c.lines(out/'rows.jsonl',rows);c.write(out/'folds.json',folds)
    c.csvwrite(out/'cohort.csv',[{k:v for k,v in r.items() if k not in ('scores',)} for r in rows if r['repeat']==0])
    c.write(out/'summary.json',dict(unique_claims=1529,score_observations=2408,patients=16,training_observations=1529,R1_only_for_evaluation=879,by_task=counts,by_author=dict(Counter(r['author_type'] for r in rows if r['repeat']==0)),new_API_calls=0,cost_cny=0))
    c.write(out/'origin.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),plan_sha256=c.sha(deps[1])))
    c.seal(out,deps,[Path(__file__),c.TASK/'common022.py',c.TASK/'calibration022.py'])
    print(c.canonical(c.read(out/'summary.json')))

if __name__=='__main__':prepare()
