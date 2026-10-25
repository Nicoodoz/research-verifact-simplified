"""034: exact same-ID comparison of original VeriFact, U2, and U2+A(all40 LOPO)."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from verifact_research.evaluation import evaluate, paired_compare

OUT = ROOT / "outputs" / "034_same_data_comparison"
P033 = ROOT / "outputs" / "033_gate_training_subset" / "evaluation_001" / "full_predictions.csv"
O_H = ROOT / "outputs" / "002_reproduce_paper_results" / "run_003" / "baseline_predictions" / "R1-70B_human_claim_valid_only.csv"
O_L = ROOT / "outputs" / "002_reproduce_paper_results" / "run_003" / "baseline_predictions" / "R1-70B_llm_claim_valid_only.csv"

METHODS = ("Original_Verifact_O", "U2", "U2_A_all40_LOPO")
LABELS = ("Supported", "Not Supported", "Not Addressed")


def rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, data: list[dict]) -> None:
    if not data:
        raise ValueError(f"empty csv: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def false_s(metric: dict) -> int:
    c = metric["confusion_matrix"]
    return int(c[1][0] + c[2][0])


def correct(metric: dict) -> int:
    c = metric["confusion_matrix"]
    return int(sum(c[i][i] for i in range(3)))


def metric_row(scope: str, method: str, metric: dict) -> dict:
    pc = metric["per_class"]
    return {
        "scope": scope, "method": method, "n": metric["n"], "correct": correct(metric),
        "PA": metric["percent_agreement"], "MCC": metric["mcc"], "AC1": metric["gwet_ac1"],
        "false_S": false_s(metric),
        "S_precision": pc["Supported"]["precision"], "S_recall": pc["Supported"]["recall"], "S_f1": pc["Supported"]["f1"],
        "NS_precision": pc["Not Supported"]["precision"], "NS_recall": pc["Not Supported"]["recall"], "NS_f1": pc["Not Supported"]["f1"],
        "NA_precision": pc["Not Addressed"]["precision"], "NA_recall": pc["Not Addressed"]["recall"], "NA_f1": pc["Not Addressed"]["f1"],
    }


def make_eval(rows_: list[dict], method: str):
    cohort = [
        {"proposition_id": r["proposition_id"], "subject_id": r["subject_id"], "human_gt": r["GT"]}
        for r in rows_
    ]
    pred = [{"proposition_id": r["proposition_id"], "verdict": r[method]} for r in rows_]
    return cohort, pred, evaluate(cohort, pred, profile="research_patient", iterations=1000)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = rows(P033)
    human_o, llm_o = rows(O_H), rows(O_L)
    if len({r["proposition_id"] for r in base}) != len(base):
        raise ValueError("033 contains duplicate proposition IDs")
    if len({r["proposition_id"] for r in human_o + llm_o}) != len(human_o) + len(llm_o):
        raise ValueError("original VeriFact prediction IDs overlap or duplicate")

    human_map = {r["proposition_id"]: r["verdict"] for r in human_o}
    llm_map = {r["proposition_id"]: r["verdict"] for r in llm_o}
    common = []
    for r in base:
        source = human_map if r["author_type"] == "human" else llm_map
        if r["proposition_id"] not in source:
            raise ValueError(f"missing original VeriFact prediction: {r['proposition_id']}")
        common.append({
            "proposition_id": r["proposition_id"], "subject_id": r["subject_id"],
            "partition": r["partition"], "author_type": r["author_type"], "GT": r["GT"],
            "Original_Verifact_O": source[r["proposition_id"]],
            "U2": r["U2"], "U2_A_all40_LOPO": r["A_all40"],
        })

    if len(common) != 3675 or len({r["subject_id"] for r in common}) != 40:
        raise ValueError("unexpected 034 cohort size")

    scopes = {"all": common,
              "human": [r for r in common if r["author_type"] == "human"],
              "llm": [r for r in common if r["author_type"] == "llm"]}
    for partition in sorted({r["partition"] for r in common}):
        scopes[f"partition:{partition}"] = [r for r in common if r["partition"] == partition]
    metrics, table, predictions, cohorts = {}, [], {}, {}
    for scope, selected in scopes.items():
        metrics[scope], predictions[scope] = {}, {}
        for method in METHODS:
            cohort, pred, metric = make_eval(selected, method)
            cohorts[scope] = cohort
            predictions[scope][method] = pred
            metrics[scope][method] = metric
            table.append(metric_row(scope, method, metric))

    pairs = {}
    comparisons = [
        ("U2_minus_Original_Verifact_O", "Original_Verifact_O", "U2"),
        ("A_all40_minus_U2", "U2", "U2_A_all40_LOPO"),
        ("A_all40_minus_Original_Verifact_O", "Original_Verifact_O", "U2_A_all40_LOPO"),
    ]
    for scope in ("all", "human", "llm"):
        pairs[scope] = {}
        for name, baseline, candidate in comparisons:
            pairs[scope][name] = paired_compare(
                cohorts[scope], predictions[scope][baseline], predictions[scope][candidate], iterations=1000
            )

    write_csv(OUT / "predictions_common.csv", common)
    write_csv(OUT / "metrics.csv", table)
    write_json(OUT / "metrics.json", metrics)
    write_json(OUT / "paired.json", pairs)
    summary = {
        "cohort": {"n": len(common), "patients": len({r["subject_id"] for r in common}),
                   "human": len(scopes["human"]), "llm": len(scopes["llm"]),
                   "original_verifact_coverage": len(common)},
        "methods": list(METHODS),
        "primary_scope": "all",
        "original_verifact_configuration": "R1-70B + 100 sentence facts, valid-only release predictions from task 002",
        "gate_configuration": "033 A_all40 patient-out/LOPO predictions; each evaluated development patient excluded from its Gate training",
    }
    write_json(OUT / "summary.json", summary)

    all_rows = {r["method"]: r for r in table if r["scope"] == "all"}
    labels = {"Original_Verifact_O": "原VeriFact O", "U2": "U2（固定lambda=2）",
              "U2_A_all40_LOPO": "U2 + A全40 Gate（患者外）"}
    lines = [
        "# 034：原 VeriFact、U2 与 U2+A全40 的严格同ID离线比较", "",
        "## 结论", "",
        "在033的40名development、3675条valid atomic claims上，002保存的原VeriFact R1-70B预测实现3675/3675完整同ID覆盖。",
        "本任务不调用API、不重新训练Judge，仅把原VeriFact预测与033冻结的U2及A全40患者外预测连接后，使用项目统一002评价代码重算。",
        "", "| 方法 | 正确/N | PA | MCC | AC1 | false-S |", "|---|---:|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        r = all_rows[method]
        lines.append(f"| {labels[method]} | {r['correct']}/{r['n']} | {r['PA']:.2%} | {r['MCC']:.4f} | {r['AC1']:.4f} | {r['false_S']} |")
    po = pairs["all"]["U2_minus_Original_Verifact_O"]["metrics"]
    pu = pairs["all"]["A_all40_minus_U2"]["metrics"]
    pa = pairs["all"]["A_all40_minus_Original_Verifact_O"]["metrics"]
    lines += ["", "## 核心比较", "",
        f"- U2相对原VeriFact：PA {po['percent_agreement']['delta']*100:+.3f}个百分点，MCC {po['mcc']['delta']:+.4f}；"
        f"95%患者bootstrap区间分别为 [{po['percent_agreement']['ci95'][0]*100:+.3f},{po['percent_agreement']['ci95'][1]*100:+.3f}]个百分点、"
        f"[{po['mcc']['ci95'][0]:+.4f},{po['mcc']['ci95'][1]:+.4f}]。",
        f"- A全40 Gate相对U2：PA {pu['percent_agreement']['delta']*100:+.3f}个百分点，MCC {pu['mcc']['delta']:+.4f}；"
        f"95%区间分别为 [{pu['percent_agreement']['ci95'][0]*100:+.3f},{pu['percent_agreement']['ci95'][1]*100:+.3f}]个百分点、"
        f"[{pu['mcc']['ci95'][0]:+.4f},{pu['mcc']['ci95'][1]:+.4f}]。",
        f"- A全40 Gate相对原VeriFact：PA {pa['percent_agreement']['delta']*100:+.3f}个百分点，MCC {pa['mcc']['delta']:+.4f}；"
        f"95%区间分别为 [{pa['percent_agreement']['ci95'][0]*100:+.3f},{pa['percent_agreement']['ci95'][1]*100:+.3f}]个百分点、"
        f"[{pa['mcc']['ci95'][0]:+.4f},{pa['mcc']['ci95'][1]:+.4f}]。",
        "", "## 作者分层", "",
        "| 作者 | 方法 | 正确/N | PA | MCC | false-S |", "|---|---|---:|---:|---:|---:|",
    ]
    for scope in ("human", "llm"):
        scoped = {r["method"]: r for r in table if r["scope"] == scope}
        for method in METHODS:
            r = scoped[method]
            lines.append(f"| {scope} | {labels[method]} | {r['correct']}/{r['n']} | {r['PA']:.2%} | {r['MCC']:.4f} | {r['false_S']} |")
    lines += ["", "## 解释边界", "",
        "- 原VeriFact O使用002保存的发布预测：R1-70B、100 sentence facts、valid-only。",
        "- U2与A Gate使用033保存的当前链路预测，因此这是同一GT/同一ID上的系统级比较，不是固定相同reference/Judge的纯组件因果实验。",
        "- A全40主比较使用033的患者外/LOPO预测：评价某位development患者时，该患者未进入对应Gate训练；不是把全40最终模型直接在训练本人上打分。",
        "- 原VeriFact在本3675条上覆盖完整，因此主表无需available-case删样本。",
        "- 本任务只做离线连接和统一重评，不使用reserved40。",
        "", "机器结果：metrics.csv/json、paired.json、predictions_common.csv。"]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {"inputs": {str(p.relative_to(ROOT)): sha256(p) for p in (P033, O_H, O_L)}, "outputs": {}}
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name != "manifest.json":
            manifest["outputs"][p.name] = sha256(p)
    write_json(OUT / "manifest.json", manifest)
    print(f"034 complete: {len(common)} rows, 40 patients")


if __name__ == "__main__":
    main()
