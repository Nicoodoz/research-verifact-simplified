"""Correct boolean leave-one-patient-out weight arithmetic; no model/threshold change."""
import common025 as c
def run():
    old=c.TASK/'frontier025.py';new=c.TASK/'frontier025_numeric.py'
    s=old.read_text(encoding='utf-8');c.require(s.count('np.asarray(weights)')==1,'Count patch target differs')
    with new.open('x',encoding='utf-8',newline='\n') as f:f.write(s.replace('np.asarray(weights)','np.asarray(weights,dtype=float)'))
    original=c.TASK/'analyze025_fixed.py';target=c.TASK/'analyze025_numeric.py'
    s=original.read_text(encoding='utf-8').replace('import frontier025 as f','import frontier025_numeric as f').replace("c.OUT/'analysis_002'","c.OUT/'analysis_003'")
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
    c.write(c.OUT/'count_repair_001.json',dict(reason='Boolean numpy matrix multiplication returned logical any rather than sum for leave-one-patient-out masks; convert weights to float before counting',affected='leave_one_patient_out and associated gate check only; ordinary and bootstrap weights already numeric',model_feature_threshold_lambda_changes=False,source_hashes={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in (old,new,original,target)},formal_run='analysis_003',prior_runs_preserved=['analysis_001','analysis_002']))
if __name__=='__main__':run()
