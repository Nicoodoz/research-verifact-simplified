"""Index first historical HTTP200 receipts by exact body hash; never send API calls."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import inventory082 as i
import prepare082 as p

ROOT, OUT = i.ROOT, i.OUT


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def targets():
    wanted = {}
    for name in ("screen_B_jobs.jsonl", "eval_jobs.jsonl"):
        for j in i.lines("outputs/082_anchor_configuration_adaptation/" + name):
            wanted.setdefault(j["body_sha256"], []).append((j["id"], j["arm"], j["stage"]))
    template = read(OUT / "templates_frozen.json")
    f4 = i.lines("outputs/079_f4_priorg_adaptation/main_jobs.jsonl")[0]["body"]
    for x in i.lines("outputs/082_anchor_configuration_adaptation/train_screen_blind.jsonl"):
        body = p.score_body(f4, x["claim"], x["reference"])
        wanted.setdefault(p.digest(body), []).append((x["id"], "F4", "screen_candidate"))
    return wanted


def main():
    wanted = targets()
    found = {}
    scan_names = [d for d in sorted((ROOT / "outputs").iterdir())
                  if d.is_dir() and d.name[:3].isdigit() and
                  (51 <= int(d.name[:3]) <= 53 or 71 <= int(d.name[:3]) <= 81)]
    count = 0
    for directory in scan_names:
        for path in directory.rglob("request.json"):
            if "attempts" not in path.parts:
                continue
            count += 1
            try:
                req = read(path)
                body = (req.get("job") or {}).get("body")
                if not body:
                    continue
                h = p.digest(body)
                if h not in wanted:
                    continue
                receipt_path = path.parent / "receipt.json"
                if not receipt_path.exists():
                    continue
                receipt = read(receipt_path)
                if receipt.get("request_sha256") != p.sha(path) or receipt["transport"]["http_status"] != 200:
                    continue
                candidate = {"body_sha256": h, "request_source": path.relative_to(ROOT).as_posix(),
                             "receipt_source": receipt_path.relative_to(ROOT).as_posix(),
                             "request_sha256": p.sha(path), "receipt_sha256": p.sha(receipt_path),
                             "started_utc": receipt["transport"]["started_utc"],
                             "targets": wanted[h]}
                if h not in found or candidate["started_utc"] < found[h]["started_utc"]:
                    found[h] = candidate
            except (KeyError, ValueError, TypeError):
                continue
    rows = sorted(found.values(), key=lambda x: x["body_sha256"])
    p.write("cache_index.jsonl", rows)
    matched = Counter(y[2] + "/" + y[1] for row in rows for y in row["targets"])
    result = {"historical_attempts_scanned": count, "exact_body_hash_targets": len(wanted),
              "cached_body_hashes": len(rows), "matched_logical": dict(matched),
              "cache_sha256": p.sha(OUT / "cache_index.jsonl"),
              "scope": [x.name for x in scan_names]}
    p.write("cache_index_summary.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "scope"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
