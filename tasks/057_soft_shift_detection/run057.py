from pathlib import Path
import argparse, csv, hashlib, json, math, subprocess, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/057_soft_shift_detection"
O055 = ROOT / "outputs/055_zero_label_policy_adaptation"
O056 = ROOT / "outputs/056_shift_decomposition"
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
RFF_DIM = 128
SEED = 20260922057
VIEWS = ("joint", "ds", "qwen")

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

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
        encoding="utf-8")

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

    def solve_many(self, Q):
        return np.stack([self.solve(q) for q in np.asarray(Q)])

def alloc(prior, n):
    x = np.asarray(prior) * n
    base = np.floor(x).astype(int)
    left = int(n - base.sum())
    order = np.argsort(-(x - base), kind="stable")
    for i in order[:left]:
        base[i] += 1
    return base

def load_pool(tag):
    rows = read_jsonl(O055 / f"features_qwen_{tag}.jsonl")
    out = []
    for x in rows:
        ds = np.array([float(x["ts_scores"][k]) / 100 for k in LABELS], float)
        qw = np.array([float(x["qwen_scores"][k]) / 100 for k in LABELS], float)
        out.append({
            "id": x["id"],
            "sid": str(x["sid"]),
            "author": x["author"],
            "y": LABELS.index(x["GT"]),
            "d": ds_frozen(x["ts_scores"]),
            "x_joint": np.r_[ds, qw],
            "x_ds": ds,
            "x_qwen": qw,
        })
    return out

def confusion_ds(rows):
    C = np.zeros((K, K), float)
    for r in rows:
        C[r["d"], r["y"]] += 1
    C /= C.sum(axis=0, keepdims=True)
    return C

def view_matrix(rows, view):
    key = {"joint": "x_joint", "ds": "x_ds", "qwen": "x_qwen"}[view]
    return np.stack([r[key] for r in rows])

def class_indices(rows):
    y = np.array([r["y"] for r in rows], int)
    return [np.where(y == k)[0] for k in range(K)]

def hard_onehot(rows):
    H = np.zeros((len(rows), K), float)
    for i, r in enumerate(rows):
        H[i, r["d"]] = 1.0
    return H

def stable_seed(source, view):
    h = hashlib.sha256(f"{SEED}:{source}:{view}".encode()).hexdigest()
    return int(h[:8], 16)

class SoftRFF:
    def __init__(self, source_rows, source_tag, view):
        X = view_matrix(source_rows, view)
        self.view = view
        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0)
        self.std[self.std < 1e-8] = 1.0
        Z = (X - self.mean) / self.std
        dif = Z[:, None, :] - Z[None, :, :]
        dist = np.sqrt(np.sum(dif * dif, axis=2))
        nz = dist[np.triu_indices(len(Z), 1)]
        nz = nz[nz > 0]
        self.bandwidth = float(np.median(nz))
        if not np.isfinite(self.bandwidth) or self.bandwidth <= 0:
            raise RuntimeError("invalid RBF bandwidth")
        rng = np.random.default_rng(stable_seed(source_tag, view))
        self.W = rng.normal(
            0.0, 1.0 / self.bandwidth, size=(Z.shape[1], RFF_DIM))
        self.b = rng.uniform(0.0, 2 * np.pi, size=RFF_DIM)
        self.scale = math.sqrt(2.0 / RFF_DIM)
        self.phi_source = self.transform_X(X)
        ys = np.array([r["y"] for r in source_rows], int)
        self.mu_y = np.stack([
            self.phi_source[ys == k].mean(axis=0) for k in range(K)
        ])

    def transform_X(self, X):
        Z = (np.asarray(X, float) - self.mean) / self.std
        return self.scale * np.cos(Z @ self.W + self.b)

    def transform_rows(self, rows):
        return self.transform_X(view_matrix(rows, self.view))

    def residual(self, phi_mean, pi_hat):
        expected = np.asarray(pi_hat) @ self.mu_y
        return float(np.linalg.norm(np.asarray(phi_mean) - expected))

def sample_count_matrix(rows, prior, n, reps, rng):
    by = class_indices(rows)
    counts = np.zeros((reps, len(rows)), dtype=float)
    for k, c in enumerate(alloc(prior, n)):
        probs = np.full(len(by[k]), 1.0 / len(by[k]))
        draws = rng.multinomial(int(c), probs, size=reps)
        counts[:, by[k]] = draws
    return counts

def batch_residuals(rows, prior, n, reps, rng, soft_model, solver):
    counts = sample_count_matrix(rows, prior, n, reps, rng)
    phi = soft_model.transform_rows(rows)
    H = hard_onehot(rows)
    phi_mean = (counts @ phi) / n
    q = (counts @ H) / n
    pi_hat = solver.solve_many(q)
    expected = pi_hat @ soft_model.mu_y
    residual = np.linalg.norm(phi_mean - expected, axis=1)
    l1 = np.sum(np.abs(pi_hat - np.asarray(prior)), axis=1)
    return residual, l1

def actual_score(source_rows, target_rows, source_tag, view, rng):
    Cds = confusion_ds(source_rows)
    solver = SimplexLS(Cds)
    soft = SoftRFF(source_rows, source_tag, view)
    target_phi = soft.transform_rows(target_rows).mean(axis=0)
    q = hard_onehot(target_rows).mean(axis=0)
    pi_hat = solver.solve(q)
    residual = soft.residual(target_phi, pi_hat)
    null, _ = batch_residuals(
        source_rows, pi_hat, len(target_rows), ACTUAL_NULL_REPS,
        rng, soft, solver)
    threshold = float(np.quantile(null, .95))
    pvalue = float((1 + np.sum(null >= residual)) / (len(null) + 1))
    return {
        "view": view,
        "pi_hat": pi_hat,
        "residual": residual,
        "threshold95": threshold,
        "pvalue": pvalue,
        "alarm": bool(residual > threshold),
        "bandwidth": soft.bandwidth,
        "source_C_condition": float(np.linalg.cond(Cds)),
    }

def stress_one(source_rows, alt_rows, source_tag, prior, n, rng):
    Cds = confusion_ds(source_rows)
    solver = SimplexLS(Cds)
    soft = SoftRFF(source_rows, source_tag, "joint")
    cal, _ = batch_residuals(
        source_rows, prior, n, CAL_REPS, rng, soft, solver)
    threshold = float(np.quantile(cal, .95))
    h0, h0_l1 = batch_residuals(
        source_rows, prior, n, EVAL_REPS, rng, soft, solver)
    h1, h1_l1 = batch_residuals(
        alt_rows, prior, n, EVAL_REPS, rng, soft, solver)
    return {
        "threshold95": threshold,
        "h0_false_alarm": float(np.mean(h0 > threshold)),
        "h1_detection": float(np.mean(h1 > threshold)),
        "h0_residual_mean": float(np.mean(h0)),
        "h1_residual_mean": float(np.mean(h1)),
        "h0_bbse_l1_mean": float(np.mean(h0_l1)),
        "h1_bbse_l1_mean": float(np.mean(h1_l1)),
        "bandwidth": soft.bandwidth,
    }

def git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def freeze():
    inputs = {
        "features_qwen_052": O055 / "features_qwen_052.jsonl",
        "features_qwen_053": O055 / "features_qwen_053.jsonl",
        "source_cv_qwen_labelmodel_actual":
            O055 / "source_cv_qwen_labelmodel_actual.csv",
        "hard056_simulation": O056 / "simulation_summary.csv",
        "hard056_actual": O056 / "actual_unlabeled.csv",
    }
    obj = {
        "git_head": git_head(),
        "seed": SEED,
        "rff_dim": RFF_DIM,
        "cal_reps": CAL_REPS,
        "eval_reps": EVAL_REPS,
        "actual_null_reps": ACTUAL_NULL_REPS,
        "batch_sizes": list(BATCH_SIZES),
        "scenarios": {k: v.tolist() for k, v in SCENARIOS.items()},
        "protocol_sha256": sha256(ROOT / "tasks/057_soft_shift_detection/protocol.md"),
        "code_sha256": sha256(Path(__file__)),
        "inputs": {k: {"path": str(v.relative_to(ROOT)), "sha256": sha256(v)}
                   for k, v in inputs.items()},
    }
    put(OUT / "freeze.json", obj)
    return obj

def self_test():
    p = np.array([.6, .25, .15])
    C = np.array([[.8,.2,.1],[.1,.6,.2],[.1,.2,.7]])
    est = SimplexLS(C).solve(C @ p)
    if np.max(np.abs(est - p)) > 1e-8:
        raise AssertionError(("simplex", est, p))
    pools = {k: load_pool(k) for k in ("052", "053")}
    if len(pools["052"]) != 236 or len(pools["053"]) != 237:
        raise AssertionError("pool sizes")
    for tag, rows in pools.items():
        for view in VIEWS:
            m = SoftRFF(rows, tag, view)
            if m.mu_y.shape != (3, RFF_DIM):
                raise AssertionError("embedding shape")
            if not np.isfinite(m.bandwidth) or m.bandwidth <= 0:
                raise AssertionError("bandwidth")
        Cds = confusion_ds(rows)
        if not np.allclose(Cds.sum(axis=0), 1):
            raise AssertionError("confusion columns")
    print("057 SELF-TEST PASS", {k: len(v) for k,v in pools.items()})

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    formal = ["freeze.json", "actual_unlabeled.csv",
              "simulation_summary.csv", "screen_summary.csv"]
    for name in formal:
        if (OUT / name).exists():
            raise RuntimeError(f"formal output already exists: {name}")
    fr = freeze()
    pools = {k: load_pool(k) for k in ("052", "053")}
    rng = np.random.default_rng(SEED)

    actual_rows = []
    actual_cache = {}
    for source, target in (("052","053"), ("053","052")):
        for view in VIEWS:
            r = actual_score(pools[source], pools[target], source, view, rng)
            row = {
                "source": source, "target": target, "target_n": len(pools[target]),
                "view": view,
                "pi_S": r["pi_hat"][0], "pi_NS": r["pi_hat"][1],
                "pi_NA": r["pi_hat"][2],
                "soft_residual": r["residual"],
                "null_q95": r["threshold95"],
                "null_pvalue": r["pvalue"],
                "alarm": r["alarm"],
                "bandwidth": r["bandwidth"],
                "C_condition": r["source_C_condition"],
            }
            actual_rows.append(row)
            actual_cache[(source,target,view)] = r

    csvwrite(OUT / "actual_unlabeled.csv", actual_rows)
    blind_sha = sha256(OUT / "actual_unlabeled.csv")

    adapt = {
        (r["source"], r["target"]): r
        for r in read_csv(O055 / "source_cv_qwen_labelmodel_actual.csv")
    }
    actual_eval = []
    for source, target in (("052","053"), ("053","052")):
        trows = pools[target]
        true = np.bincount([r["y"] for r in trows], minlength=K) / len(trows)
        a = adapt[(source,target)]
        mainr = actual_cache[(source,target,"joint")]
        actual_eval.append({
            "source": source, "target": target,
            "true_S": true[0], "true_NS": true[1], "true_NA": true[2],
            "bbse_L1": float(np.sum(np.abs(mainr["pi_hat"] - true))),
            "joint_alarm": mainr["alarm"],
            "joint_residual": mainr["residual"],
            "labelmodel_delta_PA": float(a["target_PA"]) - float(a["PG_PA"]),
            "labelmodel_delta_MCC": float(a["target_MCC"]) - float(a["PG_MCC"]),
            "labelmodel_delta_falseS":
                int(a["target_falseS"]) - int(a["PG_falseS"]),
            "labelmodel_delta_NS_recall":
                float(a["target_NS"]) - float(a["PG_NS"]),
            "labelmodel_delta_NA_recall":
                float(a["target_NA"]) - float(a["PG_NA"]),
        })
    csvwrite(OUT / "actual_evaluation.csv", actual_eval)

    sim_rows = []
    for source, alt in (("052","053"), ("053","052")):
        for scenario, prior in SCENARIOS.items():
            for n in BATCH_SIZES:
                r = stress_one(
                    pools[source], pools[alt], source, prior, n, rng)
                sim_rows.append({
                    "source": source,
                    "conditional_alt": alt,
                    "scenario": scenario,
                    "batch_n": n,
                    **r,
                })
                print("057", source, alt, scenario, n, r, flush=True)
    csvwrite(OUT / "simulation_summary.csv", sim_rows)

    hard_rows = read_csv(O056 / "simulation_summary.csv")
    screen_rows = []
    for source in ("052","053"):
        soft240 = [r for r in sim_rows
                   if r["source"] == source and r["batch_n"] == 240]
        hard240 = [r for r in hard_rows
                   if r["source"] == source and int(r["batch_n"]) == 240]
        sfpr = float(np.mean([r["h0_false_alarm"] for r in soft240]))
        stpr = float(np.mean([r["h1_detection"] for r in soft240]))
        hfpr = float(np.mean([float(r["h0_false_alarm"]) for r in hard240]))
        htpr = float(np.mean([float(r["h1_detection"]) for r in hard240]))
        screen_rows.append({
            "source": source,
            "batch_n": 240,
            "soft_h0_false_alarm": sfpr,
            "soft_h1_detection": stpr,
            "hard056_h0_false_alarm": hfpr,
            "hard056_h1_detection": htpr,
            "delta_detection_vs_056": stpr - htpr,
            "pass": bool(sfpr <= .10 and stpr >= .70),
        })
    csvwrite(OUT / "screen_summary.csv", screen_rows)
    mechanism_pass = all(r["pass"] for r in screen_rows)

    actual_joint = [
        r for r in actual_rows if r["view"] == "joint"
    ]
    deployability_pass = all(bool(r["alarm"]) for r in actual_joint)
    run = {
        "status": "PASS",
        "git_head": fr["git_head"],
        "new_api_calls": 0,
        "reserved_used": False,
        "actual_unlabeled_sha256_before_gt_evaluation": blind_sha,
        "pools": {k: len(v) for k,v in pools.items()},
        "screen": screen_rows,
        "mechanism_screen_pass": mechanism_pass,
        "actual_deployability_check_pass": deployability_pass,
        "advance_to_dynamic_gate":
            bool(mechanism_pass and deployability_pass),
    }
    put(OUT / "run_summary.json", run)
    write_report(actual_rows, actual_eval, sim_rows, screen_rows, run)
    print("057 COMPLETE", json.dumps(run, ensure_ascii=False))

def write_report(actual_rows, actual_eval, sim_rows, screen_rows, run):
    lines = [
        "# 057：Soft Multi-view Conditional-shift Detection",
        "",
        "## 核心问题",
        "",
        "056的hard-label联合残差没过门槛。057固定使用DeepSeek T-S + Qwen完整6维scores，检验连续soft信息是否能恢复conditional-shift信号。",
        "",
        "主方法：source-only标准化 + 固定128维RBF Random Fourier Features；BBSE仍只估target prevalence；soft residual比较target mean embedding与source类条件embedding按BBSE prior重混合后的差异。",
        "",
        "## 真实052↔053无标签结果",
        "",
        "| source→target | view | residual | H0 q95 | p | alarm |",
        "|---|---|---:|---:|---:|---|",
    ]
    for r in actual_rows:
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["view"]} | '
            f'{float(r["soft_residual"]):.4f} | {float(r["null_q95"]):.4f} | '
            f'{float(r["null_pvalue"]):.4f} | {r["alarm"]} |')
    lines += [
        "",
        "actual_unlabeled.csv在GT评价前先写入并记录SHA256；上述alarm不读取target GT。",
        "",
        "## 解盲后与055实际adaptation关联",
        "",
        "| source→target | BBSE L1 | joint alarm | 055 ΔPA | ΔMCC | Δfalse-S | ΔNS recall |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for r in actual_eval:
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["bbse_L1"]:.3f} | '
            f'{r["joint_alarm"]} | {r["labelmodel_delta_PA"]:+.3f} | '
            f'{r["labelmodel_delta_MCC"]:+.3f} | '
            f'{r["labelmodel_delta_falseS"]:+d} | '
            f'{r["labelmodel_delta_NS_recall"]:+.3f} |')

    lines += [
        "",
        "## 与056 hard detector同门槛比较",
        "",
        "| source | soft H0 FPR | soft H1 detection | hard056 H1 detection | soft增量 | 事前门槛 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in screen_rows:
        lines.append(
            f'| {r["source"]} | {r["soft_h0_false_alarm"]:.3f} | '
            f'{r["soft_h1_detection"]:.3f} | {r["hard056_h1_detection"]:.3f} | '
            f'{r["delta_detection_vs_056"]:+.3f} | '
            f'{"PASS" if r["pass"] else "FAIL"} |')
    lines += ["", "## 结论", ""]
    if run["advance_to_dynamic_gate"]:
        lines += [
            "**057同时通过机制screen与真实deployability check。**",
            "",
            "说明056的主要瓶颈确实是hard-label压缩；soft multi-view residual具备进入下一阶段reliability-gated adaptation的依据。",
        ]
    elif run["mechanism_screen_pass"]:
        lines += [
            "**057通过模拟机制screen，但真实deployability check未通过。**",
            "",
            "说明soft scores包含额外conditional-shift信息，但仍不足以作为实际zero-label安全开关；不直接进入动态classifier。",
        ]
    else:
        lines += [
            "**057机制screen未通过。**",
            "",
            "在固定soft detector下，连续DeepSeek+Qwen scores仍不足以稳定识别conditional behavior replacement。按事前边界不继续调RFF维度、bandwidth或transform。",
        ]
    lines += [
        "",
        "## 边界",
        "",
        "- 057检验的是shift diagnosis，不修改任何final label。",
        "- 052/053仍是development内部claim批次，不是外部domain。",
        "- H1 conditional replacement是压力测试，不代表所有真实漂移形态。",
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
