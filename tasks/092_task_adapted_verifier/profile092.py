"""Dataset coverage, exact duplicates, and leakage audit; no new labels or exclusions."""
from collections import defaultdict,Counter
import common092 as c
def main():
    meta={r['id']:r for r in c.lines(c.OUT/'cohort.jsonl')};rows=c.lines(c.PRIVATE/'inputs.jsonl');byclaim=defaultdict(list);bypair=defaultdict(list);within=defaultdict(list)
    for r in rows:
        m=meta[r['proposition_id']];byclaim[c.digest(r['text'])].append(m);bypair[c.digest(r['text']+'\n'+r['reference'])].append(m);within[(m['sid'],c.digest(r['text']))].append(m)
    def summary(groups):
        repeated=[rr for rr in groups.values() if len(rr)>1]
        return dict(repeated_groups=len(repeated),rows_in_repeated_groups=sum(map(len,repeated)),cross_patient_groups=sum(len({r['sid'] for r in rr})>1 for rr in repeated),discordant_GT_groups=sum(len({r['GT'] for r in rr})>1 for rr in repeated))
    profile=dict(N=len(rows),patients=len({r['sid'] for r in meta.values()}),GT=dict(Counter(r['GT'] for r in meta.values())),authors=dict(Counter(r['author'] for r in meta.values())),historical_roles=dict(Counter(r['historical_role'] for r in meta.values())),exact_claim=summary(byclaim),exact_claim_reference=summary(bypair),within_patient_exact_claim=summary(within),reference_characters=dict(min=min(len(r['reference']) for r in rows),max=max(len(r['reference']) for r in rows),mean=sum(len(r['reference']) for r in rows)/len(rows)),data_anomalies={k:dict(Counter(r[k] for r in meta.values())) for k in ['initial_agreement','time_metadata_conflict','second_round_anomaly']},no_deduplication_or_GT_relabel=True)
    # If identical model inputs occur across patients, disclose whether folds separate them.
    folds=c.read(c.OUT/'folds.json');fm={s:f['fold'] for f in folds for s in f['test']};dup=[]
    for h,rr in bypair.items():
        if len({r['sid'] for r in rr})>1:dup.append(dict(input_sha256=h,ids=[r['id'] for r in rr],subjects=[r['sid'] for r in rr],folds=[fm[r['sid']] for r in rr],GT=[r['GT'] for r in rr]))
    c.put(c.OUT/'dataset_profile.json',profile);c.jsonl(c.OUT/'cross_patient_exact_input_duplicates.jsonl',dup);print(profile)
if __name__=='__main__':main()
