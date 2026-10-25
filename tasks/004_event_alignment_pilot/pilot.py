"""Offline pilot preparation and response scoring. No network client or live runner."""
from __future__ import annotations

import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import re
import sys

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/004_event_alignment_pilot"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/003_error_analysis"))
from analyze import FORMAL, RAW, SPLIT_SEED, load_split, require, subset_csv
from verifact_research.audit.common import (LABELS, digest_file, digest_text, distribution,
    integer_id, new_run, read_csv, write_csv, write_json)
from verifact_research.evaluation.core import evaluate, paired_compare

ARMS = ("routine", "structured", "event_alignment")
ASPECTS = {
    "routine": [],
    "structured": ["claim_summary", "relevant_evidence", "supporting_case", "opposing_case", "overall_assessment"],
    "event_alignment": ["event", "time", "status", "scope", "support_sufficiency"],
}
INPUT_FIELDS = {"proposition_id", "subject_id", "hadm_id", "author_type", "text", "reference_id", "reference"}
PAIRS = (("structured", "event_alignment"), ("routine", "event_alignment"), ("routine", "structured"))


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value) -> str:
    return digest_text(canonical(value))


def jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [strict_json(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical(row) + "\n")


def strict_json(text: str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("Non-finite JSON constant: " + value)
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)


def patients_in_order(split: dict, count: int = 6) -> list[str]:
    groups = split["groups"]
    require(split["seed"] == SPLIT_SEED, "Unknown frozen ordering seed")
    require(len(groups["development"]) == 40, "Expected frozen development group")
    flat = [sid for group in groups.values() for sid in group]
    require(len(flat) == len(set(flat)), "Overlapping or duplicate patients")
    require(count == 6, "This preparation is fixed to six development patients")
    return sorted(groups["development"], key=lambda x: (digest_text(split["seed"] + x), x))[:count]


def select_cohort(rows: list[dict], selected: list[str]) -> tuple[list[dict], list[dict]]:
    atomic = [r for r in rows if r["subject_id"] in selected and r["proposition_type"] == "claim"]
    require(len({r["proposition_id"] for r in atomic}) == len(atomic), "Duplicate cohort ID")
    require(all(r["invalid"] in {"True", "False"} and r["author_type"] in {"llm", "human"} for r in atomic), "Invalid cohort metadata")
    valid = [r for r in atomic if r["invalid"] == "False"]
    excluded = [r for r in atomic if r["invalid"] == "True"]
    require(set(selected) == {r["subject_id"] for r in valid}, "A selected patient has no valid claims")
    return valid, excluded


def templates() -> dict[str, str]:
    return {name: (TASK / "prompts" / (name + ".md")).read_text(encoding="utf-8") for name in ("common", *ARMS)}


def reference_numbers(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"(?m)^(\d+)\. Date: ", text)]


def validate_input(item: dict) -> None:
    require(set(item) == INPUT_FIELDS, "Unexpected model input fields (GT/old verdict/BHC must not enter prompts)")
    require(all(isinstance(v, str) and v for v in item.values()), "Blank/non-string model input")
    require(digest_text(item["reference"]) == item["reference_id"], "Changed reference bytes")
    nums = reference_numbers(item["reference"])
    require(bool(nums) and len(nums) == len(set(nums)), "Missing/duplicate evidence numbering")


def make_request(item: dict, arm: str, config: dict, prompts: dict) -> dict:
    validate_input(item)
    require(arm in ARMS, "Unknown arm")
    # Only these two source strings enter the model message. Labels and author/patient
    # identifiers are in the local index, not the message sent to a future provider.
    messages = [dict(role="system", content=prompts["common"] + "\n" + prompts[arm]),
                dict(role="user", content=canonical({"proposition": item["text"], "reference": item["reference"]}))]
    body = dict(messages=messages, judge=config["judge"], generation=config["generation"])
    return dict(request_id=arm + ":" + item["proposition_id"], arm=arm,
                proposition_id=item["proposition_id"], reference_id=item["reference_id"],
                request_sha256=fingerprint(body), **body)


def schedule(inputs: list[dict], config: dict, prompts: dict) -> list[dict]:
    ordered = sorted(inputs, key=lambda r: (digest_text(config["schedule_seed"] + r["proposition_id"]), r["proposition_id"]))
    permutations = list(itertools.permutations(ARMS))
    result = []
    for index, item in enumerate(ordered):
        # Balanced rotations within each claim; independent conversations, no history.
        for arm in permutations[index % len(permutations)]:
            req = make_request(item, arm, config, prompts)
            result.append(dict(sequence=len(result) + 1, request_id=req["request_id"],
                proposition_id=item["proposition_id"], arm=arm, reference_id=item["reference_id"],
                request_sha256=req["request_sha256"], message_characters=sum(len(m["content"]) for m in req["messages"])))
    return result


def check_config(config: dict, prompts: dict) -> None:
    require(config["arms"] == list(ARMS), "Changed arm order")
    require(config["live_inference_authorized"] is False, "This task revision is offline only")
    require(config["budget"]["automatic_retries"] == config["budget"]["content_repair_calls"] == 0, "No retry/repair budget")
    words = [len(prompts[a].split()) for a in ("structured", "event_alignment")]
    require(max(words) / min(words) <= config["budget"]["structured_to_event_instruction_word_ratio_max"], "Control instructions differ too much in length")


def preparation_report(summary: dict) -> str:
    if summary["data_kind"] == "synthetic":
        return "# 虚构数据准备\n\n仅软件演练：12 条虚构命题、36 个虚构请求。未使用 VeriFact 患者资料，未调用模型；全部标签和响应均预先编写，不能据此判断三种方法的效果。\n"
    rows = "\n".join(f"| {a} | {s['valid_claims']} | {s['labels']['Supported']} | {s['labels']['Not Supported']} | {s['labels']['Not Addressed']} | {s['time_conflict_claims']} |" for a, s in summary["by_author"].items())
    return f'''# 004：实验准备结果

状态：**仅完成离线准备，真实推理尚未开始，尚无方法效果结果。**

按 003 冻结的 seed + patient ID 哈希顺序选开发组前 6 名：{", ".join(summary["selected_patients"])}。没有按标签或旧预测对错选样本。患者清单中的数值排序不是本次抽取顺序。其余 34 名开发患者及 40 名保留测试患者不进入本次队列、请求或评价。

| 作者 | 有效 claims | S | NS | NA | 已知时间冲突标记 |
| --- | ---: | ---: | ---: | ---: | ---: |
{rows}

共 {summary["valid_claims"]} 条有效命题，排除 {summary["invalid_excluded"]} 条 invalid，排除 ID 另存。主分析保留全部时间冲突行；预设敏感性分析对三臂同时排除这些 ID，不改日期或医生标签。

每条命题三种方式各调用一次，计划 {summary["planned_calls"]} 次。三臂使用同一实际 Judge、同一完整 reference、相同解码参数和 2,048 输出 token 上限，总输出上限暂计 {summary["maximum_output_tokens"]:,} tokens。该数值以最终服务确实将全部生成 token 计入同一上限为前提，不是费用估算。

普通结构化与事件核对均为五项检查、相同 JSON 格式、合计最多 200 个解释词；常规方式使用自由解释和空 checks，也可使用相同解释词数。相同上限不保证实际 token 或隐藏推理量相同。静态长度见 summary.json / request_schedule.csv；实际 token、费用、上下文适配和 thinking 配置尚待选定 Judge 后核实，禁止静默截断证据。

证据取自 release 的 R1-70B / rater-121（sentence facts、N100、rerank、absolute_time、current admission、deduplicate=True）。保存 reference 原文及 SHA-256，不补检索、不重新筛选日期。实得块数见 summary.json，不假设每条恰好 100 块。模型只看到命题和 reference，不看到 GT、既有预测、作者类型、parent 或完整 BHC。

主要比较为 event_alignment − structured；event_alignment − routine 和 structured − routine 为辅助比较。分别对 llm/human 调用 002 的 evaluate / paired_compare：valid-only、完整队列、三分类 PA/AC1/MCC、1,000 次患者 bootstrap，同时报告各类性能、非 S→S、NS↔NA、正确变错/错误改正和逐患者结果。六名患者只作探索；尤其 LLM 少数类很少，不以置信区间或单个净增益声称机制成立。

若事件核对不优于普通结构化，或只是通过全面变严增加 S→NS/NA，或收益伴随明显更高实际预算，则优先假设未得到清晰支持。原作者发布预测单列为历史参照，不能代替本轮 routine 重跑；三种新判断均须由同一实际模型执行。

待决定：Bedrock 可用的精确模型/版本、区域与推理配置；费用上限。待完成：本地 tokenizer 或获批后的计数接口核实所有请求的上下文与 token 预算、仅用虚构材料验证服务适配器。最后需用户明确确认真实推理，届时另存服务绑定后的新准备版本，不覆盖本记录。

文件：cohort_*.csv 为评价队列；inputs.jsonl 为本地命题和证据；request_schedule.csv 为固定调用顺序与哈希；historical_predictions_*.csv 为发布预测；prompts/ 与 config.json 为快照。虚构 dry-run 的分数不属于 VeriFact 实验成绩。
'''


def build_bundle(run: Path, cohort: list[dict], excluded: list[dict], inputs: list[dict],
                 config: dict, prompts: dict, selected: list[str], provenance: dict,
                 historical: list[dict] | None = None) -> dict:
    check_config(config, prompts)
    ids = {r["proposition_id"] for r in cohort}
    require(len(ids) == len(cohort) == len(inputs), "Input/cohort count mismatch")
    require({i["proposition_id"] for i in inputs} == ids, "Input/cohort identity mismatch")
    index = {r["proposition_id"]: r for r in cohort}
    for item in inputs:
        validate_input(item)
        row = index[item["proposition_id"]]
        require(all(row[k] == item[k] for k in ("subject_id", "hadm_id", "author_type")), "Cross-patient/author/admission input")
        require(row["subject_id"] in selected and row["invalid"] == "False" and row["proposition_type"] == "claim", "Out-of-scope claim")
    write_json(run / "config.json", config)
    (run / "prompts").mkdir()
    for name, text in prompts.items():
        (run / "prompts" / (name + ".md")).write_text(text, encoding="utf-8", newline="\n")
    write_jsonl(run / "inputs.jsonl", inputs)
    write_csv(run / "excluded_invalid.csv", excluded, list(cohort[0]))
    write_json(run / "provenance.json", provenance)
    calls = schedule(inputs, config, prompts)
    write_csv(run / "request_schedule.csv", calls)
    by_author = {}
    for author in ("llm", "human"):
        rows = [r for r in cohort if r["author_type"] == author]
        write_csv(run / f"cohort_{author}.csv", rows)
        if historical is not None:
            part = [r for r in historical if r["proposition_id"] in {c["proposition_id"] for c in rows}]
            require(len(part) == len(rows), "Missing historical baseline prediction")
            write_csv(run / f"historical_predictions_{author}.csv", part)
        by_author[author] = dict(valid_claims=len(rows), labels={lab: sum(r["human_gt"] == lab for r in rows) for lab in LABELS},
            time_conflict_claims=sum(r["time_metadata_conflict"] == "True" for r in rows),
            second_round_anomalies=sum(r["second_round_anomaly"] == "True" for r in rows))
    patients = [dict(subject_id=sid, rank=i + 1,
        ordering_hash=digest_text(SPLIT_SEED + sid),
        **{a: sum(r["subject_id"] == sid and r["author_type"] == a for r in cohort) for a in ("llm", "human")}) for i, sid in enumerate(selected)]
    write_csv(run / "selected_patients.csv", patients)
    summary = dict(stage="prepared_no_real_inference", data_kind=provenance["data_kind"],
        selected_patients=selected, valid_claims=len(cohort), invalid_excluded=len(excluded),
        by_author=by_author, planned_calls=len(calls),
        maximum_output_tokens=len(calls) * config["generation"]["max_output_tokens"],
        reference_blocks=distribution([len(reference_numbers(x["reference"])) for x in inputs]),
        reference_characters=distribution([len(x["reference"]) for x in inputs]),
        instruction_words={k: len(v.split()) for k, v in prompts.items()},
        message_characters={a: distribution([r["message_characters"] for r in calls if r["arm"] == a]) for a in ARMS},
        exact_input_tokens=None, cost_estimate_usd=None,
        inference_api_calls=0, real_model_predictions=0,
        same_reference_for_all_arms=True, labels_in_model_messages=False,
        pending=["exact_judge_and_region", "provider_parameter_mapping", "token_and_context_preflight", "spending_cap", "user_confirmation_for_real_inference"])
    write_json(run / "summary.json", summary)
    (run / "report.md").write_text(preparation_report(summary), encoding="utf-8", newline="\n")
    code = [Path(__file__), ROOT / "tasks/003_error_analysis/analyze.py",
            *sorted((ROOT / "src/verifact_research/evaluation").glob("*.py")), ROOT / "src/verifact_research/audit/common.py"]
    write_json(run / "manifest.json", dict(schema_version=1, stage="offline_preparation", data_kind=provenance["data_kind"],
        code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): digest_file(p) for p in code},
        output_sha256={p.relative_to(run).as_posix(): digest_file(p) for p in sorted(run.rglob("*")) if p.is_file()}))
    return summary


def prepare() -> Path:
    config = json.loads((TASK / "config.json").read_text(encoding="utf-8"))
    split_path = ROOT / "outputs/003_error_analysis/patient_groups.json"
    require(digest_file(split_path) == config["partition_sha256"], "Frozen partition changed")
    split = load_split()
    selected = patients_in_order(split, config["patient_count"])
    fm = json.loads((FORMAL / "manifest.json").read_text(encoding="utf-8"))
    master = FORMAL / "cohort_master.csv"
    require(digest_file(master) == fm["output_sha256"]["cohort_master.csv"], "002 cohort changed")
    cohort, excluded = select_cohort(subset_csv(master, "subject_id", set(selected)), selected)
    paths = ["propositions/propositions.csv.gz", "verifact/verdicts.parquet", "verifact/reference_payloads.parquet",
             "verifact/rater_configurations.csv", "verifact/model_metadata.csv"]
    before = {p: digest_file(RAW / p) for p in paths}
    require(all(before[p] == fm["input_sha256"][p] for p in paths), "Used release file differs from 002")
    configs = [r for r in read_csv(RAW / paths[3])[1] if r["rater_alias"] == config["reference_rater_alias"]]
    require(len(configs) == 1, "Ambiguous reference configuration")
    c = configs[0]
    expected = dict(model="R1-70B", fact_type="sentence", top_n="100", retrieval_method="rerank",
                    reference_format="absolute_time", reference_only_admission="True", deduplicate_text="True")
    require(all(c[k] == v for k, v in expected.items()), "Reference configuration differs from fixed baseline")
    models = [r for r in read_csv(RAW / paths[4])[1] if r["model"] == "R1-70B"]
    ids = {r["proposition_id"] for r in cohort}
    props_list = subset_csv(RAW / paths[0], "proposition_id", ids)
    props = {r["proposition_id"]: r for r in props_list}
    require(len(props) == len(props_list) == len(ids), "Missing/duplicate proposition text")
    with duckdb.connect() as con:
        con.register("selected", pd.DataFrame({"proposition_id": sorted(ids)}))
        preds = con.execute("SELECT v.proposition_id, v.reference_id, v.verdict FROM read_parquet(?) v JOIN selected USING(proposition_id) WHERE v.rater_alias = ?",
            [str(RAW / paths[1]), config["reference_rater_alias"]]).fetchall()
        require(len(preds) == len(ids) == len({r[0] for r in preds}), "Incomplete/duplicate reference coverage; do not shrink cohort")
        refids = {r[1] for r in preds}
        con.register("refs", pd.DataFrame({"reference_id": sorted(refids)}))
        refs_list = con.execute("SELECT r.reference_id, r.reference FROM read_parquet(?) r JOIN refs USING(reference_id)", [str(RAW / paths[2])]).fetchall()
    require(len(refs_list) == len(refids) == len(dict(refs_list)), "Missing/duplicate payload")
    payloads = dict(refs_list)
    links = {pid: rid for pid, rid, verdict in preds}
    inputs = []
    for row in cohort:
        pid = row["proposition_id"]
        p = props[pid]
        require(integer_id(p["subject_id"]) == row["subject_id"] and integer_id(p["hadm_id"]) == row["hadm_id"], "Source patient/admission differs")
        inputs.append({**{k: row[k] for k in ("proposition_id", "subject_id", "hadm_id", "author_type")},
            "text": p["text"], "reference_id": links[pid], "reference": payloads[links[pid]]})
    require(before == {p: digest_file(RAW / p) for p in paths}, "Input bytes changed during preparation")
    provenance = dict(data_kind="verifact_local", source_002="outputs/002_reproduce_paper_results/run_003",
        partition_sha256=digest_file(split_path), cohort_master_sha256=digest_file(master),
        raw_input_sha256=before, reference_configuration=c, historical_model_metadata=models,
        selection="First six development patients sorted by SHA256(frozen seed + canonical ID)",
        held_out_clinical_rows_exported=0, raw_unchanged=True)
    historical = [{"proposition_id": pid, "verdict": verdict} for pid, rid, verdict in preds]
    run = new_run(OUT, None, ROOT / "data/00_raw")
    summary = build_bundle(run, cohort, excluded, inputs, config, templates(), selected, provenance, historical)
    print(canonical(dict(run=str(run.relative_to(ROOT)), **summary)))
    return run


def load_bundle(path: Path):
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    for name, sha in manifest["output_sha256"].items():
        target = (path / name).resolve()
        require(path.resolve() in target.parents and digest_file(target) == sha, "Changed bundle artifact: " + name)
    config = json.loads((path / "config.json").read_text(encoding="utf-8"))
    prompts = {name: (path / "prompts" / (name + ".md")).read_text(encoding="utf-8") for name in ("common", *ARMS)}
    cohort = [r for a in ("llm", "human") for r in read_csv(path / f"cohort_{a}.csv")[1]]
    inputs = jsonl(path / "inputs.jsonl")
    return manifest, config, prompts, cohort, inputs


def parse_answer(text: str, arm: str, reference: str, word_limit: int = 200) -> dict:
    answer = strict_json(text)
    require(isinstance(answer, dict) and set(answer) == {"verdict", "reason", "checks"}, "Wrong answer schema")
    require(answer["verdict"] in LABELS, "Invalid label")
    require(isinstance(answer["reason"], str) and bool(answer["reason"].strip()), "Missing reason")
    checks = answer["checks"]
    require(isinstance(checks, list) and len(checks) == len(ASPECTS[arm]), "Wrong number of checks")
    nums = set(reference_numbers(reference))
    words = len(answer["reason"].split())
    for check, aspect in zip(checks, ASPECTS[arm]):
        require(isinstance(check, dict) and set(check) == {"aspect", "assessment", "evidence_ids"}, "Wrong check schema")
        require(check["aspect"] == aspect, "Wrong check order/aspect")
        require(isinstance(check["assessment"], str) and bool(check["assessment"].strip()), "Missing assessment")
        cites = check["evidence_ids"]
        require(isinstance(cites, list) and all(type(n) is int and n in nums for n in cites) and len(cites) == len(set(cites)), "Unknown/duplicate evidence ID")
        words += len(check["assessment"].split())
    require(words <= word_limit, "Visible explanation exceeds shared word budget")
    return answer


def assess_responses(inputs: list[dict], records: list[dict], config: dict, prompts: dict) -> tuple[dict, list[dict]]:
    expected = {q["request_id"]: (q, item) for item in inputs for arm in ARMS for q in [make_request(item, arm, config, prompts)]}
    counts = Counter(r.get("request_id") for r in records)
    errors = [{"request_id": k, "error": "missing/duplicate/unexpected response", "count": counts[k]} for k in set(expected) | set(counts) if counts[k] != 1 or k not in expected]
    predictions = {arm: [] for arm in ARMS}
    for record in records:
        key = record.get("request_id")
        if key not in expected or counts[key] != 1:
            continue
        request, item = expected[key]
        try:
            require(record["request_sha256"] == request["request_sha256"], "Request bytes/config mismatch")
            require(record["judge"] == config["judge"] and config["judge"]["model_id"] is not None, "Unbound/different Judge")
            require(config["generation"]["provider_parameter_mapping_verified"], "Generation mapping not verified")
            require(record["status"] == "success" and record["finish_reason"] == "stop", "Failed/truncated/filtered response")
            usage = record["usage"]
            require(all(type(usage[k]) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens", "reasoning_tokens")), "Missing/invalid usage accounting")
            require(usage["reasoning_tokens"] <= usage["output_tokens"] <= config["generation"]["max_output_tokens"], "Output budget exceeded or accounting inconsistent")
            if config["generation"]["thinking_mode"] == "disabled":
                require(usage["reasoning_tokens"] == 0, "Unexpected reasoning budget")
            answer = parse_answer(record["output_text"], request["arm"], item["reference"], config["budget"]["visible_explanation_word_limit"])
            predictions[request["arm"]].append(dict(proposition_id=item["proposition_id"], verdict=answer["verdict"]))
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(dict(request_id=key, error=str(exc)))
    return predictions, sorted(errors, key=lambda r: str(r["request_id"]))


def error_counts(rows: list[dict], predictions: list[dict]) -> dict:
    by_id = {r["proposition_id"]: r["verdict"] for r in predictions}
    pairs = [(r["human_gt"], by_id[r["proposition_id"]]) for r in rows]
    return dict(non_s_to_s=sum(a != "Supported" and b == "Supported" for a, b in pairs),
        s_to_non_s=sum(a == "Supported" and b != "Supported" for a, b in pairs),
        ns_na_confusion=sum({a, b} == {"Not Supported", "Not Addressed"} for a, b in pairs))


def evaluate_arms(cohort: list[dict], predictions: dict, iterations: int = 1000) -> dict:
    require(set(predictions) == set(ARMS), "Missing/unknown experimental arm")
    # Run strict alignment before any author or sensitivity filtering; extra rows
    # must not disappear during subsetting.
    for arm in ARMS:
        evaluate(cohort, predictions[arm], profile="none", missing="error")
    result = {}
    for author in ("llm", "human"):
        main = [r for r in cohort if r["author_type"] == author]
        result[author] = {}
        for scope, rows in (("primary", main), ("exclude_time_conflicts", [r for r in main if r["time_metadata_conflict"] == "False"])):
            ids = {r["proposition_id"] for r in rows}
            if not rows:
                result[author][scope] = dict(status="empty_sensitivity_cohort", excluded_ids=sorted(r["proposition_id"] for r in main))
                continue
            pp = {a: [r for r in predictions[a] if r["proposition_id"] in ids] for a in ARMS}
            metrics = {a: evaluate(rows, pp[a], profile="research_patient", missing="error", iterations=iterations) for a in ARMS}
            contrasts = {}
            for base, candidate in PAIRS:
                bc = {r["proposition_id"]: r["verdict"] for r in pp[base]}
                cc = {r["proposition_id"]: r["verdict"] for r in pp[candidate]}
                transitions = Counter((r["human_gt"], bc[r["proposition_id"]], cc[r["proposition_id"]]) for r in rows)
                contrasts[candidate + "_minus_" + base] = dict(
                    **paired_compare(rows, pp[base], pp[candidate], iterations=iterations),
                    error_to_correct=sum(n for (g, b, c), n in transitions.items() if b != g and c == g),
                    correct_to_error=sum(n for (g, b, c), n in transitions.items() if b == g and c != g),
                    transitions=[dict(gt=g, baseline=b, candidate=c, count=n) for (g, b, c), n in sorted(transitions.items())])
            per_patient = {sid: {a: evaluate([r for r in rows if r["subject_id"] == sid],
                [r for r in pp[a] if r["proposition_id"] in {c["proposition_id"] for c in rows if c["subject_id"] == sid}], profile="none")
                for a in ARMS} for sid in sorted({r["subject_id"] for r in rows})}
            result[author][scope] = dict(metrics=metrics, contrasts=contrasts, per_patient=per_patient,
                errors={a: error_counts(rows, pp[a]) for a in ARMS},
                excluded_ids=sorted({r["proposition_id"] for r in main} - ids))
    return result


def score(bundle: Path, responses: Path, output_root: Path) -> Path:
    manifest, config, prompts, cohort, inputs = load_bundle(bundle)
    run = new_run(output_root, None, ROOT / "data/00_raw")
    raw = responses.read_bytes()
    (run / "responses.original.jsonl").write_bytes(raw)
    try:
        records = jsonl(responses)
        require(all(isinstance(r, dict) for r in records), "Non-object response envelope")
        predictions, errors = assess_responses(inputs, records, config, prompts)
    except (ValueError, TypeError) as exc:
        records, predictions, errors = [], {}, [dict(error=str(exc))]
    write_json(run / "response_checks.json", dict(status="blocked" if errors else "pass", errors=errors,
        expected=len(inputs) * 3, received=len(records), automatically_repaired=0))
    if errors:
        write_json(run / "status.json", dict(status="blocked_incomplete_or_invalid_responses", scored=False))
    else:
        for arm in ARMS:
            write_csv(run / f"predictions_{arm}.csv", predictions[arm])
        metrics = evaluate_arms(cohort, predictions, config["evaluation"]["iterations"])
        write_json(run / "metrics.json", metrics)
        usage = {a: {k: sum(r["usage"][k] for r in records if r["request_id"].startswith(a + ":")) for k in ("input_tokens", "output_tokens", "reasoning_tokens")} for a in ARMS}
        write_json(run / "usage.json", dict(data_kind=manifest["data_kind"], by_arm=usage,
            actual_budget_equality_assumed=False, mocked=manifest["data_kind"] == "synthetic"))
        write_json(run / "status.json", dict(status="synthetic_pipeline_pass" if manifest["data_kind"] == "synthetic" else "scored_local_responses",
            scored=True, clinical_effect_established=False))
    write_json(run / "manifest.json", dict(bundle_manifest_sha256=digest_file(bundle / "manifest.json"),
        responses_sha256=digest_text(raw.decode("utf-8")), code_sha256=digest_file(Path(__file__)),
        output_sha256={p.name: digest_file(p) for p in sorted(run.iterdir()) if p.is_file()}))
    return run


def synthetic(output_root: Path) -> Path:
    fixture = json.loads((TASK / "fixtures/synthetic.json").read_text(encoding="utf-8"))
    require(fixture["entirely_fictional"] is True, "Synthetic-only fixture required")
    config = json.loads((TASK / "config.json").read_text(encoding="utf-8"))
    config["judge"] = dict(provider="local_fixture", model_id="mock-not-a-model-v1", model_revision="v1", region="none",
        inference_profile=None, context_window_tokens=32000, tokenizer_or_counting_method="mocked_counts_not_tokens")
    config["generation"].update(thinking_mode="disabled", provider_parameter_mapping_verified=True)
    cohort, inputs = [], []
    for i, case in enumerate(fixture["cases"]):
        for author in ("llm", "human"):
            pid = f"fictional-{i+1}-{author}"
            sid = f"fictional-patient-{i+1}"
            cohort.append(dict(proposition_id=pid, subject_id=sid, hadm_id=f"fictional-admission-{i+1}", author_type=author,
                proposition_type="claim", human_gt=case["fixture_label"], invalid="False",
                time_metadata_conflict=str(i == 5), second_round_anomaly="False"))
            inputs.append({**{k: cohort[-1][k] for k in ("proposition_id", "subject_id", "hadm_id", "author_type")},
                "text": case["proposition"], "reference": case["reference"], "reference_id": digest_text(case["reference"])})
    run = new_run(output_root, None, ROOT / "data/00_raw")
    bundle = run / "bundle"
    bundle.mkdir()
    build_bundle(bundle, cohort, [], inputs, config, templates(), list(dict.fromkeys(r["subject_id"] for r in cohort)),
        dict(data_kind="synthetic", fixture_sha256=digest_file(TASK / "fixtures/synthetic.json")))
    truth = {r["proposition_id"]: r["human_gt"] for r in cohort}
    records = []
    for item in inputs:
        for arm in ARMS:
            request = make_request(item, arm, config, templates())
            answer = dict(verdict=truth[item["proposition_id"]], reason="Canned fixture response; no clinical inference was performed.",
                checks=[dict(aspect=aspect, assessment="Synthetic plumbing check only.", evidence_ids=[1]) for aspect in ASPECTS[arm]])
            records.append(dict(request_id=request["request_id"], request_sha256=request["request_sha256"], judge=config["judge"],
                status="success", finish_reason="stop", output_text=canonical(answer),
                usage=dict(input_tokens=500, output_tokens=200, reasoning_tokens=0), latency_ms=0))
    write_jsonl(run / "mock_responses.jsonl", records)
    scored = score(bundle, run / "mock_responses.jsonl", run / "scoring")
    (run / "README.md").write_text("# 纯虚构离线演练\n\n6 名虚构患者、12 条虚构命题、36 条预写响应；没有模型、API 或 VeriFact 临床文本。三个臂故意返回相同的预写标签，验证解析、配对和共用评价通路；分数不能说明方法有效。usage 中的 token 是固定假数，不用于真实预算估计。\n", encoding="utf-8", newline="\n")
    print(canonical(dict(synthetic_run=str(run), scoring=str(scored), external_calls=0)))
    return run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="Freeze local six-patient inputs; no network")
    fake = sub.add_parser("synthetic", help="Only fictional fixtures and canned responses; no model")
    fake.add_argument("--output-root", type=Path, default=OUT / "synthetic")
    scored = sub.add_parser("score", help="Validate and score saved responses locally; never calls a provider")
    scored.add_argument("--bundle", type=Path, required=True)
    scored.add_argument("--responses", type=Path, required=True)
    scored.add_argument("--output-root", type=Path, default=OUT / "evaluations")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "synthetic":
        synthetic(args.output_root)
    else:
        result = score(args.bundle.resolve(), args.responses.resolve(), args.output_root)
        print(result)
        if json.loads((result / "status.json").read_text(encoding="utf-8"))["status"].startswith("blocked"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
