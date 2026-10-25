"""Freeze only the selected 072 candidate on untouched confirmation patients."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
sys.path.insert(0, str(Path(__file__).parent))
import prepare072 as p72  # noqa: E402
import run072  # noqa: E402


def main():
    selected = run072.read(OUT / "pilot_decision.json")
    arm = selected["selected_arm"]
    assert arm in ("F4", "S6", "D4")
    assert selected["stage"] == "pilot_selection" and selected["confirmation_not_inspected"] is True
    assert not (OUT / "confirmation_jobs.jsonl").exists()
    frozen = run072.check_frozen("pilot")
    blind = [x for x in run072.lines(OUT / "target_blind.jsonl") if x["sid"] in frozen["confirmation_patients"]]
    assert len(blind) == 60
    pool = run072.lines(OUT / "example_pool.jsonl")
    by_pool = {x["proposition_id"]: x for x in pool}
    old = {(j["id"], j["arm"]): j for j in run072.lines(ROOT / "outputs/071_judge_icl_feasibility/main_jobs.jsonl")}
    pilot = {(j["id"], j["arm"]): j for j in run072.lines(OUT / "pilot_jobs.jsonl")}
    anchor_id = next(j["id"] for j in pilot.values() if j["arm"] == "S6")
    static_append = pilot[(anchor_id, "S6")]["body"]["messages"][0]["content"][len(pilot[(anchor_id, "F4")]["body"]["messages"][0]["content"]):]
    assert "Two additional examples" in static_append
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]+\b")
    matrix = vectorizer.fit_transform([x["claim"] for x in pool])
    suffix_prefix = "\n\n## Clinician-labeled examples from four other patients\nEach example contains a proposition, EHR reference, and physician label. Examples are not evidence about the patient in the actual task. For the actual task use only its supplied reference.\n"
    jobs, selections = [], []
    for target in blind:
        pid = target["id"]
        base = old[(pid, "B")]["body"]
        fixed = old[(pid, "E")]["body"]
        bodies = {"B": base, "F4": fixed}
        if arm == "S6":
            body = copy.deepcopy(fixed)
            body["messages"][0]["content"] += static_append
            bodies["S6"] = body
        elif arm == "D4":
            chosen = p72.select_dynamic(target, pool, matrix, vectorizer, None)
            body = copy.deepcopy(base)
            body["messages"][0]["content"] += suffix_prefix + "\n".join(p72.canonical({
                "proposition": by_pool[item["proposition_id"]]["claim"],
                "reference": by_pool[item["proposition_id"]]["reference"],
                "physician_label": item["label"]}) for item in chosen) + "\n"
            bodies["D4"] = body
            selections.append({"id": pid, "sid": target["sid"], "selected": chosen})
        for this_arm, body in bodies.items():
            assert body["messages"][-1]["content"] == base["messages"][-1]["content"]
            assert body["model"] == "deepseek-v4-flash-0731" and body["reasoning_effort"] == "high"
            jobs.append({"request_id": "072_confirmation_" + this_arm + "_" + hashlib.sha256(pid.encode()).hexdigest()[:24],
                         "stage": "confirmation", "id": pid, "sid": target["sid"], "arm": this_arm,
                         "body": body, "body_sha256": p72.digest(body)})
    jobs.sort(key=lambda j: hashlib.sha256(("072/confirmjob/v1:" + j["id"] + j["arm"]).encode()).hexdigest())
    p72.write_lines(OUT / "confirmation_jobs.jsonl", jobs)
    if selections:
        p72.write_lines(OUT / "confirmation_dynamic_selections.jsonl", selections)
    decision_file = selected["decision_file"]
    assert decision_file == "pilot_decision.md" and (OUT / decision_file).exists()
    confirmation_freeze = {
        "stage": "confirmation", "selected_arm": arm, "arms": sorted({j["arm"] for j in jobs}),
        "confirmation_n": len(blind), "confirmation_patients": frozen["confirmation_patients"],
        "jobs_n": len(jobs), "source_freeze_sha256": run072.sha(OUT / "freeze.json"),
        "decision_file": decision_file, "decision_sha256": run072.sha(OUT / decision_file),
        "jobs_sha256": run072.sha(OUT / "confirmation_jobs.jsonl"),
        "pool_sha256": run072.sha(OUT / "example_pool.jsonl"),
        "dynamic_selections_sha256": run072.sha(OUT / "confirmation_dynamic_selections.jsonl") if selections else None,
    }
    p72.write(OUT / "confirmation_freeze.json", confirmation_freeze)
    print(json.dumps({"selected_arm": arm, "confirmation_n": len(blind), "jobs": len(jobs),
                      "arms": confirmation_freeze["arms"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
