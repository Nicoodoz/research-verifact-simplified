"""Finalize frozen 052 main jobs using empirical cost forecast before any API call."""
from pathlib import Path
from collections import Counter
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c
def main():
    c.require(not (c.OUT/"attempts").exists() or not any((c.OUT/"attempts").iterdir()),"API attempts already exist")
    jobs=c.lines(c.OUT/"main_jobs.jsonl");c.require(len(jobs)==1008,"job count")
    counts=Counter(j["condition"] for j in jobs)
    # Exact condition-specific per-call means from 051's 96-case confirmation.
    means={"N-S":0.01271196875,"N-V":0.01191134375,"T-S":0.02810721875,"T-V":0.025121}
    central=0.0
    for cond,n in counts.items():
        base=cond.replace("_repeat","");central+=n*means[base]
    q_mean=6.013760999999999/342  # 036 candidate-only Qwen observed mean at same price schedule
    q_stress_calls=60  # 25% of 240
    q_stress=q_stress_calls*q_mean
    stress=(central+q_stress)*1.5+5
    c.require(stress<=c.CAP,"reasonable forecast exceeds80")
    c.put(c.OUT/"main_freeze.json",dict(created_utc=c.now(),cases=240,jobs=len(jobs),repeat_n=12,
      condition_counts=dict(counts),full_max_token_envelope_cny=sum(c.bound(j) for j in jobs),
      empirical_deepseek_central_cny=central,qwen_stress_calls=q_stress_calls,qwen_historical_mean_cny=q_mean,
      qwen_stress_cny=q_stress,central_plus50pct_plus5_cny=stress,task_cap_cny=c.CAP,
      no_unconditional_full_max_guarantee=True,api_calls_before_freeze=0,GT_used_for_jobs=False,
      jobs_sha256=c.sha(c.OUT/"main_jobs.jsonl"),sample_sha256=c.sha(c.OUT/"sample_blind.jsonl"),
      calibration_sha256=c.sha(c.OUT/"calibration_models.json"),gate_mapping_sha256=c.sha(c.OUT/"gate_patient_out_mapping.json"),
      protocol_sha256_at_sample_freeze=c.read(c.OUT/"sample_freeze.json")["sources"]["protocol"],
      budget_amendment_sha256=c.sha(c.OUT/"budget_amendment_001.json")))
    print("052 MAIN FREEZE",dict(jobs=len(jobs),central=round(central,3),stress=round(stress,3),cap=c.CAP),flush=True)
if __name__=="__main__":main()
