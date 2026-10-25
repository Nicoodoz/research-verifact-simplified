"""GT-blind patient partition and metadata-only inventory; no API."""
import pandas as pd
import subprocess
import common031 as c
def run():
    out=c.OUT/'planning_001';c.require(not out.exists(),'Planning exists');groups=c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups'];prior=c.lines(c.base.PREP/'full_rows.jsonl');old=sorted({r['subject_id'] for r in prior});dev=sorted(map(str,groups['development']));remaining=sorted(set(dev)-set(old),key=c.rank)
    c.require(len(old)==16 and len(dev)==40 and len(remaining)==24 and not set(dev)&set(map(str,groups['reserved_test'])),'Frozen grouping mismatch')
    expansion=remaining[:12];confirmation=remaining[12:];split=dict(seed='031/patient-split/v1:',order='ascending SHA256(seed + canonical patient ID), lexical ID only for impossible tie',original16=old,expansion12=expansion,confirmation12=confirmation,GT_used=False,all_patients_previously_exposed_development=True)
    # Explicit usecols: no physician labels/votes, including no in-memory retained GT column.
    path=c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv';cols=['proposition_id','subject_id','hadm_id','author_type','proposition_type','invalid','human_csv_order'];df=pd.read_csv(path,usecols=cols,dtype=str,keep_default_na=False);df=df[df.subject_id.isin(remaining)&(df.proposition_type=='claim')&(df.invalid=='False')].copy();df['role']=df.subject_id.map(lambda s:'expansion' if s in expansion else 'confirmation');metadata=df.to_dict('records')
    out.mkdir(parents=True);c.put(out/'split.json',split);c.csvwrite(out/'claim_metadata.csv',metadata);c.put(out/'counts.json',dict(new_valid_claims=len(df),by_role=df.groupby('role').size().to_dict(),by_patient=df.groupby('subject_id').size().to_dict(),prior_valid_claims=len(prior),confirmation_GT_read=False));c.put(out/'manifest.json',dict(created_utc=c.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [path,c.base.PREP/'full_rows.jsonl',c.ROOT/'outputs/003_error_analysis/patient_groups.json']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print(c.read(out/'counts.json'))
if __name__=='__main__':run()
