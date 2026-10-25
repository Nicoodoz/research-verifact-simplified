from pathlib import Path
import csv, hashlib, importlib.util, json, subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/058_unlabeled_batch_scaling"
P057 = ROOT / "tasks/057_soft_shift_detection/run057.py"
spec = importlib.util.spec_from_file_location("r057", P057)
r057 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r057)

BATCHES = (240, 480, 960, 1920, 3840)
SEED = 20260922058

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def csvwrite(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def put(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("freeze.json", "scaling_summary.csv", "aggregate.csv"):
        if (OUT / name).exists():
            raise RuntimeError("formal output exists: " + name)
    fr = {
        "git_head": subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip(),
        "seed": SEED,
        "batches": list(BATCHES),
        "protocol_sha256": sha(ROOT / "tasks/058_unlabeled_batch_scaling/protocol.md"),
        "code_sha256": sha(Path(__file__)),
        "run057_sha256": sha(P057),
        "features_052_sha256": sha(ROOT / "outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl"),
        "features_053_sha256": sha(ROOT / "outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl"),
    }
    put(OUT / "freeze.json", fr)
    pools = {k: r057.load_pool(k) for k in ("052","053")}
    rng = np.random.default_rng(SEED)
    rows = []
    for source, alt in (("052","053"), ("053","052")):
        for scen, prior in r057.SCENARIOS.items():
            for n in BATCHES:
                z = r057.stress_one(pools[source], pools[alt], source, prior, n, rng)
                row = {"source":source,"alt":alt,"scenario":scen,"batch_n":n,**z}
                rows.append(row)
                print("058", source, scen, n, z, flush=True)
    csvwrite(OUT / "scaling_summary.csv", rows)
    agg = []
    for source in ("052","053"):
        for n in BATCHES:
            x = [r for r in rows if r["source"] == source and r["batch_n"] == n]
            agg.append({
                "source":source,
                "batch_n":n,
                "mean_h0_false_alarm":float(np.mean([r["h0_false_alarm"] for r in x])),
                "mean_h1_detection":float(np.mean([r["h1_detection"] for r in x])),
                "min_h1_detection":float(np.min([r["h1_detection"] for r in x])),
                "max_h1_detection":float(np.max([r["h1_detection"] for r in x])),
                "all_scenarios_ge90":bool(all(r["h1_detection"] >= .90 for r in x)),
            })
    csvwrite(OUT / "aggregate.csv", agg)
    put(OUT / "run_summary.json", {
        "status":"PASS","new_api_calls":0,"reserved_used":False,
        "pools":{k:len(v) for k,v in pools.items()},
        "mean90_both_directions": any(
            all(a["mean_h1_detection"] >= .90 and a["mean_h0_false_alarm"] <= .10
                for a in agg if a["batch_n"] == n)
            for n in BATCHES),
        "aggregate":agg,
    })

if __name__ == "__main__":
    main()
