"""Replay saved API receipts through the unchanged 002/004 evaluation protocol."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

import live
import pilot
import siliconflow as sf
import resume_balance


REPLAY_BINDINGS = Path(__file__).with_name("replay_bindings.json")


def replay_binding(run: Path) -> tuple[dict, dict]:
    """Anchor retrospective replay sources without rewriting the frozen run."""
    bindings = pilot.strict_json(REPLAY_BINDINGS.read_text(encoding="utf-8"))
    frozen = pilot.digest_file(run / "manifest.json")
    binding = bindings["runs"].get(frozen)
    pilot.require(binding is not None, "Unregistered frozen run: explicit replay binding required")
    original_path = run / "analysis/manifest.json"
    pilot.require(original_path.is_file() and pilot.digest_file(original_path) == binding["analysis_manifest_sha256"],
        "Original analysis manifest changed or missing")
    original = pilot.strict_json(original_path.read_text(encoding="utf-8"))
    pilot.require(original["frozen_manifest_sha256"] == frozen, "Analysis/frozen run binding mismatch")
    return binding, original


def fictional_api_cost(run: Path) -> dict:
    binding, _ = replay_binding(run)
    sources, seen = [], set()
    for item in binding["fictional_api_sources"]:
        name = item["path"]
        path = (pilot.ROOT / name).resolve()
        pilot.require(path.is_relative_to(pilot.OUT / "api_preflight") and path not in seen, "Invalid/duplicate fictional cost source")
        seen.add(path)
        pilot.require(path.is_file() and pilot.digest_file(path) == item["sha256"], "Fictional cost source changed or missing: " + name)
        amount = pilot.strict_json(path.read_text(encoding="utf-8"))
        for key in item["cost_field"]:
            amount = amount[key]
        pilot.require(type(amount) in (int, float) and amount >= 0, "Invalid fictional cost")
        sources.append(dict(item, estimated_cny=amount))
    return dict(estimated_cny=sum(item["estimated_cny"] for item in sources), separate_from_real_inference=True,
        binding_sha256=pilot.digest_file(REPLAY_BINDINGS), frozen_manifest_sha256=pilot.digest_file(run / "manifest.json"),
        binding_timing="retrospective_offline_revision", sources=sources)


def collect(run: Path) -> tuple:
    _, original = replay_binding(run)
    jobs, config, inputs = live.load_jobs(run)
    for name, digest in original["source_receipts_sha256"].items():
        path = run / name
        pilot.require(path.is_file() and pilot.digest_file(path) == digest, "Saved receipt/start/recovery file changed or missing: " + name)
    cohort = sum((pilot.read_csv(run / f"cohort_{a}.csv")[1] for a in ("llm", "human")), [])
    pilot.require(len(jobs) == 3 * len(cohort) and len({j["request"]["request_id"] for j in jobs}) == len(jobs), "Duplicate/missing logical request")
    pilot.require(set(inputs) == {r["proposition_id"] for r in cohort}, "Input/cohort mismatch")
    prompts = {n: (run / "prompts" / (n + ".md")).read_text(encoding="utf-8") for n in ("common", *pilot.ARMS)}
    protected = json.loads((run / "preflight.json").read_text(encoding="utf-8"))["protected_files_sha256"]
    # These were workspace snapshots, not frozen experimental inputs. Missing or
    # edited documentation is reported; load_jobs still checks frozen materials.
    protected_changes = [name for name, digest in protected.items()
        if not (pilot.ROOT / name).is_file() or pilot.digest_file(pilot.ROOT / name) != digest]
    # Preserve the original sample and prompt bytes, independently of new config.
    for name in ("inputs.jsonl", "cohort_llm.csv", "cohort_human.csv", "selected_patients.csv", "excluded_invalid.csv"):
        pilot.require(pilot.digest_file(run / name) == pilot.digest_file(live.SOURCE / name), "Changed source sample: " + name)
    for name in ("common", *pilot.ARMS):
        pilot.require(pilot.digest_file(run / "prompts" / (name + ".md")) == pilot.digest_file(live.SOURCE / "prompts" / (name + ".md")), "Changed prompt")
    starts = pilot.jsonl(run / "attempt_starts.jsonl")
    start_keys = [(r["sequence"], r["attempt"]) for r in starts]
    pilot.require(len(start_keys) == len(set(start_keys)), "Duplicate attempt start")
    by_start = dict(zip(start_keys, starts))
    by_sequence = {j["sequence"]: j for j in jobs}
    histories = defaultdict(list)
    receipts = []
    source_hashes = {"attempt_starts.jsonl": pilot.digest_file(run / "attempt_starts.jsonl")}
    recovery_targets = set()
    amendment_path = run / "balance_recovery.json"
    if amendment_path.exists():
        amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
        pilot.require(amendment["recovery_code_sha256"] == pilot.digest_file(Path(resume_balance.__file__)), "Recovery code changed")
        for name, digest in amendment["original_balance_receipts_sha256"].items():
            pilot.require(pilot.digest_file(run / name) == digest, "Original 402 receipt changed")
        recovery_targets = set(amendment["target_sequences"])
        source_hashes["balance_recovery.json"] = pilot.digest_file(amendment_path)
    for path in sorted((run / "receipts").glob("*.json")):
        value = pilot.strict_json(path.read_text(encoding="utf-8"))
        key = (value["sequence"], value["attempt"])
        pilot.require(key in by_start and value["sequence"] in by_sequence, "Unknown attempt receipt")
        job = by_sequence[value["sequence"]]
        pilot.require(value["api_body_sha256"] == by_start[key]["api_body_sha256"] == job["api_body_sha256"], "Receipt/start/request hash mismatch")
        pilot.require(by_start[key]["request_id"] == job["request"]["request_id"], "Start identity mismatch")
        transport = value["transport"]
        if transport["response_json"] is not None:
            pilot.require(pilot.strict_json(transport["response_body_text"]) == transport["response_json"], "Raw/native response mismatch")
        replay = sf.normalize_result(job["request"], inputs[job["request"]["proposition_id"]], transport, config)
        pilot.require(replay == value["normalized"], "Saved normalization differs from raw-response replay")
        histories[value["sequence"]].append(value)
        receipts.append(value)
        source_hashes[path.relative_to(run).as_posix()] = pilot.digest_file(path)
    pilot.require(len(receipts) == len(by_start), "Unresolved sent request without receipt; resume or inspect")
    pilot.require(source_hashes == original["source_receipts_sha256"], "Saved receipt source set changed")
    terminal, failures = [], []
    native_controls = set()
    for job in jobs:
        request = job["request"]
        expected = pilot.make_request(inputs[request["proposition_id"]], request["arm"], config, prompts)
        pilot.require(request == expected, "Logical request cannot be reconstructed")
        body = sf.api_body(expected, config["live_policy"]["response_format"])
        pilot.require(body == job["api_body"] and pilot.fingerprint(body) == job["api_body_sha256"], "Native request cannot be reconstructed")
        native_controls.add(pilot.fingerprint({k: v for k, v in body.items() if k != "messages"}))
        history = sorted(histories[job["sequence"]], key=lambda r: r["attempt"])
        if not history:
            failures.append(dict(request_id=request["request_id"], error="No attempt"))
            continue
        pilot.require([r["attempt"] for r in history] == list(range(1, len(history) + 1)), "Gapped or duplicate attempts")
        pilot.require(len(history) <= config["live_policy"]["maximum_service_attempts"], "Retry cap exceeded")
        pilot.require(all(r["transport"]["service_retryable"] or (job["sequence"] in recovery_targets and
            resume_balance.balance_error(r["transport"]) and r["normalized"]["verdict"] is None) for r in history[:-1]), "Answer was regenerated after terminal receipt")
        if job["sequence"] in recovery_targets and len(history) > 1:
            pilot.require(by_start[(job["sequence"], history[1]["attempt"])]["started_utc"] >= amendment["registered_utc"], "Recovery attempt preceded service amendment")
        chosen = history[-1]["normalized"]
        terminal.append(chosen)
        if chosen["status"] != "success":
            failures.append(dict(request_id=request["request_id"], error=chosen["structural_errors"]))
        else:
            u = chosen["usage"]
            pilot.require(u["input_tokens"] + u["output_tokens"] <= config["judge"]["context_window_tokens"], "Actual context usage exceeds declared capacity")
            pilot.require(u["total_tokens"] == u["input_tokens"] + u["output_tokens"], "Usage total is inconsistent")
    pilot.require(len(native_controls) == 1, "Native settings differ across arms")
    checks = dict(expected_requests=len(jobs), receipts=len(receipts), terminal_responses=len(terminal), failures=failures,
        real_patients=len({r["subject_id"] for r in cohort}), real_claims=len(cohort),
        full_sample_prompt_reference_bytes_verified=True, native_requests_reconstructed=True,
        raw_response_normalization_replayed=True, protected_files_unchanged=not protected_changes,
        protected_files_policy="workspace_snapshot_nonblocking", protected_files_changes=protected_changes,
        original_receipt_hashes_verified=True,
        balance_recovery_registered=bool(recovery_targets), original_unanswered_balance_requests=len(recovery_targets),
        outcome_based_regeneration_detected=False, complete=not failures and len(terminal) == len(jobs))
    return config, cohort, terminal, receipts, checks, source_hashes


def usage_summary(receipts: list[dict], terminal: list[dict], cohort: list[dict]) -> tuple[dict, list[dict]]:
    metadata = {r["proposition_id"]: r for r in cohort}
    records = []
    for receipt in receipts:
        r, t = receipt["normalized"], receipt["transport"]
        u = r.get("usage", {})
        records.append(dict(sequence=receipt["sequence"], attempt=receipt["attempt"], request_id=r["request_id"],
            proposition_id=r["proposition_id"], arm=r["arm"], author_type=metadata[r["proposition_id"]]["author_type"],
            subject_id=metadata[r["proposition_id"]]["subject_id"], http_status=t["http_status"], status=r["status"],
            started_utc=t["started_utc"], ended_utc=t["ended_utc"], latency_seconds=t["elapsed_seconds"],
            input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"), reasoning_tokens=u.get("reasoning_tokens"),
            cache_hit_tokens=u.get("cache_hit_tokens"), reasoning_counter_basis=u.get("reasoning_counter_basis"),
            explanation_words=r.get("explanation_words"), adherence_errors="; ".join(r["adherence_errors"]),
            outcome_unknown=t["outcome_unknown"], cny_estimate=r.get("cost", {}).get("cny"),
            budget_charge_cny=receipt["budget_charge_cny"], listing_cny=r.get("cost", {}).get("website_listing_scenario_cny"),
            finish_reason=r.get("finish_reason"), model_returned=r.get("model_returned"),
            system_fingerprint=r.get("system_fingerprint"), trace_id=t["response_headers"].get("x-siliconcloud-trace-id")))
    def aggregate(rows):
        known = [r for r in rows if r["input_tokens"] is not None]
        return dict(attempts=len(rows), generated_responses=len(known), input_tokens=sum(r["input_tokens"] for r in known),
            output_tokens=sum(r["output_tokens"] for r in known), reasoning_tokens=sum(r["reasoning_tokens"] for r in known),
            cache_hit_tokens=sum(r["cache_hit_tokens"] or 0 for r in known),
            usage_missing_attempts=len(rows) - len(known), unknown_outcomes=sum(r["outcome_unknown"] for r in rows),
            estimated_cny=sum(r["cny_estimate"] or 0 for r in rows),
            unknown_charge_bound_cny=sum(r["budget_charge_cny"] for r in rows if r["cny_estimate"] is None),
            listing_scenario_cny=sum(r["listing_cny"] or 0 for r in rows),
            cache_counter_missing=sum(r["cache_hit_tokens"] is None for r in known),
            missing_explicit_reasoning_counter=sum(r["reasoning_counter_basis"] != "provider_explicit_counter" for r in known),
            adherence_deviations=sum(bool(r["adherence_errors"]) for r in rows),
            word_limit_deviations=sum((r["explanation_words"] or 0) > 200 for r in rows),
            output_token_distribution=pilot.distribution([r["output_tokens"] for r in known]),
            input_token_distribution=pilot.distribution([r["input_tokens"] for r in known]),
            explanation_word_distribution=pilot.distribution([r["explanation_words"] for r in known if r["explanation_words"] is not None]),
            latency_seconds=pilot.distribution([r["latency_seconds"] for r in rows]))
    by_arm = {a: aggregate([r for r in records if r["arm"] == a]) for a in pilot.ARMS}
    by_author = {author: {a: aggregate([r for r in records if r["arm"] == a and r["author_type"] == author]) for a in pilot.ARMS} for author in ("llm", "human")}
    b, c = by_arm["structured"], by_arm["event_alignment"]
    begin, end = min(r["started_utc"] for r in records), max(r["ended_utc"] for r in records)
    summary = dict(total=aggregate(records), by_arm=by_arm, by_author=by_author,
        logical_requests=len(terminal), extra_service_attempts=len(receipts) - len(terminal),
        returned_models=sorted({str(r["model_returned"]) for r in records if r["model_returned"] is not None}),
        returned_system_fingerprints=sorted({str(r["system_fingerprint"]) for r in records if r["model_returned"] is not None}),
        http_status_counts=dict(Counter(str(r["http_status"]) for r in records)),
        began_utc=begin, ended_utc=end, wall_seconds=(datetime.fromisoformat(end)-datetime.fromisoformat(begin)).total_seconds(),
        event_to_structured_output_token_ratio=c["output_tokens"] / b["output_tokens"] if b["output_tokens"] else None,
        event_to_structured_total_token_ratio=(c["input_tokens"] + c["output_tokens"]) / (b["input_tokens"] + b["output_tokens"]) if b["input_tokens"] else None,
        actual_invoice_verified=False, model_immutable_revision_verified=False,
        output_cap_equality_does_not_imply_equal_consumption=True)
    summary["successful_generation_phase_by_arm"] = {a: dict(
        initial=sum(r["arm"] == a and r["attempt"] == 1 and r["status"] == "success" for r in records),
        after_service_recovery=sum(r["arm"] == a and r["attempt"] > 1 and r["status"] == "success" for r in records)) for a in pilot.ARMS}
    phases = defaultdict(set)
    for r in records:
        if r["status"] == "success":
            phases[r["proposition_id"]].add("initial" if r["attempt"] == 1 else "recovery")
    summary["claims_with_successful_arms_across_run_phases"] = sorted(k for k, v in phases.items() if len(v) > 1)
    return summary, records


def robustness(cohort: list[dict], predictions: dict) -> dict:
    result = {}
    lookup = {a: {p["proposition_id"]: p["verdict"] for p in predictions[a]} for a in pilot.ARMS}
    for author in ("llm", "human"):
        main = [r for r in cohort if r["author_type"] == author]
        subjects = sorted({r["subject_id"] for r in main})
        lopo, patients = [], []
        for sid in subjects:
            rows = [r for r in main if r["subject_id"] != sid]
            ids = {r["proposition_id"] for r in rows}
            scores = {a: pilot.evaluate(rows, [r for r in predictions[a] if r["proposition_id"] in ids], profile="none") for a in ("structured", "event_alignment")}
            lopo.append(dict(excluded_patient=sid, retained_n=len(rows), deltas={k: scores["event_alignment"][k] - scores["structured"][k]
                for k in ("percent_agreement", "gwet_ac1", "mcc")}))
            own = [r for r in main if r["subject_id"] == sid]
            fixed = sum(lookup["structured"][r["proposition_id"]] != r["human_gt"] == lookup["event_alignment"][r["proposition_id"]] for r in own)
            broken = sum(lookup["structured"][r["proposition_id"]] == r["human_gt"] != lookup["event_alignment"][r["proposition_id"]] for r in own)
            patients.append(dict(subject_id=sid, n=len(own), error_to_correct=fixed, correct_to_error=broken, net_correct=fixed-broken))
        result[author] = dict(leave_one_patient_out=lopo, patient_changes=patients,
            positive_patient_nets=sum(r["net_correct"] > 0 for r in patients),
            negative_patient_nets=sum(r["net_correct"] < 0 for r in patients),
            lopo_mcc_delta_min=min(r["deltas"]["mcc"] for r in lopo), lopo_mcc_delta_max=max(r["deltas"]["mcc"] for r in lopo))
    return result


def evaluate_complete_components(cohort: list[dict], predictions: dict, iterations: int) -> dict:
    """Strict complete denominators per author/scope and pair, never available-case.

    This is explicitly separate from pilot.evaluate_arms's all-three-arm gate.
    A failed routine generation must not be imputed or invalidate a complete
    structured-versus-event comparison. Missing arms/pairs remain blocked.
    """
    expected = {r["proposition_id"] for r in cohort}
    for arm, pp in predictions.items():
        ids = [r["proposition_id"] for r in pp]
        pilot.require(len(ids) == len(set(ids)) and set(ids) <= expected, "Duplicate or unknown prediction")
        pilot.require(all(r["verdict"] in pilot.LABELS for r in pp), "Invalid label cannot be scored")
    result = {}
    for author in ("llm", "human"):
        main = [r for r in cohort if r["author_type"] == author]
        result[author] = {}
        for scope, rows in (("primary", main), ("exclude_time_conflicts", [r for r in main if r["time_metadata_conflict"] == "False"])):
            ids = {r["proposition_id"] for r in rows}
            pp = {a: [r for r in predictions[a] if r["proposition_id"] in ids] for a in pilot.ARMS}
            metrics = {}
            for a in pilot.ARMS:
                absent = sorted(ids - {r["proposition_id"] for r in pp[a]})
                if absent:
                    metrics[a] = dict(status="blocked_incomplete_predictions", expected_n=len(rows), missing_n=len(absent), missing_ids=absent)
                else:
                    metrics[a] = pilot.evaluate(rows, pp[a], profile="research_patient", missing="error", iterations=iterations)
            contrasts = {}
            for base, candidate in pilot.PAIRS:
                if "status" in metrics[base] or "status" in metrics[candidate]:
                    contrasts[candidate + "_minus_" + base] = dict(status="blocked_incomplete_pair", expected_n=len(rows),
                        missing_ids=sorted(set(metrics[base].get("missing_ids", []) + metrics[candidate].get("missing_ids", []))))
                    continue
                bc, cc = ({r["proposition_id"]: r["verdict"] for r in pp[a]} for a in (base, candidate))
                transitions = Counter((r["human_gt"], bc[r["proposition_id"]], cc[r["proposition_id"]]) for r in rows)
                contrasts[candidate + "_minus_" + base] = dict(**pilot.paired_compare(rows, pp[base], pp[candidate], iterations=iterations),
                    error_to_correct=sum(n for (g, b, c), n in transitions.items() if b != g and c == g),
                    correct_to_error=sum(n for (g, b, c), n in transitions.items() if b == g and c != g),
                    transitions=[dict(gt=g, baseline=b, candidate=c, count=n) for (g, b, c), n in sorted(transitions.items())])
            per_patient = {}
            for sid in sorted({r["subject_id"] for r in rows}):
                own = [r for r in rows if r["subject_id"] == sid]
                own_ids = {r["proposition_id"] for r in own}
                per_patient[sid] = {}
                for a in pilot.ARMS:
                    pred = [r for r in pp[a] if r["proposition_id"] in own_ids]
                    per_patient[sid][a] = pilot.evaluate(own, pred, profile="none") if len(pred) == len(own) else dict(status="blocked_incomplete_predictions")
            result[author][scope] = dict(metrics=metrics, contrasts=contrasts, per_patient=per_patient,
                errors={a: pilot.error_counts(rows, pp[a]) for a in pilot.ARMS if "status" not in metrics[a]},
                excluded_ids=sorted({r["proposition_id"] for r in main} - ids))
    return result


def adherence_summary(terminal: list[dict]) -> tuple[dict, list[dict]]:
    """Mechanical instruction adherence only; no medical or semantic relabeling."""
    rows = []
    for r in terminal:
        if r["status"] != "success":
            continue
        answer = pilot.strict_json(r["output_text"])
        checks = answer.get("checks", [])
        aspects = [c.get("aspect") for c in checks if isinstance(c, dict)] if isinstance(checks, list) else []
        expected = pilot.ASPECTS[r["arm"]]
        cosmetic = [str(a).strip().lower().replace(" ", "_") for a in aspects]
        rows.append(dict(request_id=r["request_id"], proposition_id=r["proposition_id"], arm=r["arm"],
            checks_count=len(checks) if isinstance(checks, list) else None, expected_count=len(expected),
            exact_aspects=aspects == expected, case_space_normalized_aspects=cosmetic == expected,
            all_strict_checks_satisfied=not r["adherence_errors"], word_limit_exceeded=(r.get("explanation_words") or 0) > 200,
            actual_aspects_json=pilot.canonical(aspects), errors="; ".join(r["adherence_errors"])))
    summary = {a: dict(n=sum(r["arm"] == a for r in rows),
        all_strict_checks_satisfied=sum(r["all_strict_checks_satisfied"] for r in rows if r["arm"] == a),
        exact_aspects=sum(r["exact_aspects"] for r in rows if r["arm"] == a),
        case_space_normalized_aspects=sum(r["case_space_normalized_aspects"] for r in rows if r["arm"] == a),
        wrong_check_count=sum(r["checks_count"] != r["expected_count"] for r in rows if r["arm"] == a),
        word_limit_exceeded=sum(r["word_limit_exceeded"] for r in rows if r["arm"] == a),
        count_distribution=dict(Counter(str(r["checks_count"]) for r in rows if r["arm"] == a))) for a in pilot.ARMS}
    return dict(by_arm=summary, mechanical_not_semantic_validation=True, all_original_verdicts_retained=True,
        no_adherence_based_subset_scoring=True), rows


def result_tables(metrics: dict) -> tuple[list, list]:
    flat, contrasts = [], []
    for author, scopes in metrics.items():
        for scope, result in scopes.items():
            for arm, m in result["metrics"].items():
                if "status" in m:
                    flat.append(dict(author=author, scope=scope, arm=arm, status=m["status"], n=m["expected_n"], missing_n=m["missing_n"]))
                    continue
                flat.append(dict(author=author, scope=scope, arm=arm, n=m["n"], patients=m["coverage"]["evaluated_patients"],
                    **{k: m[k] for k in ("percent_agreement", "gwet_ac1", "mcc")},
                    **{short + "_recall": m["per_class"][label]["recall"] for short, label in zip(("S", "NS", "NA"), pilot.LABELS)}))
            for name, c in result["contrasts"].items():
                if "status" in c:
                    contrasts.append(dict(author=author, scope=scope, comparison=name, status=c["status"]))
                    continue
                for metric, v in c["metrics"].items():
                    contrasts.append(dict(author=author, scope=scope, comparison=name, metric=metric,
                        delta=v["delta"], ci95_low=v["ci95"][0], ci95_high=v["ci95"][1],
                        error_to_correct=c["error_to_correct"], correct_to_error=c["correct_to_error"]))
    return flat, contrasts


def report(metrics, budget, influence, checks, preflight_cost, adherence) -> str:
    lines = ["# 004 真实 pilot：执行结果", "", "**状态：执行完成，等待独立审计。** 本报告由执行者生成，不代表独立审计通过。", "",
        f"6 名冻结 development 患者、421 条 valid atomic claims（LLM 181、human 240），1,263 个逻辑请求已处理，终结失败 {len(checks['failures'])} 个。使用硅基流动官方 `deepseek-ai/DeepSeek-V4-Flash`；temperature=0、thinking=false、max_tokens=2048、n=1、非流式、相同 strict JSON schema。每条独立会话，原命题、完整 reference 和提示词沿用离线 run_001，没有使用 reserved test、重新检索或训练。原 R1 预测仅保留为历史资料，不进入本轮三臂比较。", "",
        "## 主要结果", "", "PA 为完全一致率；AC1/MCC 为三分类指标。共用 002 评价，valid-only 完整队列、1,000 次配对患者 bootstrap；主对比为 **event_alignment − structured 的 MCC**。", "",
        "| 作者 | 方法 | n | PA | AC1 | MCC |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for author in ("llm", "human"):
        for arm in pilot.ARMS:
            m = metrics[author]["primary"]["metrics"][arm]
            if "status" in m:
                lines.append(f"| {author} | {arm} | {m['expected_n']}（缺 {m['missing_n']}） | 暂不可计算 | — | — |")
                continue
            lines.append(f"| {author} | {arm} | {m['n']} | {m['percent_agreement']:.1%} | {m['gwet_ac1']:.4f} | {m['mcc']:.4f} |")
    lines += ["", "| 作者 | ΔMCC [95% 患者 bootstrap CI] | ΔPA | 错→对 / 对→错 | 排除时间冲突后的 ΔMCC |", "| --- | --- | ---: | ---: | ---: |"]
    for author in ("llm", "human"):
        c = metrics[author]["primary"]["contrasts"]["event_alignment_minus_structured"]
        v = c["metrics"]["mcc"]
        s = metrics[author]["exclude_time_conflicts"]["contrasts"]["event_alignment_minus_structured"]["metrics"]["mcc"]
        lines.append(f"| {author} | {v['delta']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | {100*c['metrics']['percent_agreement']['delta']:+.2f} 个百分点 | {c['error_to_correct']} / {c['correct_to_error']} | {s['delta']:+.4f} |")
    lines += ["", "**失败与评价范围：** 截断/无效响应保持失败状态，不补标签、不重跑。原离线汇总器会因任一臂失败阻止所有比较；本轮明确改为逐作者、逐臂/配对调用同一 002 严格评价：含失败的完整分母不发布点估计，不涉及失败且两臂均完整的对比仍可评价。这是看到服务/生成失败后明确登记的分析处理，不是运行前预设；未使用 available-case 或过滤 GT。原始失败及受阻比较保留在 response_checks/metrics 中。", "", "时间敏感性共同排除患者 98790 的 77 条（LLM 29、human 48）；实际变为 5 名患者、LLM 152/human 192 条。因此它同时改变患者构成，不能直接解释成修复时间字段的效果。完整区间及另外两组对比在 `metrics.json`。", "", "## 类别代价与患者影响", "",
        "| 作者/方法 | S 召回 | NS 召回 | NA 召回 | 非 S→S | S→非 S | NS↔NA |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for author in ("llm", "human"):
        for arm in pilot.ARMS:
            m = metrics[author]["primary"]["metrics"][arm]
            if "status" in m:
                lines.append(f"| {author}/{arm} | 缺失导致无法计算 | — | — | — | — | — |")
                continue
            e = metrics[author]["primary"]["errors"][arm]
            recalls = [m["per_class"][label]["recall"] for label in pilot.LABELS]
            lines.append(f"| {author}/{arm} | {recalls[0]:.1%} | {recalls[1]:.1%} | {recalls[2]:.1%} | {e['non_s_to_s']} | {e['s_to_non_s']} | {e['ns_na_confusion']} |")
    lines.append("")
    for author in ("llm", "human"):
        r = influence[author]
        nets = "、".join(f"{p['subject_id']}：{p['net_correct']:+d}" for p in r["patient_changes"])
        lines.append(f"- {author}：每名患者正确数净变化（event − structured）为 {nets}；逐一留出患者后 ΔMCC 范围 [{r['lopo_mcc_delta_min']:+.4f}, {r['lopo_mcc_delta_max']:+.4f}]。")
    lines += ["", "LLM 仅 7 条 NS、8 条 NA，个别样本可明显改变 MCC。逐患者指标、留一患者结果及全部改变标签的 ID/GT/三臂标签见机器文件；这些是对医生标签的一致性统计，不是新的医学真值或模型内部机制证明。", "", "## 实际调用与预算", "",
        "| 方法 | 调用尝试 | 输入 tokens | 输出 tokens | 平均输出 tokens | 平均解释词数 | 格式/词数偏离 | 估算费用 ¥ |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for arm in pilot.ARMS:
        b = budget["by_arm"][arm]
        lines.append(f"| {arm} | {b['attempts']} | {b['input_tokens']:,} | {b['output_tokens']:,} | {b['output_token_distribution']['mean']:.1f} | {b['explanation_word_distribution']['mean']:.1f} | {b['adherence_deviations']} | {b['estimated_cny']:.4f} |")
    b = budget["total"]
    lines += ["", f"真实调用 {b['attempts']} 次，额外服务尝试 {budget['extra_service_attempts']} 次，未解决失败 {len(checks['failures'])}；从首次调用至结束约 {budget['wall_seconds']/60:.1f} 分钟（含中断）。总输入 {b['input_tokens']:,}、输出 {b['output_tokens']:,}、reasoning {b['reasoning_tokens']:,} tokens；缺少显式 reasoning 计数的模型响应 {b['missing_explicit_reasoning_counter']} 个。原始响应及每次尝试均保留。", "",
        f"初轮完成 723 个答案后余额不足，随后留下 540 个 HTTP 402/code 30001、无 choices/usage 的失败响应。原执行器没有余额错误立即停止后续调度的控制，已补充并用虚构测试验证。用户充值后，仅补齐这些无答案请求；已有答案不重跑。恢复口径在补跑前单独登记于 `../balance_recovery.json`，原代码/配置和 402 回执不改写。共有 {len(budget['claims_with_successful_arms_across_run_phases'])} 条命题的成功响应跨越两次运行时段；逐臂阶段统计保留，无法证明服务端底层权重在中断前后绝对不变。", "",
        f"event/structured 实际输出 token 比为 **{budget['event_to_structured_output_token_ratio']:.3f}**，输入+输出合计比为 {budget['event_to_structured_total_token_ratio']:.3f}。相同调用数和上限不代表精确等算力；routine 的解释结构更短，主要因果对照仍是 structured。解释偏离按运行前登记保留原标签计分，不修复、不删除、不选择性重跑。", "",
        f"按有生效日期的峰谷价及实际缓存 usage，真实推理估算 **¥{b['estimated_cny']:.4f}**；全部虚构接口测试另约 ¥{preflight_cost:.4f}。未知结果费用占用上界 ¥{b['unknown_charge_bound_cny']:.4f}。模型目录价格场景下真实调用约 ¥{b['listing_scenario_cny']:.4f}。**未核对账户账单，以上均非实际结算金额**；官网目录和日期公告价格不同，差异未自行消除。[价格公告](https://docs.siliconflow.cn/docs/release-notes/overview) · [模型目录](https://siliconflow.cn/models?page=1&q=DeepSeek)。", "",
        "全部原生请求可从冻结输入重建并验证 SHA-256；原始响应重新解析与保存标签一致。实际 usage 未超上下文/生成上限，没有客户端 reference 截断。服务返回同一模型别名，但 system_fingerprint 未提供有效固定版本，无法保证将来调用仍是同一权重。[接口说明](https://api-docs.siliconflow.cn/docs/api/chat-completions-post)。", "", "## 下一步与独立审计", ""]
    lines += ["**实际检查结构的遵守情况限制了机制解释：**", "",
        "| 方法 | 严格遵守全部要求 | 精确检查项名称/次序正确 | 仅统一大小写和空格后正确 | 检查项数量错误 |", "| --- | ---: | ---: | ---: | ---: |"]
    for arm in pilot.ARMS:
        a = adherence["by_arm"][arm]
        lines.append(f"| {arm} | {a['all_strict_checks_satisfied']}/{a['n']} | {a['exact_aspects']}/{a['n']} | {a['case_space_normalized_aspects']}/{a['n']} | {a['wrong_check_count']} |")
    lines += ["", "大小写/空格归一化仅用于诊断名称差异，没有修改回答、标签或评分分母；其余不匹配也不能直接等同于模型没考虑对应问题。普通 JSON schema 约束了字段形式，但未硬约束每臂检查项数量/名称，真实复杂输入上的执行遵守明显弱于虚构测试。**本轮首先比较三种提示词方案的实际表现，不能据此宣称稳定执行了三种预设推理过程。** 不按遵守情况筛出子集来挽救成绩。", ""]
    # Deliberately conservative decision logic; no p-value or positive spin.
    deltas = {a: metrics[a]["primary"]["contrasts"]["event_alignment_minus_structured"]["metrics"]["mcc"]["delta"] for a in ("llm", "human")}
    if all(d <= 0 for d in deltas.values()):
        lines.append("**不建议直接扩大当前事件对齐方案。** 两种作者的主比较均未优于普通结构化解释；即使某项相对 routine 更好，也不足以支持事件对齐的额外价值。保留本轮负结果，先在这 6 名已使用的开发患者中核查反复出现的损失与输出遵守情况，再决定是否提出有明确改动的新假设。")
    elif any(d <= 0 for d in deltas.values()):
        lines.append("**当前信号不一致，不宜直接宣布事件对齐得到支持或无条件扩大全部队列。** 两种作者的主比较方向不同；先核查上述类别代价、逐患者集中程度和区间。若后续扩大，应只作为提前登记的开发验证，沿原开发顺序且保留负向作者层结果，不触碰保留测试组。")
    else:
        lines.append("两种作者的主比较点估计均为正，但 6 名患者不足以确认稳定改进。只有结合上述区间、类别代价、留一患者稳定性和实际预算后，才考虑沿原顺序扩大 development 验证；本轮不构成最终方法贡献或测试集结论。")
    lines += ["", "独立审计请重点检查：① 冻结时间是否早于真实调用，421×3 请求与原 reference 是否完整一致；② 有无内容驱动重跑、失败隐藏或格式偏离造成预算不公平；③ 002 完整分母、配对方向、bootstrap 和时间排除是否正确；④ 少数类与患者集中是否支持本文判读；⑤ 缓存/价格矛盾、费用估算和模型版本不可确认的表述。", "",
        "执行者没有修改独立审计记录或宣布审计 PASS。报告之外的 `metrics.json`、`contrasts.csv`、`robustness.json`、`usage.json`、`attempts.csv`、`changed_predictions.csv` 和源回执供程序及独立模型复查。"]
    return "\n".join(lines) + "\n"


def analyze(run: Path, output: Path, make_report=True) -> dict:
    config, cohort, terminal, receipts, checks, source_hashes = collect(run)
    fictional_cost = fictional_api_cost(run)
    output.mkdir(parents=True, exist_ok=False)
    pilot.write_json(output / "response_checks.json", checks)
    pilot.write_jsonl(output / "normalized_responses.jsonl", terminal)
    budget, attempts = usage_summary(receipts, terminal, cohort)
    pilot.write_json(output / "usage.json", budget)
    pilot.write_csv(output / "attempts.csv", attempts)
    adherence, adherence_rows = adherence_summary(terminal)
    pilot.write_json(output / "adherence.json", adherence)
    pilot.write_csv(output / "adherence_by_response.csv", adherence_rows)
    predictions = {a: [dict(proposition_id=r["proposition_id"], verdict=r["verdict"]) for r in terminal if r["arm"] == a and r["status"] == "success"] for a in pilot.ARMS}
    for a in pilot.ARMS:
        # Full original IDs remain in exported files; failed verdicts are blank,
        # not invented labels and not silently removed from the denominator.
        pilot.write_csv(output / f"predictions_{a}.csv", [dict(proposition_id=r["proposition_id"], verdict=r["verdict"], status=r["status"])
            for r in terminal if r["arm"] == a])
    pilot.write_json(output / "analysis_scope.json", dict(registered_utc=sf.utcnow(), complete_three_arm_predictions=checks["complete"],
        handling="Only complete author/scope arms and complete pairs are scored with 002 missing=error; failed comparisons stay blocked",
        timing="Component-wise handling explicitly added after a routine truncation was observed; not a pre-registered all-three-arm scoring gate",
        full_denominators_retained=True, label_imputation=False, available_case=False, failure_count=len(checks["failures"])))
    metrics = pilot.evaluate_arms(cohort, predictions, config["evaluation"]["iterations"]) if checks["complete"] else evaluate_complete_components(cohort, predictions, config["evaluation"]["iterations"])
    pilot.write_json(output / "metrics.json", metrics)
    flat, contrasts = result_tables(metrics)
    pilot.write_csv(output / "metric_summary.csv", flat, fields=list(dict.fromkeys(k for r in flat for k in r)))
    pilot.write_csv(output / "contrasts.csv", contrasts, fields=list(dict.fromkeys(k for r in contrasts for k in r)))
    try:
        influence = robustness(cohort, predictions)
    except ValueError:
        influence = dict(status="blocked_incomplete_primary_pair")
    pilot.write_json(output / "robustness.json", influence)
    lookup = {a: {p["proposition_id"]: p["verdict"] for p in predictions[a]} for a in pilot.ARMS}
    changed = [dict(proposition_id=r["proposition_id"], subject_id=r["subject_id"], author_type=r["author_type"], human_gt=r["human_gt"],
        time_metadata_conflict=r["time_metadata_conflict"], **{a: lookup[a].get(r["proposition_id"]) for a in pilot.ARMS}) for r in cohort
        if len({lookup[a].get(r["proposition_id"]) for a in pilot.ARMS}) > 1]
    pilot.write_csv(output / "changed_predictions.csv", changed, fields=["proposition_id", "subject_id", "author_type", "human_gt", "time_metadata_conflict", *pilot.ARMS])
    pilot.write_json(output / "status.json", dict(status="execution_complete_awaiting_independent_audit", independent_audit_pass_claimed=False,
        scored=True, complete_three_arm_predictions=checks["complete"], real_claims=len(cohort), expected_predictions=3*len(cohort),
        terminal_responses=len(terminal), valid_predictions=sum(r["status"] == "success" for r in terminal),
        generation_failures=len(checks["failures"]), reserved_test_used=False))
    preflight_cost = fictional_cost["estimated_cny"]
    pilot.write_json(output / "fictional_api_cost.json", fictional_cost)
    if make_report:
        with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(report(metrics, budget, influence, checks, preflight_cost, adherence))
    pilot.write_json(output / "manifest.json", dict(stage="execution_complete_awaiting_independent_audit", created_utc=sf.utcnow(),
        frozen_manifest_sha256=pilot.digest_file(run / "manifest.json"), source_receipts_sha256=source_hashes,
        analysis_code_sha256=pilot.digest_file(Path(__file__)),
        output_sha256={p.name: pilot.digest_file(p) for p in output.iterdir() if p.is_file()}))
    result = dict(output=str(output), requests=len(terminal), attempts=len(receipts), estimated_cny=budget["total"]["estimated_cny"],
        primary={a: metrics[a]["primary"]["contrasts"]["event_alignment_minus_structured"].get("metrics", {"status": "blocked"}) for a in ("llm", "human")})
    print(pilot.canonical(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()
    analyze(args.run.resolve(), args.output.resolve() if args.output else args.run.resolve() / "analysis", not args.no_report)


if __name__ == "__main__":
    main()
