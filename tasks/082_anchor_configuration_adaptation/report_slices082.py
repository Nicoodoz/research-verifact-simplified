"""Print compact secondary findings for human report drafting; no fitting or API."""
import json
from pathlib import Path

o = Path("outputs/082_anchor_configuration_adaptation")
load = lambda n: json.loads((o / n).read_text(encoding="utf-8"))
r = load("evaluation_results.json")
for name in ("old352", "new180", "combined532"):
    print("AUTHORS", name, r["by_author"][name])
    matches = [x for x in r["paired"][name] if (x["base"], x["candidate"]) in {
        ("F4:PriorG", "F4:adapted_R"), ("B:PriorG", "B:adapted_R"),
        ("F4:PriorG", "F4:independent_R"), ("F4:independent_R", "F4:shared_R")
    }]
    print("OTHER_PAIRS", name, [(x["base"], x["candidate"], x["net"], x["rescue"], x["harm"],
                                 x["patient_wins"], x["patient_losses"], x["delta_false_S"],
                                 x["metrics"]["mcc"]) for x in matches])
print("INVALID", r["invalid"])
s = load("sensitivity_results.json")
for name, x in s["groups"].items():
    print("EXPOSURE", name, x["n"], x["patients"],
          [(m["config"], m["method"], m["correct"], round(m["MCC"], 4), m["false_S"])
           for m in x["metrics"]])
c = load("common_core_valid_sensitivity.json")
for name, x in c["groups"].items():
    print("CORE", name, x["common_valid_n"],
          [(m["config"], m["method"], m["correct"], round(m["MCC"], 4), m["false_S"])
           for m in x["metrics"]])
