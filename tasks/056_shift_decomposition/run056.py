from pathlib import Path
from collections import Counter
import argparse, csv, hashlib, json, math, subprocess, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/056_shift_decomposition"
T055 = ROOT / "outputs/055_zero_label_policy_adaptation"
T054 = ROOT / "outputs/054_unlabeled_prior_shift"
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
import common053 as c53

LABELS = list(c53.LABELS)
K = 3
SOURCE_COUNTS = np.array([1108.0, 100.0, 170.0])
SOURCE_PRIOR = SOURCE_COUNTS / SOURCE_COUNTS.sum()
CAL_COUNTS = np.array([48.0, 47.0, 48.0])
CAL_PRIOR = CAL_COUNTS / CAL_COUNTS.sum()
G = float(c53.read(ROOT / "outputs/053_thinking_prior_validation/freeze.json")
          ["calibration_theta"]["T-S"]["G"][0])
SCENARIOS = {
    "source": SOURCE_PRIOR,
    "high_S": np.array([.90, .05, .05]),
    "S70": np.array([.70, .15, .15]),
    "S60": np.array([.60, .20, .20]),
    "NS_heavy": np.array([.60, .30, .10]),
    "NA_heavy": np.array([.60, .10, .30]),
}
BATCH_SIZES = (60, 120, 240, 480)
CAL_REPS, EVAL_REPS, ACTUAL_NULL_REPS = 1000, 500, 2000
SEED = 20260922056

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]

def csvwrite(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def put(path, obj):
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

def base_logits(scores):
    z = np.log(np.maximum(
        np.array([float(scores[k]) / 100 for k in LABELS]), 1e-6))
    z[0] += G
    return z

def posterior(z, prior):
    z = np.asarray(z, float) + np.log(np.maximum(prior, 1e-12) / CAL_PRIOR)
    z -= np.max(z)
    e = np.exp(z)
    return e / e.sum()

def ds_frozen(scores):
    return int(np.argmax(posterior(base_logits(scores), SOURCE_PRIOR)))

def qwen_u0(scores):
    return LABELS.index(c53.decision(scores, 0))

class SimplexLS:
    def __init__(self, C):
        self.C = np.asarray(C, float)
        self.solvers = []
        for mask in range(1, 1 << K):
            idx = [i for i in range(K) if mask & (1 << i)]
            A = self.C[:, idx]
            H = 2 * (A.T @ A)
            one = np.ones((len(idx), 1))
            M = np.block([[H, one], [one.T, np.zeros((1, 1))]])
            self.solvers.append((idx, A, np.linalg.pinv(M)))

    def solve(self, q):
        q = np.asarray(q, float)
        best = None
        for idx, A, pinv in self.solvers:
            rhs = np.r_[2 * (A.T @ q), 1.0]
            x = pinv @ rhs
            psub = x[:-1]
            if np.min(psub) < -1e-9:
                continue
            p = np.zeros(K)
            p[idx] = np.maximum(psub, 0)
            p /= p.sum()
            loss = float(np.sum((self.C @ p - q) ** 2))
            if best is None or loss < best[0]:
                best = (loss, p)
        if best is None:
            raise RuntimeError("simplex LS failed")
        return best[1]

def hard_dist(v, n_states=3):
    return np.bincount(np.asarray(v, int), minlength=n_states) / len(v)

def tv(p, q):
    return 0.5 * float(np.sum(np.abs(np.asarray(p) - np.asarray(q))))

def js(p, q):
    p, q = np.asarray(p, float), np.asarray(q, float)
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log(a[mask] / np.maximum(b[mask], 1e-15))))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)

def load_pool(tag):
    rows = read_jsonl(T055 / f"features_qwen_{tag}.jsonl")
    out = []
    for x in rows:
        y = LABELS.index(x["GT"])
        d = ds_frozen(x["ts_scores"])
        q = qwen_u0(x["qwen_scores"])
        out.append({
            "id": x["id"], "sid": str(x["sid"]), "author": x["author"],
            "y": y, "d": d, "q": q, "joint": d * K + q,
        })
    return out

def matrices(rows):
    Cds = np.zeros((K, K), float)
    Cq = np.zeros((K, K), float)
    Cjoint = np.zeros((K * K, K), float)
    for r in rows:
        Cds[r["d"], r["y"]] += 1
        Cq[r["q"], r["y"]] += 1
        Cjoint[r["joint"], r["y"]] += 1
    for C in (Cds, Cq, Cjoint):
        den = C.sum(axis=0, keepdims=True)
        if np.any(den == 0):
            raise RuntimeError("missing class in source pool")
        C /= den
    return Cds, Cq, Cjoint

def alloc(prior, n):
    x = np.asarray(prior) * n
    base = np.floor(x).astype(int)
    left = int(n - base.sum())
    order = np.argsort(-(x - base), kind="stable")
    for i in order[:left]:
        base[i] += 1
    return base

def sample_arrays(rows, prior, n, rng):
    yall = np.array([r["y"] for r in rows], int)
    by = [np.where(yall == k)[0] for k in range(K)]
    idx = []
    for k, count in enumerate(alloc(prior, n)):
        idx.extend(rng.choice(by[k], size=int(count), replace=True).tolist())
    rng.shuffle(idx)
    rr = [rows[i] for i in idx]
    return (
        np.array([r["d"] for r in rr], int),
        np.array([r["q"] for r in rr], int),
        np.array([r["joint"] for r in rr], int),
    )

def score_unlabeled(d, q, joint, Cds, Cq, Cjoint):
    pi_ds = SimplexLS(Cds).solve(hard_dist(d, K))
    pi_q = SimplexLS(Cq).solve(hard_dist(q, K))
    observed = hard_dist(joint, K * K)
    expected = Cjoint @ pi_ds
    return dict(pi_ds=pi_ds, pi_q=pi_q,
                prior_disagreement=float(np.sum(np.abs(pi_ds-pi_q))),
                joint_tv=tv(observed, expected),
                joint_js=js(observed, expected),
                observed=observed, expected=expected)

def null_tvs(source_rows, prior, n, Cds, Cq, Cjoint, reps, rng):
    vals = np.empty(reps, float)
    for i in range(reps):
        d, q, j = sample_arrays(source_rows, prior, n, rng)
        vals[i] = score_unlabeled(d, q, j, Cds, Cq, Cjoint)["joint_tv"]
    return vals

def actual_unlabeled(source_rows, target_rows, rng):
    Cds, Cq, Cjoint = matrices(source_rows)
    d = np.array([r["d"] for r in target_rows], int)
    q = np.array([r["q"] for r in target_rows], int)
    j = np.array([r["joint"] for r in target_rows], int)
    res = score_unlabeled(d, q, j, Cds, Cq, Cjoint)
    null = null_tvs(
        source_rows, res["pi_ds"], len(target_rows),
        Cds, Cq, Cjoint, ACTUAL_NULL_REPS, rng)
    threshold = float(np.quantile(null, .95))
    pvalue = float((1 + np.sum(null >= res["joint_tv"])) / (len(null) + 1))
    return res, threshold, pvalue, Cds, Cq, Cjoint

def stress_one(source_rows, alt_rows, prior, n, rng):
    Cds, Cq, Cjoint = matrices(source_rows)
    cal = null_tvs(source_rows, prior, n, Cds, Cq, Cjoint, CAL_REPS, rng)
    threshold = float(np.quantile(cal, .95))
    h0_tvs, h1_tvs, h0_l1, h1_l1 = [], [], [], []
    for _ in range(EVAL_REPS):
        for pool, tvs, l1s in (
            (source_rows, h0_tvs, h0_l1),
            (alt_rows, h1_tvs, h1_l1),
        ):
            d, q, j = sample_arrays(pool, prior, n, rng)
            r = score_unlabeled(d, q, j, Cds, Cq, Cjoint)
            tvs.append(r["joint_tv"])
            l1s.append(float(np.sum(np.abs(r["pi_ds"] - prior))))
    return {
        "threshold95": threshold,
        "h0_false_alarm": float(np.mean(np.array(h0_tvs) > threshold)),
        "h1_detection": float(np.mean(np.array(h1_tvs) > threshold)),
        "h0_tv_mean": float(np.mean(h0_tvs)),
        "h1_tv_mean": float(np.mean(h1_tvs)),
        "h0_bbse_l1_mean": float(np.mean(h0_l1)),
        "h1_bbse_l1_mean": float(np.mean(h1_l1)),
    }

def git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def freeze():
    inputs = {
        "features_qwen_052": T055 / "features_qwen_052.jsonl",
        "features_qwen_053": T055 / "features_qwen_053.jsonl",
        "source_cv_qwen_labelmodel_actual": T055 / "source_cv_qwen_labelmodel_actual.csv",
    }
    obj = {
        "git_head": git_head(),
        "seed": SEED,
        "cal_reps": CAL_REPS,
        "eval_reps": EVAL_REPS,
        "actual_null_reps": ACTUAL_NULL_REPS,
        "scenarios": {k: v.tolist() for k, v in SCENARIOS.items()},
        "batch_sizes": list(BATCH_SIZES),
        "protocol_sha256": sha256(ROOT / "tasks/056_shift_decomposition/protocol.md"),
        "code_sha256": sha256(Path(__file__)),
        "inputs": {k: {"path": str(v.relative_to(ROOT)), "sha256": sha256(v)}
                   for k, v in inputs.items()},
    }
    put(OUT / "freeze.json", obj)
    return obj

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def self_test():
    p = np.array([.6, .25, .15])
    C = np.array([[.8,.2,.1],[.1,.6,.2],[.1,.2,.7]])
    est = SimplexLS(C).solve(C @ p)
    if np.max(np.abs(est - p)) > 1e-8:
        raise AssertionError(("simplex solver", est, p))
    pools = {k: load_pool(k) for k in ("052", "053")}
    if len(pools["052"]) != 236 or len(pools["053"]) != 237:
        raise AssertionError("unexpected pool sizes")
    for tag, rows in pools.items():
        if len({r["id"] for r in rows}) != len(rows):
            raise AssertionError(f"duplicate ids in {tag}")
        Cds, Cq, Cj = matrices(rows)
        if Cds.shape != (3,3) or Cq.shape != (3,3) or Cj.shape != (9,3):
            raise AssertionError("matrix shape")
        if not np.allclose(Cds.sum(axis=0), 1):
            raise AssertionError("DS columns")
        if not np.allclose(Cj.sum(axis=0), 1):
            raise AssertionError("joint columns")
    print("056 SELF-TEST PASS", {k: len(v) for k,v in pools.items()})

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("freeze.json", "actual_unlabeled.csv", "simulation_summary.csv"):
        if (OUT / name).exists():
            raise RuntimeError(f"formal output already exists: {name}")
    fr = freeze()
    pools = {k: load_pool(k) for k in ("052", "053")}
    rng = np.random.default_rng(SEED)
    actual_rows, eval_rows = [], []
    actual_cache = {}
    for source, target in (("052","053"), ("053","052")):
        srows, trows = pools[source], pools[target]
        res, threshold, pvalue, Cds, Cq, Cjoint = actual_unlabeled(srows, trows, rng)
        row = {
            "source": source, "target": target, "target_n": len(trows),
            "pi_ds_S": res["pi_ds"][0], "pi_ds_NS": res["pi_ds"][1],
            "pi_ds_NA": res["pi_ds"][2],
            "pi_q_S": res["pi_q"][0], "pi_q_NS": res["pi_q"][1],
            "pi_q_NA": res["pi_q"][2],
            "prior_disagreement_L1": res["prior_disagreement"],
            "joint_tv": res["joint_tv"], "joint_js": res["joint_js"],
            "null_q95": threshold, "null_pvalue": pvalue,
            "alarm": bool(res["joint_tv"] > threshold),
            "Cds_condition": float(np.linalg.cond(Cds)),
            "Cq_condition": float(np.linalg.cond(Cq)),
            "observed_joint": json.dumps(res["observed"].tolist()),
            "expected_joint": json.dumps(res["expected"].tolist()),
        }
        actual_rows.append(row)
        actual_cache[(source,target)] = (res, threshold, pvalue)
    csvwrite(OUT / "actual_unlabeled.csv", actual_rows)
    blind_sha = sha256(OUT / "actual_unlabeled.csv")

    adapt = {
        (r["source"], r["target"]): r
        for r in read_csv(T055 / "source_cv_qwen_labelmodel_actual.csv")
    }
    for source, target in (("052","053"), ("053","052")):
        trows = pools[target]
        true = np.bincount([r["y"] for r in trows], minlength=K) / len(trows)
        res, threshold, pvalue = actual_cache[(source,target)]
        a = adapt[(source,target)]
        eval_rows.append({
            "source": source, "target": target,
            "true_S": true[0], "true_NS": true[1], "true_NA": true[2],
            "ds_BBSE_L1": float(np.sum(np.abs(res["pi_ds"] - true))),
            "qwen_BBSE_L1": float(np.sum(np.abs(res["pi_q"] - true))),
            "alarm": bool(res["joint_tv"] > threshold),
            "labelmodel_delta_PA": float(a["target_PA"]) - float(a["PG_PA"]),
            "labelmodel_delta_MCC": float(a["target_MCC"]) - float(a["PG_MCC"]),
            "labelmodel_delta_falseS": int(a["target_falseS"]) - int(a["PG_falseS"]),
            "labelmodel_delta_NS_recall": float(a["target_NS"]) - float(a["PG_NS"]),
            "labelmodel_delta_NA_recall": float(a["target_NA"]) - float(a["PG_NA"]),
        })
    csvwrite(OUT / "actual_evaluation.csv", eval_rows)

    sim_rows = []
    for source, alt in (("052","053"), ("053","052")):
        for scenario, prior in SCENARIOS.items():
            for n in BATCH_SIZES:
                r = stress_one(pools[source], pools[alt], prior, n, rng)
                sim_rows.append({
                    "source": source, "conditional_alt": alt,
                    "scenario": scenario, "batch_n": n,
                    **r,
                })
                print("056", source, "vs", alt, scenario, n, r, flush=True)
    csvwrite(OUT / "simulation_summary.csv", sim_rows)

    screen_rows = []
    for source in ("052","053"):
        rows = [r for r in sim_rows if r["source"] == source and r["batch_n"] == 240]
        fpr = float(np.mean([r["h0_false_alarm"] for r in rows]))
        tpr = float(np.mean([r["h1_detection"] for r in rows]))
        passed = bool(fpr <= .10 and tpr >= .70)
        screen_rows.append({
            "source": source, "batch_n": 240,
            "mean_h0_false_alarm": fpr,
            "mean_h1_detection": tpr,
            "pass": passed,
        })
    csvwrite(OUT / "screen_summary.csv", screen_rows)
    overall_pass = all(r["pass"] for r in screen_rows)

    run = {
        "status": "PASS",
        "git_head": fr["git_head"],
        "new_api_calls": 0,
        "reserved_used": False,
        "actual_unlabeled_sha256_before_gt_evaluation": blind_sha,
        "pools": {k: len(v) for k,v in pools.items()},
        "actual": actual_rows,
        "screen": screen_rows,
        "mechanism_screen_pass": overall_pass,
    }
    put(OUT / "run_summary.json", run)
    write_report(actual_rows, eval_rows, sim_rows, screen_rows, overall_pass)
    print("056 COMPLETE", json.dumps(screen_rows, ensure_ascii=False))

def write_report(actual_rows, eval_rows, sim_rows, screen_rows, overall_pass):
    lines = [
        "# 056：Unlabeled Shift Decomposition",
        "",
        "## 核心问题",
        "",
        "target完全无GT时，能否先用BBSE估prevalence，再用DeepSeek×Qwen联合输出判断当前变化是否仍符合纯label shift。",
        "",
        "主残差：TV(observed target joint outputs, source P(D,Q|Y) × BBSE pi_hat)。阈值来自source纯label-shift重采样95%分位。",
        "",
        "## 真实052↔053无标签诊断",
        "",
        "| source→target | DS-BBSE pi(S/NS/NA) | DS-Qwen prior L1差 | joint TV | H0 q95 | p | alarm |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in actual_rows:
        pi = f'{r["pi_ds_S"]:.3f}/{r["pi_ds_NS"]:.3f}/{r["pi_ds_NA"]:.3f}'
        lines.append(
            f'| {r["source"]}→{r["target"]} | {pi} | {r["prior_disagreement_L1"]:.3f} | '
            f'{r["joint_tv"]:.3f} | {r["null_q95"]:.3f} | {r["null_pvalue"]:.4f} | {r["alarm"]} |')
    lines += [
        "",
        "上述alarm计算不读取target GT；actual_unlabeled.csv先写入并记录哈希，随后才生成下面的GT评价。",
        "",
        "## 解盲后评价与055关联",
        "",
        "| source→target | true pi | DS-BBSE L1 | Qwen-BBSE L1 | 055 label-model ΔPA | ΔMCC | Δfalse-S | ΔNS recall | alarm |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in eval_rows:
        pi = f'{r["true_S"]:.3f}/{r["true_NS"]:.3f}/{r["true_NA"]:.3f}'
        lines.append(
            f'| {r["source"]}→{r["target"]} | {pi} | {r["ds_BBSE_L1"]:.3f} | {r["qwen_BBSE_L1"]:.3f} | '
            f'{r["labelmodel_delta_PA"]:+.3f} | {r["labelmodel_delta_MCC"]:+.3f} | '
            f'{r["labelmodel_delta_falseS"]:+d} | {r["labelmodel_delta_NS_recall"]:+.3f} | {r["alarm"]} |')
    lines += [
        "",
        "## 纯label shift vs conditional replacement压力测试",
        "",
        "| source | n=240平均H0 false-alarm | n=240平均H1 detection | 事前门槛 |",
        "|---|---:|---:|---|",
    ]
    for r in screen_rows:
        lines.append(
            f'| {r["source"]} | {r["mean_h0_false_alarm"]:.3f} | '
            f'{r["mean_h1_detection"]:.3f} | {"PASS" if r["pass"] else "FAIL"} |')
    n240 = [r for r in sim_rows if r["batch_n"] == 240]
    lines += [
        "",
        "H0只改变类别比例并保持source类条件Judge行为；H1保持同一类别比例，但把类条件DeepSeek×Qwen行为替换为另一批真实观测行为。",
        "",
        "## 结论",
        "",
    ]
    if overall_pass:
        lines += [
            "**056机制screen通过。** 在事前标准下，联合输出残差能在控制纯label-shift误报的同时识别跨批次conditional behavior replacement。",
            "",
            "因此下一步可进入057：让该alarm只负责控制是否启用zero-label adaptation，而不是直接估完整target confusion matrix。",
        ]
    else:
        lines += [
            "**056机制screen未通过。** 当前DeepSeek+Qwen无标签联合输出不足以稳定区分纯label shift与conditional behavior replacement。",
            "",
            "按事前边界不应继续调同一detector；优先考虑few-label target reliability calibration，而不是继续堆zero-label动态机制。",
        ]
    lines += [
        "",
        "## 边界",
        "",
        "- 052/053都是development内部claim批次，不是外部医院或新数据集。",
        "- H1是利用另一批真实P(D,Q|Y)做conditional replacement的压力测试，不等于真实部署漂移的完整生成过程。",
        "- 056只做shift diagnosis，不修改final label，不宣称解决zero-label adaptation。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    else:
        main()
