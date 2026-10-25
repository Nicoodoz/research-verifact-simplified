"""Create a static paired-effect and label-scale figure from frozen evaluation results."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import inventory082 as i
import run082 as r

OUT = i.OUT


def main():
    results = r.read(OUT / "evaluation_results.json")
    models = r.read(OUT / "models_frozen.json")
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    comparison = ("B:PriorG", "F4:selected_R")
    colors = {"old352": "#3366aa", "new180": "#bb6633", "combined532": "#337755"}
    for shift, cohort in enumerate(("old352", "new180", "combined532")):
        item = next(x for x in results["paired"][cohort]
                    if (x["base"], x["candidate"]) == comparison)
        d = item["metrics"]["mcc"]
        x = shift
        axes[0].vlines(x, d["ci95"][0], d["ci95"][1], color=colors[cohort], linewidth=2)
        axes[0].hlines(d["ci95"], x - 0.07, x + 0.07, color=colors[cohort], linewidth=2)
        axes[0].scatter([x], [d["delta"]], color=colors[cohort], label=cohort, zorder=3)
    axes[0].axhline(0, color="0.45", linewidth=1)
    axes[0].set_xticks(range(3), ["Historical 352", "Added 180", "Combined 532"], rotation=14)
    axes[0].set_ylabel("Paired ΔMCC vs current B + PriorG")
    axes[0].set_title("Training-selected F4 system")
    axes[0].grid(axis="y", alpha=0.25)
    metrics = {(x["config"], x["method"]): x for x in results["metrics"]["combined532"]}
    for seed, color in ((0, "#3366aa"), (1, "#bb6633")):
        x, y = [], []
        for size in (7, 14):
            curve = next(v for v in models["learning_curve_models"] if v["seed"] == seed and v["per_patient"] == size)
            x.append(curve["n"])
            y.append(metrics["F4", f"curve_s{seed}_{size}"]["MCC"])
        full = next(v for v in models["learning_curve_models"] if v["seed"] == seed and v["per_patient"] == 22)
        x.append(full["n"])
        y.append(metrics["F4", "independent_R"]["MCC"])
        axes[1].plot(x, y, marker="o", color=color, label=f"Fixed subset seed {seed}")
    axes[1].axhline(metrics["F4", "PriorG"]["MCC"], color="0.45", linestyle="--", label="F4 + Frozen PriorG")
    axes[1].set_xlabel("Paired calibration claims")
    axes[1].set_ylabel("F4 MCC on the same combined 532")
    axes[1].set_title("Independent scaling learning curve")
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=8)
    figure.savefig(OUT / "figure_082.png", dpi=180)
    figure.savefig(OUT / "figure_082.svg")
    plt.close(figure)
    print("figure_082.png and figure_082.svg saved")


if __name__ == "__main__":
    main()
