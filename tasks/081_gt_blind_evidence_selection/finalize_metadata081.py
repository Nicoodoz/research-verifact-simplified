"""Create concise patient manifest from the immutable blind sample."""
import csv
from collections import defaultdict

import blind081 as b


def main():
    sample = b.lines("outputs/081_gt_blind_evidence_selection/sample_blind.jsonl")
    patients = defaultdict(list)
    for x in sample:
        patients[x["sid"]].append(x)
    assert len(patients) == 24
    with (b.OUT / "patients.csv").open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject_id", "stage1_ids", "stage1_new_n",
                                                  "stage2_ids", "stage2_new_n", "source"])
        writer.writeheader()
        for sid, rows in sorted(patients.items()):
            s1 = [x for x in rows if x["stage"] == 1]
            s2 = [x for x in rows if x["stage"] == 2]
            assert len(s1) == len(s2) == 4
            writer.writerow({"subject_id": sid, "stage1_ids": ";".join(x["id"] for x in s1),
                             "stage1_new_n": sum(not x["previously_exposed"] for x in s1),
                             "stage2_ids": ";".join(x["id"] for x in s2),
                             "stage2_new_n": sum(not x["previously_exposed"] for x in s2),
                             "source": s1[0]["source"]})
    print("24 patient rows saved")


if __name__ == "__main__":
    main()
