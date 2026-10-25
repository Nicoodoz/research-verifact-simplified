"""Freeze diagnostic 068 repeats and presentation controls; no API calls."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c  # noqa: E402
from build_stage2_067 import CORPUS  # noqa: E402


def read_jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def id_order(pid):
    return hashlib.sha256(str(pid).encode("utf-8")).hexdigest()


def blocks_as_subsequence(first, second):
    positions = []
    start = 0
    for item in first:
        try:
            pos = second.index(item, start)
        except ValueError:
            return False, positions
        positions.append(pos)
        start = pos + 1
    return True, positions


def normalized_blocks(ref):
    """067 may delimit blocks with either actual LF or literal backslash-n."""
    parts = re.split(r"(?:^|\n|\\n)\d+\. Date:", ref)
    out = []
    for part in parts[1:]:
        if "| Text:" not in part:
            continue
        content = part.split("| Text:", 1)[1]
        content = content.replace("\\n", " ").replace("\n", " ")
        out.append(re.sub(r"\s+", " ", content).strip().lower())
    return out


def main():
    if (OUT / "freeze_002.json").exists():
        raise RuntimeError("068 already frozen")
    OUT.mkdir(parents=True, exist_ok=True)
    p067 = ROOT / "outputs/067_conservative_evidence_packing"
    rows = list(csv.DictReader((p067 / "results.csv").open(encoding="utf-8-sig", newline="")))
    cases = {x["id"]: x for x in read_jsonl(p067 / "cases_blind.jsonl")}
    packs = {x["id"]: x for x in read_jsonl(p067 / "pack_mapping.jsonl")}
    formal = {x["id"]: x for x in read_jsonl(p067 / "stage2_jobs.jsonl")}
    original = {x["id"]: x for x in read_jsonl(ROOT / "outputs/052_first_tier_validation/main_jobs.jsonl") if x["condition"] == "T-S"}
    assert len(rows) == len(cases) == len(packs) == 236
    assert len(formal) == 226
    groups = {}
    for row in rows:
        old_ok = row["baseline_pg"] == row["GT"]
        new_ok = row["new_pg"] == row["GT"]
        if not old_ok and new_ok:
            kind = "rescue"
        elif old_ok and not new_ok:
            kind = "harm"
        elif row["changed"] == "True" and old_ok:
            kind = "unchanged_correct"
        elif row["changed"] == "True" and not old_ok:
            kind = "unchanged_wrong"
        else:
            kind = "unmodified"
        groups[row["id"]] = kind
    counts = Counter(groups.values())
    assert counts["rescue"] == 14 and counts["harm"] == 13
    chosen = [r["id"] for r in rows if groups[r["id"]] in ("rescue", "harm")]
    for kind in ("unchanged_correct", "unchanged_wrong"):
        chosen += sorted((r["id"] for r in rows if groups[r["id"]] == kind), key=id_order)[:6]
    assert len(chosen) == 39

    corpora = {key: {x["passage_id"]: x for x in read_jsonl(path)} for key, path in CORPUS.items()}
    mechanism = []
    presentation = {}
    for row in rows:
        pid = row["id"]
        case, pack = cases[pid], packs[pid]
        b = normalized_blocks(case["baseline_reference"])
        f = normalized_blocks(pack["final_reference"])
        retained, positions = blocks_as_subsequence(b, f)
        entry = {
            "id": pid,
            "group": groups[pid],
            "changed": bool(pack["changed"]),
            "baseline_blocks": len(b),
            "final_blocks": len(f),
            "baseline_blocks_retained_in_order": retained,
            "baseline_positions_in_final": positions,
            "header_same": c.reference_header(case["baseline_reference"]) == c.reference_header(pack["final_reference"]),
            "added_n": len(pack["added_pids"]),
            "dropped_n": len(pack["dropped_pids"]),
        }
        if pack["changed"]:
            assert case["mapped"] and case["source"] in corpora
            ref = c.build_reference_from_ids(case["baseline_pids"], corpora[case["source"]], case["baseline_reference"])
            entry["presentation_identical_to_baseline"] = ref == case["baseline_reference"]
            entry["presentation_blocks_same"] = normalized_blocks(ref) == b
            if entry["presentation_blocks_same"]:
                presentation[pid] = ref
        mechanism.append(entry)

    jobs = []
    for pid in sorted(chosen, key=id_order):
        old = original[pid]["body"]
        new = formal[pid]["body"]
        assert old["model"] == new["model"] == c.MODELS["deepseek"]
        assert new == c.score_body(cases[pid]["claim"], packs[pid]["final_reference"])
        jobs += [
            {"request_id": "068_repeat_baseline_" + sha(pid)[:24], "id": pid, "condition": "baseline_repeat", "group": groups[pid], "model_key": "deepseek", "body": old},
            {"request_id": "068_repeat_added_" + sha(pid)[:24], "id": pid, "condition": "added_repeat", "group": groups[pid], "model_key": "deepseek", "body": new},
        ]
    bound = sum(c.bound(job) for job in jobs)
    assert bound <= 9.5, f"repeat bound {bound:.4f} exceeds 9.5"
    pres_candidates = sorted((pid for pid in chosen if groups[pid] in ("rescue", "harm") and pid in presentation and presentation[pid] != cases[pid]["baseline_reference"]), key=id_order)
    for pid in pres_candidates:
        job = {"request_id": "068_presentation_" + sha(pid)[:24], "id": pid, "condition": "presentation_only", "group": groups[pid], "model_key": "deepseek", "body": c.score_body(cases[pid]["claim"], presentation[pid])}
        if bound + c.bound(job) > 9.5:
            break
        jobs.append(job)
        bound += c.bound(job)
    ids = [j["request_id"] for j in jobs]
    assert len(ids) == len(set(ids))
    for job in jobs:
        assert set(job["body"]) <= {"enable_thinking", "max_tokens", "messages", "model", "n", "reasoning_effort", "response_format", "stream", "temperature"}
        assert job["body"].get("enable_thinking") is True
        assert job["body"].get("reasoning_effort") == "high"
        assert job["body"].get("max_tokens") == 8192
        job["body_sha256"] = sha(job["body"])
        job["conservative_reservation_cny"] = c.bound(job)

    with (OUT / "mechanism_mapping_002.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for entry in mechanism:
            handle.write(canonical(entry) + "\n")
    with (OUT / "jobs_002.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for job in jobs:
            handle.write(canonical(job) + "\n")
    source_paths = [
        p067 / "results.csv", p067 / "cases_blind.jsonl", p067 / "pack_mapping.jsonl",
        p067 / "stage2_jobs.jsonl", ROOT / "outputs/052_first_tier_validation/main_jobs.jsonl",
        HERE / "protocol.md", HERE / "protocol_amendment_001.md", HERE / "prepare068.py",
    ]
    freeze = {
        "task": "068_final_pack_utility_diagnosis",
        "historical_groups": dict(counts),
        "diagnostic_cases": len(chosen),
        "repeat_jobs": 2 * len(chosen),
        "presentation_candidates": len(pres_candidates),
        "presentation_jobs": sum(j["condition"] == "presentation_only" for j in jobs),
        "changed_baseline_blocks_retained_in_order": sum(x["changed"] and x["baseline_blocks_retained_in_order"] for x in mechanism),
        "changed_presentation_blocks_same": sum(x["changed"] and x.get("presentation_blocks_same", False) for x in mechanism),
        "all_jobs": len(jobs),
        "conservative_total_reservation_cny": bound,
        "hard_cap_cny": 10.0,
        "unknown_or_failure_buffer_cny": 10.0 - bound,
        "model": c.MODELS["deepseek"],
        "price_basis_cny_per_million_input_output": list(c.PRICES["deepseek"]),
        "selection_uses_067_outcome": "all 27 final flips; noflip controls selected by ID hash",
        "new_answers_used_for_selection": False,
        "GT_in_API": False,
        "reserved_used": False,
        "jobs_sha256": hashlib.sha256((OUT / "jobs_002.jsonl").read_bytes()).hexdigest(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
    }
    (OUT / "freeze_002.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: freeze[k] for k in ("historical_groups", "diagnostic_cases", "repeat_jobs", "presentation_candidates", "presentation_jobs", "all_jobs", "conservative_total_reservation_cny", "unknown_or_failure_buffer_cny")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
