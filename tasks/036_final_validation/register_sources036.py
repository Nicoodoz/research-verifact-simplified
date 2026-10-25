"""Hash historical published baselines before the first reserved evaluation."""
import common036 as c
def main():
    path=c.OUT/'published_baseline_sources_001.json';assert not path.exists() and not (c.OUT/'analysis_001').exists()
    files=[c.ROOT/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv' for author in ('human','llm')]
    files+=[c.ROOT/'outputs/003_error_analysis/patient_groups.json',c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv']
    c.put(path,dict(created_utc=c.now(),sha256={str(p.relative_to(c.ROOT)):c.sha(p) for p in files},values_read=False,operation='Byte hashing only; no reserved verdict/GT analysis',release_baseline='R1-70B,100 sentence facts,rerank,absolute_time,current admission,deduplicate=True'))
    print('Published baseline/group/master input bytes bound before reserved evaluation; no labels projected.')
if __name__=='__main__':main()
