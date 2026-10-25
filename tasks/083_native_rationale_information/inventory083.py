"""Recover native B/F4 answers and exact request provenance without reading evaluation GT."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/083_native_rationale_information"
sys.path.insert(0, str(ROOT / "tasks/082_anchor_configuration_adaptation"))
import inventory082 as i82
import run082 as r82
import prepare082 as p82

MODEL = "deepseek-v4-flash-0731"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def lines(path):
    with (ROOT / path).open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    path = OUT / name
    assert not path.exists(), path
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if name.endswith(".jsonl"):
            for row in value:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")


def native(phase, arm, pid, sid, receipt_source, request_source=None, expected=None):
    receipt_path = ROOT / receipt_source
    request_path = ROOT / (request_source or str(Path(receipt_source).with_name("request.json")))
    assert receipt_path.is_file() and request_path.is_file(), (pid, receipt_source)
    rb, qb = receipt_path.read_bytes(), request_path.read_bytes()
    receipt, request = json.loads(rb), json.loads(qb)
    assert receipt["request_sha256"] == digest(qb), (pid, receipt_source)
    body = request["job"]["body"]
    body_sha = p82.digest(body)
    if expected and expected.get("body_sha256"):
        assert body_sha == expected["body_sha256"], (pid, arm, "body")
    assert body["model"] == MODEL and body.get("enable_thinking") is True
    assert len(body["messages"]) >= 2
    user = json.loads(body["messages"][1]["content"])
    assert set(user) == {"proposition", "reference"}
    transport = receipt["transport"]
    assert transport["http_status"] == 200
    response = json.loads(transport["body_text"])
    assert response["model"] == MODEL
    choice = response["choices"][0]
    msg = choice["message"]
    content = msg.get("content") or ""
    try:
        fields = json.loads(content)
        assert isinstance(fields, dict)
    except (ValueError, AssertionError):
        fields = {}
    reason = fields.get("reason") if isinstance(fields.get("reason"), str) else ""
    checks = fields.get("checks") if isinstance(fields.get("checks"), (list, dict)) else None
    thinking = msg.get("reasoning_content") if isinstance(msg.get("reasoning_content"), str) else ""
    if expected and expected.get("valid"):
        scores = fields.get("label_scores")
        assert isinstance(scores, dict)
        assert all(abs(float(scores[k]) - float(expected["scores"][k])) < 1e-8
                   for k in ("Supported", "Not Supported", "Not Addressed")), (pid, arm, "scores")
        assert fields.get("verdict") == expected["raw"], (pid, arm, "raw")
    check_keys = sorted({key for item in (checks if isinstance(checks, list) else [])
                         if isinstance(item, dict) for key in item})
    meta = {"phase": phase, "arm": arm, "id": pid, "sid": sid,
            "request_source": request_path.relative_to(ROOT).as_posix(),
            "receipt_source": receipt_path.relative_to(ROOT).as_posix(),
            "request_sha256": digest(qb), "receipt_sha256": digest(rb),
            "body_sha256": body_sha, "content_sha256": digest(content.encode()),
            "claim_sha256": digest(user["proposition"].encode()),
            "reference_sha256": digest(user["reference"].encode()),
            "prompt_sha256": digest(str(body["messages"][0]["content"]).encode()),
            "model": response["model"], "finish_reason": choice.get("finish_reason"),
            "reason_chars": len(reason), "checks_type": type(checks).__name__,
            "checks_n": len(checks) if checks is not None else 0,
            "check_keys": check_keys, "thinking_chars": len(thinking),
            "content_json_valid": bool(fields), "has_scores": isinstance(fields.get("label_scores"), dict),
            "has_verdict": isinstance(fields.get("verdict"), str)}
    text = {"phase": phase, "arm": arm, "id": pid, "sid": sid,
            "claim": user["proposition"], "reason": reason, "checks": checks,
            "reasoning_content": thinking, "native_verdict": fields.get("verdict"),
            "native_scores": fields.get("label_scores"), "body_sha256": body_sha,
            "content_sha256": meta["content_sha256"]}
    return meta, text


def main():
    assert not OUT.exists(), OUT
    OUT.mkdir(parents=True)
    effective = read(ROOT / "outputs/082_anchor_configuration_adaptation/training_effective.json")
    ids = set(effective["R_ids"]) | set(effective["E_ids"])
    assert len(ids) == 347 and len(effective["old112_ids"]) == 112
    new_pairs = {x["id"]: x for x in lines("outputs/082_anchor_configuration_adaptation/training_pairs.jsonl")}
    old_pairs = {x["id"]: x for x in lines("outputs/079_f4_priorg_adaptation/calibration_predictions.jsonl")}
    train = []
    for pid in sorted(ids):
        x = new_pairs[pid]
        train.append((pid, x["sid"], x["GT"],
                      {arm: {"receipt_source": x[f"{arm}_receipt_source"],
                             "body_sha256": x[f"{arm}_body_sha256"],
                             "scores": x[arm], "raw": x[f"{arm}_raw"], "valid": True}
                       for arm in ("B", "F4")}, "082 R/E union"))
    for pid in effective["old112_ids"]:
        x = old_pairs[pid]
        arms = {}
        for arm in ("B", "F4"):
            y = x[arm]
            arms[arm] = {"receipt_source": y["receipt_source"],
                         "request_source": y["request_source"],
                         "scores": y["parsed"]["scores"],
                         "raw": y["parsed"]["verdict"], "valid": True}
        train.append((pid, x["sid"], x["GT"], arms, "079 old112"))
    assert len(train) == 459 and len({x[0] for x in train}) == 459
    old_eval = lines("outputs/079_f4_priorg_adaptation/evaluation_blind.jsonl")
    assert len(old_eval) == 352
    eval_items = []
    for x in old_eval:
        arms = {}
        for arm, historical in (("B", "TS"), ("F4", "F4")):
            y = x["arms"][historical]
            arms[arm] = {"receipt_source": y["receipt_source"],
                         "request_source": y["request_source"],
                         "body_sha256": y["body_sha256"], "scores": y.get("scores"),
                         "raw": y.get("raw"), "valid": y["valid"]}
        eval_items.append((x["id"], x["sid"], arms, "old352"))
    new_blind = lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")
    eval_jobs = {(x["id"], x["arm"]): x for x in r82.jobs("eval")}
    _, eval_answers = r82.answers("eval")
    assert len(new_blind) == 180 and len(eval_answers) == 360
    for x in new_blind:
        arms = {}
        for arm in ("B", "F4"):
            y = eval_answers[eval_jobs[x["id"], arm]["request_id"]]
            arms[arm] = {"receipt_source": y.get("receipt_source") or y["attempt"]["receipt_source"],
                         "request_source": y.get("request_source") or y["attempt"]["request_source"],
                         "body_sha256": eval_jobs[x["id"], arm]["body_sha256"]}
        eval_items.append((x["id"], x["sid"], arms, "new180"))
    assert len(eval_items) == 532 and len({x[0] for x in eval_items}) == 532
    repeat_blind = lines("outputs/082_anchor_configuration_adaptation/repeat_blind.jsonl")
    repeat_jobs = {(x["id"], x["arm"]): x for x in r82.jobs("repeat")}
    _, repeat_answers = r82.answers("repeat")
    assert len(repeat_blind) == 24 and len(repeat_answers) == 48
    repeats = []
    for x in repeat_blind:
        arms = {}
        for arm in ("B", "F4"):
            job = repeat_jobs[x["id"], arm]
            answer = repeat_answers[job["request_id"]]
            assert answer["mode"] == "new"
            arms[arm] = {"receipt_source": answer["attempt"]["receipt_source"],
                         "request_source": answer["attempt"]["request_source"],
                         "body_sha256": job["body_sha256"]}
        repeats.append((x["id"], x["sid"], arms))
    train_pat = {x[1] for x in train}
    eval_pat = {x[1] for x in eval_items}
    demo_pat = set(read(ROOT / "outputs/082_anchor_configuration_adaptation/blind_freeze.json")["demo_patients"])
    assert len(train_pat) == 14 and len(eval_pat) == 22
    assert not train_pat & eval_pat and not demo_pat & (train_pat | eval_pat)
    manifest, texts, labels = [], [], []
    for pid, sid, gt, arms, source in train:
        labels.append({"id": pid, "sid": sid, "GT": gt, "source": source})
        for arm in ("B", "F4"):
            x = arms[arm]
            m, t = native("train", arm, pid, sid, x["receipt_source"], x.get("request_source"), x)
            manifest.append(m); texts.append(t)
    for pid, sid, arms, cohort in eval_items:
        for arm in ("B", "F4"):
            x = arms[arm]
            m, t = native(cohort, arm, pid, sid, x["receipt_source"], x.get("request_source"), x)
            manifest.append(m); texts.append(t)
    for pid, sid, arms in repeats:
        for arm in ("B", "F4"):
            x = arms[arm]
            m, t = native("repeat", arm, pid, sid, x["receipt_source"], x.get("request_source"), x)
            manifest.append(m); texts.append(t)
    assert len(manifest) == len(texts) == 2 * (459 + 532 + 24)
    quality = {}
    for phase in ("train", "old352", "new180", "repeat"):
        for arm in ("B", "F4"):
            group = [x for x in manifest if x["phase"] == phase and x["arm"] == arm]
            quality[phase + ":" + arm] = {
                "n": len(group), "reason_present": sum(x["reason_chars"] > 0 for x in group),
                "checks_present": sum(x["checks_n"] > 0 for x in group),
                "thinking_present": sum(x["thinking_chars"] > 0 for x in group),
                "json_content": sum(x["content_json_valid"] for x in group),
                "scores_present": sum(x["has_scores"] for x in group),
                "finish_reasons": dict(Counter(x["finish_reason"] for x in group)),
                "checks_types": dict(Counter(x["checks_type"] for x in group)),
                "check_keys": dict(Counter(k for x in group for k in x["check_keys"])),
                "reason_char_median": sorted(x["reason_chars"] for x in group)[len(group)//2],
                "reason_char_max": max(x["reason_chars"] for x in group),
                "thinking_char_median": sorted(x["thinking_chars"] for x in group)[len(group)//2],
            }
    write("source_manifest.jsonl", manifest)
    write("native_texts.jsonl", texts)
    write("train_labels.jsonl", labels)
    write("native_quality.json", {"quality": quality, "training_n": len(train),
                                  "evaluation_n": len(eval_items), "repeat_n": len(repeats),
                                  "training_patients": sorted(train_pat),
                                  "evaluation_patients": sorted(eval_pat),
                                  "example_patients": sorted(demo_pat),
                                  "evaluation_GT_read": False,
                                  "source_files": {
                                      path: digest((ROOT / path).read_bytes()) for path in (
                                          "outputs/082_anchor_configuration_adaptation/training_effective.json",
                                          "outputs/082_anchor_configuration_adaptation/training_pairs.jsonl",
                                          "outputs/079_f4_priorg_adaptation/calibration_predictions.jsonl",
                                          "outputs/079_f4_priorg_adaptation/evaluation_blind.jsonl",
                                          "outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl",
                                          "outputs/082_anchor_configuration_adaptation/repeat_blind.jsonl")}})
    print(json.dumps(quality, ensure_ascii=False))


if __name__ == "__main__":
    main()
