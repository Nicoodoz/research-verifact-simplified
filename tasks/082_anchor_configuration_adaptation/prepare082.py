"""Freeze GT-blind 082 screen/evaluation/repeat IDs and exact Judge bodies."""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import inventory082 as i

ROOT, OUT = i.ROOT, i.OUT
OLD_F4_JOBS = "outputs/079_f4_priorg_adaptation/main_jobs.jsonl"


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stable(prefix, value):
    return hashlib.sha256((prefix + str(value)).encode()).hexdigest()


def write(name, data):
    path = OUT / name
    with path.open("x", encoding="utf-8", newline="\n") as f:
        if isinstance(data, list):
            for row in data:
                f.write(canonical(row) + "\n")
        else:
            f.write(canonical(data) + "\n")


def score_body(template, claim, reference):
    body = copy.deepcopy(template)
    body["messages"][1]["content"] = json.dumps({"proposition": claim, "reference": reference},
                                                     ensure_ascii=False, separators=(",", ":"))
    assert body["model"] == "deepseek-v4-flash-0731" and body["enable_thinking"] is True
    assert body["reasoning_effort"] == "high" and body["max_tokens"] == 8192
    return body


def job(pid, sid, arm, stage, body):
    return {"request_id": f"082_{stage}_{arm}_{pid}", "id": pid, "sid": sid,
            "arm": arm, "stage": stage, "body": body, "body_sha256": digest(body),
            "scored": True, "thinking": True}


def main():
    OUT.mkdir(exist_ok=False)
    q = i.load()
    train_patients = sorted(q["train_patients"])
    by_train = defaultdict(list)
    for x in q["train_pool"]:
        by_train[x["subject_id"]].append(x)
    screen, train_manifest = [], []
    for sid in train_patients:
        pool = sorted(by_train[sid], key=lambda x: (stable("082/screen/v1:", x["proposition_id"]), x["proposition_id"]))
        assert len(pool) >= 30
        for rank, x in enumerate(pool[:30], 1):
            row = {"id": x["proposition_id"], "sid": sid, "author": x["author_type"],
                   "claim": x["text"], "reference": x["reference"],
                   "role": x["role"], "rank": rank, "is_R": rank <= 22,
                   "is_E_core": rank <= 17, "historical_mechanism_exposure": q["exposed"].get(x["proposition_id"], [])}
            screen.append(row)
            train_manifest.append({k: v for k, v in row.items() if k not in ("claim", "reference")})
    assert len(screen) == 420 and sum(x["is_R"] for x in screen) == 308 and sum(x["is_E_core"] for x in screen) == 238
    eval_patients = sorted({x["subject_id"] for x in q["eval_pool"]})
    assert len(eval_patients) == 7
    by_eval = defaultdict(list)
    for x in q["eval_pool"]:
        by_eval[x["subject_id"]].append(x)
    for sid in by_eval:
        by_eval[sid].sort(key=lambda x: (stable("082/eval/v1:", x["proposition_id"]), x["proposition_id"]))
    evaluate = []
    depth = 0
    while len(evaluate) < 180:
        moved = False
        for sid in eval_patients:
            if depth < len(by_eval[sid]) and len(evaluate) < 180:
                x = by_eval[sid][depth]
                evaluate.append({"id": x["proposition_id"], "sid": sid, "author": x["author_type"],
                                 "claim": x["text"], "reference": x["reference"],
                                 "role": x["role"], "patient_rank": depth + 1})
                moved = True
        assert moved
        depth += 1
    assert len(evaluate) == len({x["id"] for x in evaluate}) == 180
    old_eval = i.lines(i.OLD_EVAL)
    by_old_eval = defaultdict(list)
    for x in old_eval:
        by_old_eval[x["sid"]].append(x)
    repeat = []
    for sid, rows in sorted(by_old_eval.items()):
        ordered = sorted(rows, key=lambda x: (stable("082/repeat/v1:", x["id"]), x["id"]))
        repeat.append(ordered[0])
    extra_patients = sorted(by_old_eval, key=lambda s: stable("082/repeat-extra-patient/v1:", s))[:2]
    for sid in extra_patients:
        ordered = sorted(by_old_eval[sid], key=lambda x: (stable("082/repeat/v1:", x["id"]), x["id"]))
        repeat.append(ordered[1])
    assert len(repeat) == 24 and len({x["sid"] for x in repeat}) == 22
    old_cal = i.lines(i.OLD_TRAIN)
    btemplate = old_cal[0]["B"]["body"]
    f4template = i.lines(OLD_F4_JOBS)[0]["body"]
    assert {k: v for k, v in btemplate.items() if k != "messages"} == {k: v for k, v in f4template.items() if k != "messages"}
    assert btemplate["messages"][0]["content"] != f4template["messages"][0]["content"]
    screen_jobs = [job(x["id"], x["sid"], "B", "screen_B", score_body(btemplate, x["claim"], x["reference"])) for x in screen]
    eval_jobs = [job(x["id"], x["sid"], arm, "eval", score_body(template, x["claim"], x["reference"]))
                 for x in evaluate for arm, template in (("B", btemplate), ("F4", f4template))]
    repeat_jobs, repeat_sources = [], {}
    for x in repeat:
        for arm, historical in (("B", "TS"), ("F4", "F4")):
            source = ROOT / x["arms"][historical]["request_source"]
            raw = json.loads(source.read_text(encoding="utf-8-sig"))
            body = raw["job"]["body"]
            assert digest(body) == x["arms"][historical]["body_sha256"]
            repeat_sources[source.relative_to(ROOT).as_posix()] = sha(source)
            repeat_jobs.append(job(x["id"], x["sid"], arm, "repeat", body))
    repeat_jobs.sort(key=lambda x: stable("082/repeat-send/v1:", x["id"] + x["arm"]))
    eval_jobs.sort(key=lambda x: stable("082/eval-send/v1:", x["id"] + x["arm"]))
    write("train_screen_blind.jsonl", screen)
    write("train_screen_manifest.jsonl", train_manifest)
    write("eval_new_blind.jsonl", evaluate)
    write("repeat_blind.jsonl", [{"id": x["id"], "sid": x["sid"]} for x in repeat])
    write("screen_B_jobs.jsonl", screen_jobs)
    write("eval_jobs.jsonl", eval_jobs)
    write("repeat_jobs.jsonl", repeat_jobs)
    template_info = {"B_system_sha256": hashlib.sha256(btemplate["messages"][0]["content"].encode()).hexdigest(),
                     "F4_system_sha256": hashlib.sha256(f4template["messages"][0]["content"].encode()).hexdigest(),
                     "B_template_body_sha256": digest(btemplate), "F4_template_body_sha256": digest(f4template),
                     "B_system": btemplate["messages"][0]["content"], "F4_system": f4template["messages"][0]["content"]}
    write("templates_frozen.json", template_info)
    sources = {p: sha(ROOT / p) for p in [i.MATERIAL, i.SPLIT, i.OLD_EVAL, i.OLD_TRAIN, OLD_F4_JOBS,
                                           "outputs/071_judge_icl_feasibility/freeze.json",
                                           "tasks/082_anchor_configuration_adaptation/protocol.md"]}
    for p in i.EXPOSURE:
        if (ROOT / p).exists():
            sources[p] = sha(ROOT / p)
    sources.update(repeat_sources)
    write("blind_freeze.json", {"status": "FROZEN_BEFORE_082_API_AND_EVALUATION_GT", "cap_original_cny": 50,
                               "train_patients": train_patients, "eval_patients": sorted(q["eval_patients"]),
                               "demo_patients": sorted(q["demo_patients"]), "old_train_n": len(q["old_train"]),
                               "old_eval_n": len(q["old_eval"]), "screen_n": 420, "R_n": 308, "E_core_n": 238,
                               "E_add_n": 70, "new_eval_n": 180, "repeat_n": 24,
                               "new_eval_per_patient": dict(Counter(x["sid"] for x in evaluate)),
                               "source_sha256": sources,
                               "artifacts_sha256": {p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
                               "training_label_set_definition": "079 old114 separate; new screen420 all distinct; R/E only B/F4 paired core valid used for fit",
                               "eval_selection": "GT-free fixed hash after excluding old352 and available 066-070/081 mechanism ID lists"})
    print(json.dumps({"train_screen": 420, "R": 308, "E_core": 238,
                      "eval_new": 180, "eval_patients": dict(Counter(x["sid"] for x in evaluate)),
                      "repeat": 24, "repeat_patients": 22}, ensure_ascii=False))


if __name__ == "__main__":
    main()
