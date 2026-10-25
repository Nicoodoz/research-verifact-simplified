"""Metadata-only reserved inventory; no physician GT projected/read."""
import pandas as pd
import subprocess
import common036 as c
def main():
    out=c.OUT/'planning_001';c.require(not out.exists(),'Planning exists')
    groups=c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups'];ids=set(map(str,groups['reserved_test']))
    assert len(ids)==40 and ids.isdisjoint(map(str,groups['development']))
    path=c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv'
    cols=['proposition_id','subject_id','hadm_id','author_type','proposition_type','invalid','human_csv_order']
    df=pd.read_csv(path,usecols=cols,dtype=str,keep_default_na=False);df=df[df.subject_id.isin(ids)&(df.proposition_type=='claim')&(df.invalid=='False')].copy();df['role']='reserved'
    assert set(df.subject_id)==ids and not df.proposition_id.duplicated().any()
    c.csvwrite(out/'claim_metadata.csv',df.to_dict('records'));c.put(out/'counts.json',dict(n=len(df),patients=sorted(ids),by_patient=df.groupby('subject_id').size().to_dict(),by_author=df.groupby('author_type').size().to_dict(),GT_read=False))
    c.put(out/'manifest.json',dict(created_utc=c.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source=str(path.relative_to(c.ROOT)),source_sha256=c.sha(path),metadata_sha256=c.sha(out/'claim_metadata.csv')))
    print(c.read(out/'counts.json'))
if __name__=='__main__':main()
