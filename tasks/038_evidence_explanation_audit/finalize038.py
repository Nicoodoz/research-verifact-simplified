from pathlib import Path
import hashlib, json, datetime

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/038_evidence_explanation_audit"
TASK=ROOT/"tasks/038_evidence_explanation_audit"

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

attempts=sorted((OUT/"attempts").glob("*/*.json"))
key_outputs=[
    OUT/"report.md", OUT/"CURRENT_STATUS.md", OUT/"audit_handoff.md",
    OUT/"planning_001/preflight.json", OUT/"planning_001/blind_cohort.csv",
    OUT/"planning_001/evaluation_key.csv", OUT/"planning_001/jobs.jsonl",
    OUT/"analysis_001/evidence_cases.csv", OUT/"analysis_001/evidence_summary.csv",
    OUT/"analysis_001/reason_alignment.csv", OUT/"analysis_001/key_results.json",
    OUT/"analysis_001/spotcheck_cases.csv", OUT/"verification_001.json",
]
code=sorted(TASK.glob("*.py"))+[TASK/"protocol.md",TASK/"README.md"]
source=[
    ROOT/"outputs/036_final_validation/analysis_001/R0/predictions.csv",
    ROOT/"outputs/036_final_validation/judge_inputs_001/jobs.jsonl",
    ROOT/"outputs/036_final_validation/predictions_blind_001/normalized.jsonl",
]
obj={
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "attempt_json_count":len(attempts),
 "attempts_combined_sha256":hashlib.sha256("".join(sha(p) for p in attempts).encode()).hexdigest(),
 "sources":{str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in source},
 "code":{str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in code if p.exists()},
 "key_outputs":{str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in key_outputs if p.exists()},
}
(OUT/"manifest.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("038 manifest",len(attempts),"attempt json")
