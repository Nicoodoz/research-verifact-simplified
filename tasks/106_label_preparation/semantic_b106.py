"""Record task 106 train-only source readings without publishing clinical text."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / ".local_models/106_label_preparation"
PUBLIC = ROOT / "outputs/106_label_preparation"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]


def main() -> None:
    pool = {row["id"]: row for row in read_rows(PRIVATE / "training_pool.jsonl")}
    original = {row["id"]: row for row in read_rows(PUBLIC / "data_104_supported_disagreements.jsonl")}
    public, private = [], []
    drafts = read_rows(PRIVATE / "semantic_B_drafts.jsonl")
    assert len({row["id"] for row in drafts}) == len(drafts)
    for draft in drafts:
        row = pool[draft["id"]]
        assert row["role"] == "train"
        assert row["id"] in original
        ref = row["reference"]
        assert sha(ref) == original[row["id"]]["reference_sha256"]
        assert sha(row["claim"]) == original[row["id"]]["claim_sha256"]
        spans = []
        for item in draft["quotes"]:
            quote = item["text"]
            offsets = []
            start = 0
            while (pos := ref.find(quote, start)) >= 0:
                offsets.append([pos, pos + len(quote)])
                start = pos + 1
            if not offsets:
                raise ValueError(f"Unmatched quote: {draft['id']} {quote!r}")
            spans.append({"role": item["role"], "offsets_python_chars": offsets, "quote_sha256": sha(quote), "quote": quote})
        common = {
            "id": row["id"], "sid": row["sid"], "role": "train",
            "GT_unchanged": row["GT"], "destination104": original[row["id"]]["actual_destination104"],
            "category": draft["category"], "recommendation": draft["recommendation"],
            "relation_dimensions": draft["dimensions"], "abstract_finding": draft["finding"],
            "counterevidence": draft["counterevidence"], "limitations": draft["limitations"],
            "claim_sha256": sha(row["claim"]), "reference_sha256": sha(ref),
            "reference_characters": len(ref), "full_actual_reference_read": True,
            "additional_EHR_read": False, "current_input_changed": False,
            "GT_modified": False, "reviewer": "106 literature/source-B agent; not clinician gold",
            "GT_known_targeted_review": True,
            "prior104_relation_read_after_all16_drafts": True,
            "prior104_isolation_not_revoked": True,
            "source_positions": [{k: v for k, v in span.items() if k != "quote"} for span in spans],
        }
        public.append(common)
        private.append({**common, "claim": row["claim"], "quotes": spans})
    for path, rows in [(PUBLIC / "semantic_B.jsonl", public), (PRIVATE / "semantic_B_private.jsonl", private)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    print(json.dumps({"recorded": len(public), "all_quote_spans_matched": True, "clinical_text_public": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
