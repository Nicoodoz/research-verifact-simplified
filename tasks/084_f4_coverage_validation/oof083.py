"""Describe frozen 083 OOF predictions without fitting or selecting models."""
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
SOURCE = ROOT / "outputs/083_native_rationale_information"
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.evaluation import evaluate

LABELS = ("Supported", "Not Supported", "Not Addressed")


def readjson(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def lines(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = SOURCE / "oof_predictions.jsonl"
    rows = lines(source)
    frozen = readjson(SOURCE / "models_frozen.json")
    folds = lines(SOURCE / "fold_manifest.jsonl")
    assert len(rows) == 459 * 6 * 3 and len(folds) == 14
    result = []
    for arm in ("N", "C", "T", "G", "R", "P"):
        for c in (0.03, 0.3, 3.0):
            take = [x for x in rows if x["arm"] == arm and x["C"] == c]
            assert len(take) == 459 == len({x["id"] for x in take})
            assert all(x["prediction"] == LABELS[max(range(3), key=lambda k: x["prob"][k])] for x in take)
            cohort = [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in take]
            pred = [{"proposition_id": x["id"], "verdict": x["prediction"]} for x in take]
            ev = evaluate(cohort, pred, profile="none", missing="error")
            true = Counter(x["GT"] for x in take)
            predicted = Counter(x["prediction"] for x in take)
            fold_summary = []
            for fold in folds:
                held = [x for x in take if x["sid"] == fold["heldout_patient"]]
                assert len(held) == fold["held_n"]
                fold_summary.append({"sid": fold["heldout_patient"], "n": len(held),
                                     "true": dict(Counter(x["GT"] for x in held)),
                                     "predicted": dict(Counter(x["prediction"] for x in held))})
            nll = sum(-math.log(max(x["prob"][LABELS.index(x["GT"])], 1e-12)) for x in take) / len(take)
            weighted = next(z["oof_weighted_nll"] for z in frozen["selection"][arm]["candidates"] if z["C"] == c)
            result.append({"arm": arm, "C": c, "selected": c == frozen["selection"][arm]["chosen_C"],
                           "weighted_NLL_selection": weighted, "unweighted_NLL": nll,
                           "n": len(take), "correct": sum(x["GT"] == x["prediction"] for x in take),
                           "PA": ev["percent_agreement"], "MCC": ev["mcc"], "AC1": ev["gwet_ac1"],
                           "macro_F1": sum((ev["per_class"][k]["f1"] or 0) for k in LABELS) / 3,
                           "confusion_matrix": ev["confusion_matrix"],
                           "true": {k: true[k] for k in LABELS}, "predicted": {k: predicted[k] for k in LABELS},
                           "recall": {k: ev["per_class"][k]["recall"] for k in LABELS},
                           "false_S": sum(x["GT"] != LABELS[0] and x["prediction"] == LABELS[0] for x in take),
                           "nonS_denominator": sum(x["GT"] != LABELS[0] for x in take),
                           "NS_probability_min": min(x["prob"][1] for x in take),
                           "NS_probability_mean": sum(x["prob"][1] for x in take) / len(take),
                           "folds": fold_summary})
    assert len(result) == 18
    artifact = {"source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                  (source, SOURCE / "fold_manifest.jsonl", SOURCE / "models_frozen.json")},
                "candidates": result}
    (OUT / "083_oof_diagnosis.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md = ["# 083 冻结 OOF 诊断（零API、零重训）", "", "459条／14患者，全部18个预设 arm×C；OOF仅用于原083选参，不是独立外测。类别顺序 S/NS/NA。", "",
          "|臂|C|原选参加权NLL|普通NLL|正确|PA|MCC|Macro-F1|预测 S/NS/NA|召回 S/NS/NA|错误支持/非S|零NS折|", "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|"]
    for x in result:
        ps = "/".join(str(x["predicted"][k]) for k in LABELS)
        rs = "/".join(f"{100*x['recall'][k]:.1f}%" for k in LABELS)
        zero = sum(f["predicted"].get(LABELS[1], 0) == 0 for f in x["folds"])
        md.append(f"|{x['arm']}{'*' if x['selected'] else ''}|{x['C']:g}|{x['weighted_NLL_selection']:.4f}|{x['unweighted_NLL']:.4f}|{x['correct']}|{x['PA']:.4f}|{x['MCC']:.4f}|{x['macro_F1']:.4f}|{ps}|{rs}|{x['false_S']}/{x['nonS_denominator']}|{zero}/14|")
    md += ["", "星号为083原先已冻结的赢家；完整混淆矩阵和逐折真/预测分布见JSON，未在此重选。", ""]
    for x in result:
        if x["selected"]:
            zero = [f["sid"] for f in x["folds"] if f["predicted"].get(LABELS[1], 0) == 0]
            md.append(f"- {x['arm']} 选中C={x['C']:g}：零NS预测折 {len(zero)}/14：{', '.join(zero) if zero else '无'}；NS概率最小 {x['NS_probability_min']:.6g}，平均 {x['NS_probability_mean']:.4f}。")
    (OUT / "083_oof_diagnosis.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"candidates": len(result), "selected": {x["arm"]: {"correct": x["correct"], "NS_pred": x["predicted"][LABELS[1]], "false_S": x["false_S"]} for x in result if x["selected"]}}))


if __name__ == "__main__":
    main()
