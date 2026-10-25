"""Check frozen source alignment and seal before any 029 real-data fitting."""
import subprocess
import common029 as c

def run():
    c.offline();c.require(not c.PREP.exists(),'Preparation exists; never overwrite')
    c.require('research-verifact-029' in c.environment()['executable'].lower(),'Use dedicated 029 environment')
    o=c.ROOT/'outputs';p28=o/'028_traceable_claim_evidence_verification';p27=o/'027_dual_judge_transfer_diagnosis'
    paths=[p28/'analysis_001/predictions.csv',p28/'analysis_001/normalized.jsonl',p27/'analysis_002/candidates.json',p27/'analysis_002/conflicts.json',o/'025_lambda_flip_risk_separability/preparation_001/rows.jsonl',o/'026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl']
    # Validate audited source output fingerprints, including all core upstream source hashes.
    for base,folder in [(p28,'analysis_001'),(p27,'analysis_002')]:
        mp=base/folder/'manifest.json';manifest=c.read(mp);paths.append(mp)
        for rel,h in manifest.get('outputs',{}).items():c.require(c.sha(base/folder/rel)==h,'Audited output modified '+rel)
    mp=p28/'preparation_001/manifest.json';paths.append(mp)
    for rel,h in c.read(mp)['sha256'].items():
        c.require(c.sha(c.ROOT/rel)==h,'028 frozen claim/reference/prompt source changed '+rel)
    paths.append(p28/'preparation_001/materials.jsonl')
    norm=c.lines(paths[1]);c.require(len(norm)==310,'028 outputs count');outputs={(r['proposition_id'],r['arm']):r for r in norm};c.require(len(outputs)==310,'Duplicate 028 output')
    candidates=c.read(paths[2]);byid={r['proposition_id']:r for r in candidates};c.require(len(candidates)==len(byid)==155,'Candidate IDs')
    old={r['proposition_id']:r for r in c.lines(paths[4]) if r['group']=='024_D'}
    ns={r['proposition_id']:r['scores'] for r in c.lines(paths[5]) if r['model_key']=='deepseek' and r['arm']=='S'}
    full=c.csvread(paths[0]);c.require(len(full)==len({r['proposition_id'] for r in full})==1529,'Full identities')
    rows=[];training=[];counts={}
    for x in full:
        pid=x['proposition_id'];sc=old[pid]['scores'] if x['group']=='025' else ns[pid];u0=int(c.old.decode(c.old.logs(sc),0));u2=int(c.old.decode(c.old.logs(sc),2));is_candidate=u0!=0 and u2==0
        c.require(c.LABELS[u0]==x['U0'] and c.LABELS[u2]==x['U2'],'Frozen U0/U2 mismatch')
        row=dict(proposition_id=pid,subject_id=x['subject_id'],author_type=x['author_type'],human_gt=x['GT'],group=x['group'],scores=sc,u0=u0,u2=u2,candidate=is_candidate,SD=c.LABELS.index(x['SD']),repeat=c.LABELS.index(x['repeat']),trace=c.LABELS.index(x['trace']))
        c.require(is_candidate==(pid in byid),'Candidate selection mismatch')
        if is_candidate:
            h=byid[pid];c.require((h['group'],h['subject_id'],h['GT'],h['D_scores'])==(x['group'],x['subject_id'],x['GT'],sc),'Candidate metadata mismatch')
            row['SD_probability']=h['SD']
            f=c.score_features(sc,h['Q_scores']);c.require(all(abs(f[k]-h['features'][k])<1e-12 for k in c.SCORE),'Original SD features differ')
            f.update(c.new_features(outputs[pid,'repeat'],outputs[pid,'trace']));c.require(all(c.np.isfinite(v) for v in f.values()),'Nonfinite feature')
            training.append(dict(proposition_id=pid,subject_id=x['subject_id'],author_type=x['author_type'],human_gt=x['GT'],group=x['group'],features=f,kind=h['kind']))
        rows.append(row)
    groups={g:sorted({r['subject_id'] for r in rows if r['group']==g}) for g in ('025','026')}
    c.require(set(groups['025']).isdisjoint(groups['026']),'Cohort patient overlap')
    splitpath=o/'003_error_analysis/patient_groups.json';paths.append(splitpath);split=c.read(splitpath)['groups'];patient_ids={r['subject_id'] for r in rows}
    c.require(patient_ids.issubset({str(v) for v in split['development']}) and patient_ids.isdisjoint({str(v) for v in split['reserved_test']}),'Development-only boundary')
    for g,n,k,pat in [('025',879,103,10),('026',650,52,6)]:
        rr=[r for r in rows if r['group']==g];cc=[r for r in training if r['group']==g]
        c.require(len(rr)==n and len(cc)==k and len(groups[g])==pat,'Frozen scope mismatch')
        counts[g]=dict(claims=len(rr),candidates=len(cc),patients=groups[g],candidate_patients=sorted({r['subject_id'] for r in cc}))
    conflicts=c.read(paths[3])
    for g in ('025','026'):
        for group in conflicts[g]['mixed_groups']:
            rs=[byid[p] for p in group['ids']];c.require(len({tuple(r['features'][n] for n in c.SCORE) for r in rs})==1,'Conflict feature equality');c.require(len({r['GT']=='Supported' for r in rs})==2,'Conflict is not mixed')
    c.PREP.mkdir(parents=True)
    c.jsonl(c.PREP/'full_rows.jsonl',rows);c.jsonl(c.PREP/'features.jsonl',training);c.put(c.PREP/'conflicts.json',conflicts);c.put(c.PREP/'cohort_summary.json',counts)
    c.put(c.PREP/'feature_schema.json',c.schema());c.put(c.PREP/'config.json',c.read(c.TASK/'config.json'));c.put(c.PREP/'environment.json',c.environment())
    subjects=sorted({r['subject_id'] for r in rows});c.put(c.PREP/'outer_folds.json',[dict(test_patient=s,training_patients=[t for t in subjects if t!=s],test_candidate_ids=[r['proposition_id'] for r in training if r['subject_id']==s]) for s in subjects])
    c.write_text(c.PREP/'protocol.md',(c.TASK/'protocol.md').read_text(encoding='utf-8'))
    code=list(c.TASK.glob('*.py'))+list(c.TASK.glob('*.ps1'))+[c.TASK/'config.json',c.TASK/'protocol.md',c.ROOT/'tasks/025_lambda_flip_risk_separability/common025.py',c.ROOT/'tasks/025_lambda_flip_risk_separability/frontier025_numeric.py',c.ROOT/'tasks/022_competition_aware_support_calibration/common022.py']+list((c.ROOT/'src/verifact_research/evaluation').glob('*.py'))
    c.put(c.PREP/'manifest.json',dict(created_utc=c.now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in c.PREP.iterdir() if p.is_file()},code={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in code},API_calls=0,real_029_fits_before_freeze=0))
    print('Frozen: 1529 claims / 16 patients; 155 candidates / 15 candidate-bearing patients. No models fitted.')
if __name__=='__main__':run()
