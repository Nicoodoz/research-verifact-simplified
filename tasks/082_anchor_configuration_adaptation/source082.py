"""Register provenance of the frozen C48 final references without reading GT."""
from __future__ import annotations

import hashlib
from collections import Counter

import inventory082 as i
import prepare082 as p

ROOT, OUT = i.ROOT, i.OUT


def main():
    material = {x["proposition_id"]: x for x in i.lines(i.MATERIAL)}
    rows = []
    for name, cohort in (("train_screen", i.lines("outputs/082_anchor_configuration_adaptation/train_screen_blind.jsonl")),
                         ("new_eval", i.lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl"))):
        for x in cohort:
            source = material[x["id"]]
            assert x["claim"] == source["text"] and x["reference"] == source["reference"]
            rows.append({"id": x["id"], "sid": x["sid"], "cohort": name,
                         "material_role": source["role"], "evidence_source": source["evidence_source"],
                         "claim_sha256": hashlib.sha256(x["claim"].encode()).hexdigest(),
                         "reference_sha256": hashlib.sha256(x["reference"].encode()).hexdigest(),
                         "reference_chars": len(x["reference"]),
                         "source_selected_ids": source.get("selected_ids")})
    p.write("source_manifest.jsonl", rows)
    print({"rows": len(rows), "by_source": dict(Counter(x["evidence_source"] for x in rows))})


if __name__ == "__main__":
    main()
