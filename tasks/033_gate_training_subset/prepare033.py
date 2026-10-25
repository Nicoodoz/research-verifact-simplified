"""Freeze study partition and body-free development inputs before subset ranking."""
import subprocess
import common033 as s

def main():
    s.require(not s.PREP.exists(),'Preparation already exists');s.old.verify();split=s.read(s.P31/'planning_001/split.json');prior=s.lines(s.old.PREP/'full_rows.jsonl');oldf={r['proposition_id']:r for r in s.lines(s.old.PREP/'features.jsonl')};later=s.lines(s.P31/'features_001/rows.jsonl');trainlabels=s.ROOT/'outputs/032_evidence_relation_correction/preparation_001/training_labels.jsonl';labelmanifest=s.read(trainlabels.parent/'manifest.json');s.require(s.sha(trainlabels)==labelmanifest['files'][trainlabels.name],'032 training labels changed');gt={r['proposition_id']:r['human_gt'] for r in s.lines(trainlabels)};rows=[]
    for r in prior:
        q={k:r[k] for k in ('proposition_id','subject_id','author_type','scores','u0','u2','candidate','human_gt')};q.update(group=r['group'],partition='original16',features=oldf[r['proposition_id']]['features'] if r['candidate'] else None);rows.append(q)
    for r in later:
        q={k:r[k] for k in ('proposition_id','subject_id','author_type','scores','u0','u2','candidate')};q.update(group='031_'+r['group'],partition=r['group'],human_gt=gt[r['proposition_id']] if r['group']=='expansion' else None,features=r['features']['D'] if r['candidate'] else None);rows.append(q)
    s.require(len(rows)==3675 and len({r['proposition_id'] for r in rows})==3675,'Full development identity');s.require(sum(r['candidate'] for r in rows)==370,'All frozen candidates');s.require(all(r['features'] is not None for r in rows if r['candidate']),'Missing candidate features');s.require(all(r['human_gt'] is None for r in rows if r['partition']=='confirmation'),'Selection GT isolation')
    s.PREP.mkdir(parents=True);s.jsonl(s.PREP/'rows_selection_blind.jsonl',rows);s.put(s.PREP/'split.json',split);s.put(s.PREP/'config.json',s.read(s.TASK/'config.json'));s.put(s.PREP/'environment.json',s.c.environment());(s.PREP/'protocol.md').write_bytes((s.TASK/'protocol.md').read_bytes());sources=[s.old.PREP/'manifest.json',s.HIST/'manifest.json',s.HIST/'model_index.json',s.HIST/'unit_metrics.csv',s.P31/'features_001/rows.jsonl',s.P31/'planning_001/split.json',s.P31/'before_models/A.json',trainlabels,s.c.PREP/'config.json']
    s.put(s.PREP/'manifest.json',dict(created_utc=s.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),sources={p.relative_to(s.ROOT).as_posix():s.sha(p) for p in sources},files={p.name:s.sha(p) for p in s.PREP.iterdir() if p.is_file()},code={p.name:s.sha(p) for p in s.TASK.glob('*.py')},reserved_used=False,confirmation_GT_unread_for_new_selection=True))
    s.status('prepared',state='ready',rows=len(rows),candidates=370)

if __name__=='__main__':main()
