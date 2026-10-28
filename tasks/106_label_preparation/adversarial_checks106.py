"""Independent read-only checks of actual frozen candidates, no model/API."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/106_label_preparation"
PRIVATE = ROOT / ".local_models/106_label_preparation"


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line]


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    original196 = ROOT / ".local_models/104_supervision_evidence/paired/label_only.jsonl"
    sources = [ROOT / "outputs/103_lora_selection/patient_roles.json", PRIVATE / "training_pool.jsonl", OUT / "data_pool_index.jsonl", OUT / "data_isolation.jsonl", OUT / "semantic_B.jsonl", original196, Path(__file__)] + [PRIVATE / (arm + ".jsonl") for arm in ("ordinary_sample", "boundary_cover", "label_mean", "label_sum")]
    source_sha = {p.relative_to(ROOT).as_posix(): file_sha(p) for p in sources}
    roles = json.loads((ROOT / "outputs/103_lora_selection/patient_roles.json").read_text(encoding="utf-8-sig"))["patients"]
    train_sids = set(map(str, roles["train"]))
    forbidden_sids = set(map(str, roles["selection"] + roles["confirmation"]))
    pool = {r["id"]: r for r in rows(PRIVATE / "training_pool.jsonl")}
    index = {r["id"]: r for r in rows(OUT / "data_pool_index.jsonl")}
    isolated = {r["id"] for r in rows(OUT / "data_isolation.jsonl")}
    arms = {name: rows(PRIVATE / (name + ".jsonl")) for name in ("ordinary_sample", "boundary_cover")}
    checks = {"patient_roles_disjoint": not bool(train_sids & forbidden_sids), "full_pool_N3675": len(pool) == 3675}
    summaries = {}
    strata = {}
    for arm, data in arms.items():
        ids = {r["id"] for r in data}
        checks[arm + "_N512_unique"] = len(data) == len(ids) == 512
        checks[arm + "_only_train40"] = {r["sid"] for r in data} == train_sids and not {r["sid"] for r in data} & forbidden_sids
        checks[arm + "_no_known_gap"] = not bool(ids & isolated)
        checks[arm + "_quotas"] = Counter(r["GT"] for r in data) == Counter({"Supported": 320, "Not Supported": 96, "Not Addressed": 96})
        unchanged = []
        for r in data:
            source = pool[r["id"]]
            unchanged.append(all(r[k] == source[k] for k in ("sid", "GT", "claim", "reference", "reference_id", "author")))
            unchanged.append(json.loads(r["answer"]) == {"verdict": source["GT"]})
            unchanged.append(r["reference_id"] == digest(r["reference"]))
        checks[arm + "_own_original_claim_reference_GT"] = all(unchanged)
        strata[arm] = Counter((index[r["id"]]["sid"], index[r["id"]]["GT"], index[r["id"]]["author"], index[r["id"]]["length_quartile"], index[r["id"]]["semantic104_status"]) for r in data)
        summaries[arm] = {"N": len(data), "patients": len({r["sid"] for r in data}), "GT": dict(Counter(r["GT"] for r in data)), "author": dict(Counter(r["author"] for r in data)), "semantic104_status": dict(Counter(index[r["id"]]["semantic104_status"] for r in data))}
    checks["actual_5way_strata_exact"] = strata["ordinary_sample"] == strata["boundary_cover"]
    b16 = rows(OUT / "semantic_B.jsonl")
    for arm, data in arms.items():
        ids = {r["id"] for r in data}
        summaries[arm]["B16_included_ids"] = [r["id"] for r in b16 if r["id"] in ids]
    checks["B16_membership_same_both_arms"] = summaries["ordinary_sample"]["B16_included_ids"] == summaries["boundary_cover"]["B16_included_ids"]
    active = {arm: rows(PRIVATE / (arm + ".jsonl")) for arm in ("label_mean", "label_sum")}
    checks["active196_byte_identical_to104_and_each_other"] = file_sha(PRIVATE / "label_mean.jsonl") == file_sha(PRIVATE / "label_sum.jsonl") == file_sha(original196)
    checks["active196_same_original_order"] = [r["id"] for r in active["label_mean"]] == [r["id"] for r in rows(original196)]
    for arm, data in active.items():
        checks[arm + "_196_unique_original_quotas"] = len(data) == len({r["id"] for r in data}) == 196 and Counter(r["GT"] for r in data) == Counter({"Supported": 83, "Not Supported": 62, "Not Addressed": 51})
        checks[arm + "_train_patients_only"] = {str(r["sid"]) for r in data} == train_sids and not {str(r["sid"]) for r in data} & forbidden_sids
    label_lengths = {"Supported": 1, "Not Supported": 2, "Not Addressed": 3}
    length_sum = sum(label_lengths[r["GT"]] for r in active["label_mean"])
    checks["active196_global_verdict_length_sum360"] = length_sum == 360
    normalizer = length_sum / len(active["label_mean"])
    checks["global_sum_segment_average_weight_preserved"] = abs(sum(label_lengths[r["GT"]] / normalizer for r in active["label_mean"]) / 196 - 1) < 1e-12
    if source_sha != {p.relative_to(ROOT).as_posix(): file_sha(p) for p in sources}:
        raise RuntimeError("A candidate/source changed during independent checks; rerun after data freeze")
    result = {"scope": "106 literature/source-B agent independent candidate-integrity checks; not executor selfcheck or clinical-validity certification", "checks": checks, "all_listed_integrity_checks_pass": all(checks.values()), "summary": summaries, "active196_verdict_length_sum": length_sum, "active196_global_normalizer": normalizer, "actual_isolated_N": len(isolated), "source_sha256": source_sha, "clinical_text_printed": False, "paid_API_new": 0, "GPU_calls": 0}
    (OUT / "adversarial_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"checks": checks, "integrity_only": True}))


if __name__ == "__main__":
    main()
