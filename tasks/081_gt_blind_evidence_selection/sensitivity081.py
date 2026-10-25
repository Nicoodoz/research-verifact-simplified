"""Post hoc descriptive exposure sensitivity; never replaces frozen 96-case gates."""
import json

import analyze081 as a
import blind081 as b
import run081 as r


def main():
    first = b.lines("outputs/081_gt_blind_evidence_selection/case_results.jsonl")
    result = r.read(b.OUT / "results.json")
    historical = {pid for ids in result["historical_066_069_overlap"].values() for pid in ids}
    groups = {"not_066_069": [x for x in first if x["id"] not in historical],
              "previously_unexposed_blind": [x for x in first if not x["previously_exposed"]],
              "historically_exposed_blind": [x for x in first if x["previously_exposed"]]}
    out = {}
    for name, rows in groups.items():
        out[name] = {"n": len(rows), "patients": len({x["sid"] for x in rows}),
                     "GT": {lab: sum(x["GT"] == lab for x in rows) for lab in a.LABELS},
                     "correct": {arm: sum(x["methods"][arm]["PriorG"] == x["GT"] for x in rows)
                                 for arm in ("B", "U", "T")},
                     "rescue_harm": {arm: {"rescue": sum(x["methods"]["B"]["PriorG"] != x["GT"] and x["methods"][arm]["PriorG"] == x["GT"] for x in rows),
                                          "harm": sum(x["methods"]["B"]["PriorG"] == x["GT"] and x["methods"][arm]["PriorG"] != x["GT"] for x in rows)}
                                     for arm in ("U", "T")},
                     "ids": [x["id"] for x in rows]}
    a.write("overlap_sensitivity.json", {"status": "post_hoc_descriptive_only", "groups": out,
                                         "protocol_deviation": "Sampling prioritized broad blind exposure lists but did not explicitly exclude 066-069 diagnostic ID lists before hash choice; 41 Stage1 IDs overlap 067. No resampling or gate change."})
    print(json.dumps({k: (v["n"], v["patients"], v["correct"]) for k, v in out.items()}))


if __name__ == "__main__":
    main()
