"""Compact deterministic result display to support the Chinese report."""
import json
from pathlib import Path

out = Path("outputs/082_anchor_configuration_adaptation")
r = json.loads((out / "evaluation_results.json").read_text(encoding="utf-8"))
methods = [("B", "PriorG"), ("F4", "PriorG"), ("B", "independent_R"),
           ("F4", "independent_R"), ("F4", "shared_R"), ("F4", "adapted_R"),
           ("F4", "independent_E"), ("F4", "independent_old112")]
for cohort in ("old352", "new180", "combined532"):
    lookup = {(x["config"], x["method"]): x for x in r["metrics"][cohort]}
    print("COHORT", cohort, r["cohorts"][cohort], "original", r["original_verifact"][cohort]["correct"])
    for arm, method in methods:
        x = lookup[arm, method]
        print(arm, method, "correct", x["correct"], "MCC", round(x["MCC"], 5),
              "PA", round(x["PA"], 5), "MacroF1", round(x["macro_F1"], 5),
              "falseS", x["false_S"], "NSrecall", round(x["per_class"]["Not Supported"]["recall"], 5),
              "NArecall", round(x["per_class"]["Not Addressed"]["recall"], 5))
    for x in r["paired"][cohort]:
        if (x["base"], x["candidate"]) in {
            ("B:PriorG", "F4:PriorG"), ("B:PriorG", "F4:selected_R"),
            ("F4:independent_R", "F4:adapted_R"), ("F4:independent_R", "F4:independent_E"),
            ("F4:independent_old112", "F4:independent_R"),
            ("B:independent_R", "F4:independent_R"),
        }:
            print("PAIR", x["base"], "->", x["candidate"], "net", x["net"],
                  "rescue", x["rescue"], "harm", x["harm"], "patient", x["patient_wins"], x["patient_losses"],
                  "dMCC", round(x["metrics"]["mcc"]["delta"], 5),
                  "CI", [round(z, 5) for z in x["metrics"]["mcc"]["ci95"]],
                  "dPA", round(x["metrics"]["percent_agreement"]["delta"], 5),
                  "dFalseS", x["delta_false_S"])
    if cohort == "combined532":
        for seed in (0, 1):
            for size in (7, 14):
                key = ("F4", f"curve_s{seed}_{size}")
                x = lookup[key]
                print("CURVE", seed, size, x["correct"], round(x["MCC"], 5), x["false_S"])
        for arm, method in (("B", "PriorG"), ("F4", "PriorG"),
                            ("F4", "independent_R"), ("F4", "adapted_R")):
            print("CONFUSION", arm, method, lookup[arm, method]["confusion_matrix"])
        print("SAME_SCORE_CONFLICTS", {k: (len(v), sum(x["n"] for x in v))
                                       for k, v in r["same_score_different_GT"].items()})
