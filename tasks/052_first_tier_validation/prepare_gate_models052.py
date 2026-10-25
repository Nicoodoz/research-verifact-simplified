"""Freeze patient-out Gate A model mapping from already saved 033 OOF models; no refit/no API."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c

def main():
    eval_patients=c.read(c.OUT/"sample_freeze.json")["evaluation_patients"]
    bindings=c.read(ROOT/"outputs/033_gate_training_subset/evaluation_001/OOF_model_bindings.json")
    usage=c.read(ROOT/"outputs/033_gate_training_subset/evaluation_001/model_usage.json")["used_models"]
    all40=c.read(ROOT/"outputs/033_gate_training_subset/recommendation_001/gate_A_all40.json")
    out={}
    for sid in eval_patients:
        if sid=="15057":
            # 15057 contributed no historical candidate rows; full all40 fit already excludes it effectively.
            source=ROOT/"outputs/033_gate_training_subset/recommendation_001/gate_A_all40.json"
            model=all40
            c.require("15057" not in model["final_fit"]["training_patients"],"15057 unexpectedly in fitted candidates")
            out[sid]=dict(model_id=model["model_id"],source=source.relative_to(ROOT).as_posix(),sha256=c.sha(source),
              threshold=model["threshold"],training_patients=model["final_fit"]["training_patients"],special_no_candidate_patient=True)
            continue
        rr=[r for r in bindings if r.get("configuration")=="A_all40" and r.get("held_patient")==sid]
        c.require(len(rr)==1 and rr[0].get("model_id"),"missing OOF Gate A binding "+sid)
        mid=rr[0]["model_id"];u=usage[mid];source=ROOT/u["path"];model=c.read(source)
        c.require(sid not in model["final_fit"]["training_patients"],"Gate patient leakage "+sid)
        c.require(model["threshold"]==u["threshold"],"threshold binding")
        out[sid]=dict(model_id=mid,source=source.relative_to(ROOT).as_posix(),sha256=c.sha(source),
          threshold=model["threshold"],training_patients=model["final_fit"]["training_patients"],special_no_candidate_patient=False)
    c.put(c.OUT/"gate_patient_out_mapping.json",dict(created_utc=c.now(),method="A_all40 patient-out OOF models from 033",
      evaluation_patients=eval_patients,models=out,
      bindings_sha256=c.sha(ROOT/"outputs/033_gate_training_subset/evaluation_001/OOF_model_bindings.json"),
      usage_sha256=c.sha(ROOT/"outputs/033_gate_training_subset/evaluation_001/model_usage.json")))
    print("052 GATE MAPPING",len(out),flush=True)
if __name__=="__main__":main()
