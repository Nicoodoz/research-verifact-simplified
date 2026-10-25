"""Validate local case notes, render a casebook and summarize exploratory observations."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from analyze import (ROOT, RAW, OUT, MODELS, digest_file, digest_text, integer_id,
                     load_split, new_run, read_csv, require, write_csv, write_json)
from inspect_cases import compare_references, facts


OUTPUT_FIELDS = ("reason", "reasoning_chain", "reasoning_final_answer")


def model_output(case: dict, model: str, field: str) -> str:
    require(model in MODELS and field in OUTPUT_FIELDS, "Unknown model output field")
    value = case["models"][model]
    require(value["proposition_id"] == case["selection"]["proposition_id"], "Cross-proposition model output")
    text = value.get(field)
    require(isinstance(text, str), "Missing model output field")
    return text


def fenced(text: str) -> str:
    fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", text)), default=0))
    return f"{fence}text\n{text}\n{fence}"


def render_full_output(case: dict, model: str) -> str:
    lines = ["<details>", f"<summary>{model}：完整生成输出（非内部因果机制证明）</summary>", ""]
    for field in ("reasoning_chain", "reasoning_final_answer"):
        text = model_output(case, model, field)
        lines += [f"**{field}**；SHA-256：`{digest_text(text)}`。", "", fenced(text) if text else "（发布字段为空）", ""]
    return "\n".join([*lines, "</details>", ""])


def final_answer_comparison(case: dict, model: str) -> dict:
    text = model_output(case, model, "reasoning_final_answer")
    candidates = []
    for match in re.finditer(r"\{", text):
        try:
            value, length = json.JSONDecoder().raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and {"verdict", "reason"} <= value.keys():
            candidates.append(dict(start=match.start(), end=match.start() + length, value=value))
    result = dict(json_object_count=len(candidates), candidates=candidates,
                  verdict_equal=None, reason_equal=None)
    if len(candidates) == 1:
        value = candidates[0]["value"]
        result.update({field + "_equal": value[field] == case["models"][model][field]
                       for field in ("verdict", "reason")})
    return result


def span(text: str, start: int, end: int) -> dict:
    require(0 <= start < end <= len(text), "Invalid evidence span")
    return dict(start=start, end=end, quote=text[start:end], source_sha256=digest_text(text))


def resolve_evidence(case: dict, notes: dict, spec: dict) -> dict:
    if spec["source"] == "model_output":
        model, field = spec["model"], spec["field"]
        text = model_output(case, model, field)
        evidence = dict(source="model_output", model=model, field=field,
                        proposition_id=case["selection"]["proposition_id"],
                        rater_alias=case["models"][model]["rater_alias"],
                        **span(text, spec["start"], spec["end"]))
        require(evidence["quote"] == spec["quote"], "Model output quotation changed")
        return evidence
    if spec["source"] == "reference":
        model = spec.get("model", "R1-70B")
        ref = case["models"][model]
        matches = [f for f in facts(ref["reference"]) if f["quote"].startswith(str(spec["fact_number"]) + ". Date: ")]
        require(len(matches) == 1, "Ambiguous/missing reference block")
        f = matches[0]
        return dict(source="reference", model=model, reference_id=ref["reference_id"],
                    fact_number=spec["fact_number"], **span(ref["reference"], f["start"], f["end"]))
    require(spec["source"] == "ehr", "Unknown evidence source")
    n = notes[spec["row_id"]]
    require(integer_id(n["SUBJECT_ID"]) == case["selection"]["subject_id"], "Cross-patient evidence rejected")
    return dict(source="ehr", row_id=n["ROW_ID"], subject_id=integer_id(n["SUBJECT_ID"]),
                hadm_id=integer_id(n["HADM_ID"]), target_admission=integer_id(n["HADM_ID"]) == case["selection"]["hadm_id"],
                chartdate=n["CHARTDATE"], charttime=n["CHARTTIME"], storetime=n["STORETIME"],
                category=n["CATEGORY"], description=n["DESCRIPTION"], **span(n["TEXT"], spec["start"], spec["end"]))


def verify_evidence(case: dict, notes: dict, evidence: dict) -> None:
    if evidence["source"] == "model_output":
        model = evidence["model"]
        text = model_output(case, model, evidence["field"])
        require(evidence["proposition_id"] == case["selection"]["proposition_id"]
                and evidence["rater_alias"] == case["models"][model]["rater_alias"], "Model output identity changed")
    elif evidence["source"] == "reference":
        text = case["models"][evidence["model"]]["reference"]
        require(digest_text(text) == evidence["reference_id"], "Reference hash mismatch")
    else:
        n = notes[evidence["row_id"]]
        require(integer_id(n["SUBJECT_ID"]) == case["selection"]["subject_id"], "Cross-patient evidence")
        require(evidence["subject_id"] == integer_id(n["SUBJECT_ID"])
                and evidence["hadm_id"] == integer_id(n["HADM_ID"])
                and evidence["target_admission"] == (integer_id(n["HADM_ID"]) == case["selection"]["hadm_id"]), "Evidence admission metadata changed")
        require(all(evidence[k.lower()] == n[k] for k in ("CHARTDATE", "CHARTTIME", "STORETIME", "CATEGORY", "DESCRIPTION")), "Evidence note metadata changed")
        text = n["TEXT"]
    require(span(text, evidence["start"], evidence["end"]) == {k: evidence[k] for k in ("start", "end", "quote", "source_sha256")}, "Evidence text or offsets changed")


def reference_comparison(case: dict) -> dict:
    a, b = [case["models"][m]["reference"] for m in MODELS]
    result = compare_references(a, b)
    def texts(ref: str) -> Counter:
        ff = facts(ref)
        require(all(" | Text: " in f["quote"] for f in ff), "Unrecognized reference syntax")
        return Counter(re.sub(r"\s+", " ", f["quote"].split(" | Text: ", 1)[1]).strip() for f in ff)
    aa, bb = texts(a), texts(b)
    result.update(normalized_text_multiset_equal=aa == bb,
                  text_only_a=list((aa-bb).elements()), text_only_b=list((bb-aa).elements()))
    return result


def render_case(case: dict, review: dict, comparison: dict) -> str:
    s, h = case["selection"], case["human"]
    lines = [f"# {s['case_id']}：{review['claim_zh']}", "", "中文释义和分析不是医生新标注。", "",
        f"proposition_id：`{s['proposition_id']}`；subject_id：`{s['subject_id']}`；hadm_id：`{s['hadm_id']}`。",
        f"作者：{s['author_type']}；类型：claim；invalid：{s['invalid']}；最终 GT：**{h['human_gt']}**。",
        f"初始投票：{h['verdict1']} / {h['verdict2']} / {h['verdict3']}；第二轮：{h['verdict4'] or '空'} / {h['verdict5'] or '空'}。",
        f"抽样理由：{s['selection_reason']}；患者上限放宽：{s['patient_cap_relaxed']}。", "", "## 原始命题与上下文", "",
        case["proposition"]["text"], "", "原 parent（待核验文本，不是证据）：", "", "```text", case["proposition"]["parent_text_chunk"], "```", "",
        "完整 BHC、医生所有字段、两模型的原始输出和完整 reference 见 " + f"[原始案例包](../../cases/{s['case_id']}.json)。", "",
        "医生原始评论（空白即未提供；不补写）：", ""]
    comments = {k: v for k, v in h.items() if "comment" in k and v}
    lines += ["```json", json.dumps(comments, ensure_ascii=False, indent=2), "```", "", "## 模型实际输出", ""]
    for model in MODELS:
        v = case["models"][model]
        lines += [f"**{model}：{v['verdict']}**；rater `{v['rater_alias']}`。", "", v["reason"] or "（理由为空）", "",
                  f"reference_id：`{v['reference_id']}`；输入字符数 {len(v['reference'])}。", ""]
        lines += [render_full_output(case, model), ""]
    if "output_review" in review:
        lines += ["**本次完整输出复查：** " + review["output_review"]["finding"], "",
                  "逐模型阅读范围与原文字段指纹见 [output_review.json](../output_review.json)。", ""]
    lines += [f"逐字相同：{comparison['exact_equal']}；保留时间/类别的归一化块集合相同：{comparison['normalized_block_multiset_equal']}；仅正文集合相同：{comparison['normalized_text_multiset_equal']}。这不是临床等价性证明。", "",
        "## 探索性阅读", "", "**观察：** " + review["observation"], "", "**可能解释：** " + review["hypothesis"], "",
        "**不确定性：** " + review["uncertainty"], "", "**证据强度：** " + review["confidence"], "",
        "分析标签（可重叠，非医学 GT）：" + ", ".join(review["tags"]), "", "## 原文回查锚点", "",
        "偏移均为解码后 Python 字符索引，左闭右开；不是字节位置或 PDF 页码。完整原文字段的 SHA-256 在机器结果中保存。", ""]
    for i, e in enumerate(review["resolved_evidence"], 1):
        if e["source"] == "model_output":
            source = f"{e['model']} {e['field']}，rater={e['rater_alias']}，proposition_id={e['proposition_id']}（生成文本，不是临床证据）"
        elif e["source"] == "reference":
            source = f"{e['model']} reference，第 {e['fact_number']} 项"
        else:
            source = f"EHR ROW_ID={e['row_id']}，HADM_ID={e['hadm_id']}，target={e['target_admission']}，CHARTTIME={e['charttime'] or '空'}，CHARTDATE={e['chartdate']}，STORETIME={e['storetime'] or '空'}"
        lines += [f"**E{i}**：{source}；[{e['start']}:{e['end']}]；SHA-256：`{e['source_sha256']}`。", "", fenced(e["quote"]), ""]
    if review.get("negative_search"):
        lines += [f"限定阴性检索词：`{review['negative_search']}`。命中数与搜索范围见 reviews.json；不是全 EHR 医学否定证据。", ""]
    return "\n".join(lines)


def build(run_name: str, note_path: Path) -> Path:
    require(re.fullmatch(r"run_\d{3,}", run_name) is not None, "Invalid run name")
    run = OUT / run_name
    split = load_split()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    require(digest_file(OUT / "patient_groups.json") == manifest["partition_sha256"], "Frozen split changed")
    require(all(digest_file(run / p) == sha for p, sha in manifest["output_sha256"].items()), "Extraction output modified")
    require(all(digest_file(RAW / p) == sha for p, sha in manifest["raw_input_sha256"].items()), "Raw input changed")
    bundle = json.loads(note_path.read_text(encoding="utf-8"))
    require(bundle["medical_gold"] is False, "Exploratory notes must not claim to be gold")
    cases = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "cases").glob("*.json"))}
    reviews = bundle["cases"]
    require(len(reviews) == len({r["case_id"] for r in reviews}) and set(cases) == {r["case_id"] for r in reviews}, "Incomplete/duplicate review coverage")
    notes = {n["ROW_ID"]: n for n in json.loads((run / "ehr_notes.json").read_text(encoding="utf-8"))}
    exploration = set(split["groups"]["exploration"])
    require(all(c["selection"]["subject_id"] in exploration for c in cases.values()), "Case outside exploration")
    require(all(integer_id(n["SUBJECT_ID"]) in exploration for n in notes.values()), "EHR outside exploration")
    number = 1
    while (run / f"review_{number:03d}").exists():
        number += 1
    output = new_run(run, f"review_{number:03d}", ROOT / "data/00_raw")
    (output / "cases").mkdir()
    comparisons, index, all_evidence = {}, [], []
    for r in reviews:
        c = cases[r["case_id"]]
        r["resolved_evidence"] = [resolve_evidence(c, notes, e) for e in r["evidence"]]
        for e in r["resolved_evidence"]:
            verify_evidence(c, notes, e)
            all_evidence.append(e)
        if r.get("negative_search"):
            pattern = re.compile(r["negative_search"], re.I)
            nn = [n for n in notes.values() if integer_id(n["SUBJECT_ID"]) == c["selection"]["subject_id"]]
            hits = sum(len(pattern.findall(n["TEXT"])) for n in nn)
            ref_hits = {m: len(pattern.findall(c["models"][m]["reference"])) for m in MODELS}
            require(hits == 0 and all(v == 0 for v in ref_hits.values()), "Claimed zero-match search is false")
            r["negative_search_result"] = dict(ehr_notes=len(nn), ehr_hits=hits, reference_hits=ref_hits, entire_ehr_absence_proven=False)
        d = reference_comparison(c)
        comparisons[r["case_id"]] = d
        index.append(dict(c["selection"], tags=";".join(r["tags"]), medical_gold=False))
        with (output / "cases" / f"{r['case_id']}.md").open("x", encoding="utf-8", newline="\n") as f:
            f.write(render_case(c, r, d))
    tags = sorted({t for r in reviews for t in r["tags"]})
    tag_summary = {t: dict(cases=[r["case_id"] for r in reviews if t in r["tags"]],
        patients=len({cases[r["case_id"]]["selection"]["subject_id"] for r in reviews if t in r["tags"]}),
        by_author=dict(Counter(cases[r["case_id"]]["selection"]["author_type"] for r in reviews if t in r["tags"]))) for t in tags}
    expected = read_csv(run / "candidate_index.csv")[1]
    agreement = []
    for author in ("llm", "human"):
        for level in ("3", "2", "0"):
            rr = [r for r in expected if r["author_type"] == author and r["initial_agreement"] == level]
            agreement.append(dict(author=author, initial_agreement=level, n=len(rr), errors=sum(r["human_gt"] != r["baseline_verdict"] for r in rr)))
    summary = dict(case_n=len(cases), evidence_spans=len(all_evidence), case_patients=len({c["selection"]["subject_id"] for c in cases.values()}),
        evidence_spans_by_source=dict(Counter(e["source"] for e in all_evidence)),
        initial_agreement=dict(Counter(c["selection"]["initial_agreement"] for c in cases.values())),
        error_initial_agreement=dict(Counter(c["selection"]["initial_agreement"] for c in cases.values() if c["selection"]["human_gt"] != c["selection"]["baseline_verdict"])),
        tags=tag_summary, reference_exact_equal=sum(d["exact_equal"] for d in comparisons.values()),
        reference_timed_multiset_equal=sum(d["normalized_block_multiset_equal"] for d in comparisons.values()),
        reference_text_multiset_equal=sum(d["normalized_text_multiset_equal"] for d in comparisons.values()),
        baseline_actual_fact_counts=dict(Counter(d["facts_a"] for d in comparisons.values())),
        no_test_or_development_case_exports=True, medical_gold=False)
    write_json(output / "review_notes_snapshot.json", json.loads(note_path.read_text(encoding="utf-8")))
    write_json(output / "reviews.json", bundle)
    write_json(output / "reference_comparison.json", comparisons)
    write_json(output / "summary.json", summary)
    write_csv(output / "case_index.csv", index)
    write_csv(output / "agreement_diagnostics.csv", agreement)
    if "revision" in bundle:
        output_reviews = []
        for r in reviews:
            c = cases[r["case_id"]]
            scope = r["output_review"]["models_read"]
            require(set(scope) == set(MODELS), "Incomplete output review scope")
            require(scope["R1-70B"] == "full", "Baseline full output review not recorded")
            for model in MODELS:
                require(scope[model] in {"full", "reason_only"}, "Invalid output review scope")
                output_reviews.append(dict(case_id=r["case_id"], model=model,
                    proposition_id=c["selection"]["proposition_id"], rater_alias=c["models"][model]["rater_alias"],
                    reading_scope=scope[model], finding=r["output_review"]["finding"],
                    final_answer_comparison=final_answer_comparison(c, model),
                    fields={field: dict(characters=len(model_output(c, model, field)),
                        sha256=digest_text(model_output(c, model, field))) for field in OUTPUT_FIELDS}))
        write_json(output / "output_review.json", dict(revision=bundle["revision"],
            entries=output_reviews, automated_checks_prove_reading_or_interpretation=False))
    checks = dict(partition_unchanged=True, cases_and_ehr_in_exploration=True,
        all_24_initial_cases_reviewed=len(cases) == 24, raw_hashes_unchanged=True,
        extraction_hashes_valid=True, evidence_spans_verified=len(all_evidence),
        negative_search_verified=True, gt_relabelled=False,
        complete_generated_outputs_rendered=len(cases) * len(MODELS),
        interpretation_independently_clinically_validated=False)
    write_json(output / "checks.json", checks)
    # Human-readable synthesis is rendered separately from the case notes, using the template below.
    template_path = note_path.parent / "report_template.md"
    template = template_path.read_text(encoding="utf-8")
    with (output / "report_template.md").open("x", encoding="utf-8", newline="\n") as f:
        f.write(template)
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    metric_lines = []
    for a in ("llm", "human"):
        for model in MODELS:
            m = metrics[a][model]
            metric_lines.append(f"| {a} claim | {model} | {m['coverage']['evaluated_n']} | {m['percent_agreement']:.2%} | {m['gwet_ac1']:.4f} | {m['mcc']:.4f} |")
    case_lines = [f"| [{r['case_id']}](cases/{r['case_id']}.md) | {r['claim_zh']} | {cases[r['case_id']]['human']['human_gt']} | {cases[r['case_id']]['models']['R1-70B']['verdict']} | {r['confidence']} |" for r in reviews]
    report = template.replace("{{EXPLORATION_IDS}}", ", ".join(split["groups"]["exploration"]))
    report = report.replace("{{PARTITION_SHA256}}", manifest["partition_sha256"]).replace("{{METRIC_ROWS}}", "\n".join(metric_lines)).replace("{{CASE_ROWS}}", "\n".join(case_lines))
    for tag, values in tag_summary.items():
        report = report.replace("{{TAG_" + tag + "_CASES}}", str(len(values["cases"])))
        report = report.replace("{{TAG_" + tag + "_PATIENTS}}", str(values["patients"]))
    require("{{" not in report, "Unfilled report placeholder")
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as f:
        f.write(report)
    write_json(output / "manifest.json", dict(source_extraction_manifest_sha256=digest_file(run / "manifest.json"),
        partition_sha256=digest_file(OUT / "patient_groups.json"), review_notes_sha256=digest_file(note_path),
        code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): digest_file(p) for p in sorted((ROOT / "tasks/003_error_analysis").glob("*.py"))},
        report_template_sha256=digest_file(template_path),
        output_sha256={str(p.relative_to(output)).replace('\\', '/'): digest_file(p) for p in sorted(output.rglob("*")) if p.is_file()}))
    print(json.dumps({"review": str(output.relative_to(ROOT)), **summary}, ensure_ascii=False))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="run_001")
    parser.add_argument("--notes", type=Path, default=OUT / "review_notes.json")
    args = parser.parse_args()
    build(args.run, args.notes.resolve())
