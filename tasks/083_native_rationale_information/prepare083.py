"""Freeze rationale cleaning and extraction requests without reading evaluation GT."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import inventory083 as base

OUT = base.OUT
MODEL = "qwen3.5-flash-2026-02-23"
MAX_TOKENS = 600
KEEP_ASPECTS = ("relevant_evidence", "supporting_case", "opposing_case")

SYSTEM = """You organize statements in one existing rationale. This is text extraction, not a new clinical judgment. Return one JSON object with key arguments, a list of at most six objects. Each object has exactly stance, basis, dimension, quote. stance: supports, opposes, or uncertain. basis: explicit_record, paraphrase, inference, explicit_wording_required, contradiction, absence, irrelevant, or other. dimension: event_status, time, negation, certainty, number, attribution, scope, or other. Quote must be a short exact contiguous substring copied from the supplied rationale text. Include a field only when those exact words warrant it. Do not infer unmentioned matching, contradiction, or completion. Silence about a dimension is not a match. Distinguish no completed event documented from an explicit statement that it did not happen. Do not output a final verdict, class label, probability, or new medical fact. If no grounded argument exists, return {\"arguments\": []}."""

FINAL_PATTERNS = (
    re.compile(r"(?i)\b(?:the\s+|this\s+)?(?:complete\s+)?(?:proposition|claim|statement)\s+(?:is|was|remains)\s+(?:not\s+|only\s+partially\s+)?(?:fully\s+)?(?:supported|addressed)\b"),
    re.compile(r"(?i)\b(?:final\s+)?(?:verdict|classification|label)\s*(?:is|=|:)\s*(?:not\s+supported|not\s+addressed|supported)\b"),
    re.compile(r"(?i)\b(?:classify|classified)\s+(?:as\s+)?(?:not\s+supported|not\s+addressed|supported)\b"),
    re.compile(r"(?i)\b(?:supported|not\s+supported|not\s+addressed)\s*[:=]\s*\d+(?:\.\d+)?\s*%?"),
)


def clean_piece(value):
    value = str(value or "")[:1600]
    removed = 0
    for pattern in FINAL_PATTERNS:
        value, n = pattern.subn("[final decision omitted]", value)
        removed += n
    value = re.sub(r"\s+", " ", value).strip()
    return value, removed


def clean(row):
    raw_fields = [("reason", row.get("reason") or "")]
    checks = row.get("checks")
    if isinstance(checks, list):
        for item in checks:
            if isinstance(item, dict) and item.get("aspect") in KEEP_ASPECTS:
                raw_fields.append((item["aspect"], item.get("assessment") or ""))
    parts, removals, raw_chars, cleaned_chars, truncations = [], 0, 0, 0, 0
    for tag, content in raw_fields:
        if not isinstance(content, str):
            continue
        raw_chars += len(content)
        truncations += int(len(content) > 1600)
        filtered, count = clean_piece(content)
        removals += count
        cleaned_chars += len(filtered)
        if filtered:
            parts.append(f"[{tag}] {filtered}")
    return "\n".join(parts), {"source_chars": raw_chars, "cleaned_chars": cleaned_chars,
                               "final_phrase_replacements": removals,
                               "truncated_sections": truncations,
                               "included_sections": [tag for tag, _ in raw_fields]}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def main():
    rows = base.lines("outputs/083_native_rationale_information/native_texts.jsonl")
    assert len(rows) == 2 * (459 + 532 + 24)
    cleaned, by_hash = [], {}
    for row in rows:
        value, stats = clean(row)
        token = sha(value.encode("utf-8"))
        cleaned.append({"phase": row["phase"], "arm": row["arm"], "id": row["id"],
                        "sid": row["sid"], "body_sha256": row["body_sha256"],
                        "content_sha256": row["content_sha256"],
                        "cleaned_sha256": token, "cleaned_text": value, **stats})
        if row["arm"] == "F4" and value:
            by_hash.setdefault(token, value)
    assert len([x for x in cleaned if x["arm"] == "F4"]) == 1015
    jobs = []
    for token, value in sorted(by_hash.items()):
        body = {"model": MODEL, "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": canonical({"rationale_text": value})}],
            "temperature": 0, "max_tokens": MAX_TOKENS, "enable_thinking": False,
            "response_format": {"type": "json_object"}}
        jobs.append({"request_id": "083:" + token[:24], "cleaned_sha256": token,
                     "body_sha256": sha(canonical(body).encode("utf-8")), "body": body})
    base.write("cleaned_inputs.jsonl", cleaned)
    base.write("extraction_jobs.jsonl", jobs)
    f4 = [x for x in cleaned if x["arm"] == "F4"]
    sizes = sorted(x["cleaned_chars"] for x in f4)
    jobs_bytes = [len(canonical(x["body"]).encode("utf-8")) for x in jobs]
    estimate = sum(((n + 2000) * .2 + MAX_TOKENS * 2) / 1e6 for n in jobs_bytes)
    base.write("preflight_and_cost_plan.json", {
        "status": "FROZEN_BEFORE_083_CHARGED_API_AND_EVALUATION_GT",
        "cap_original_cny": 20.0,
        "model": MODEL, "provider": "Alibaba Model Studio Beijing workspace",
        "official_price_input_output_per_million_cny": [0.2, 2.0],
        "price_url": "https://help.aliyun.com/zh/model-studio/qwen3-5-flash",
        "json_url": "https://help.aliyun.com/zh/model-studio/qwen-structured-output",
        "new_main_judge_calls": 0, "extra_embedding_api_calls": 0,
        "logical_f4_answers": len(f4), "unique_extraction_requests": len(jobs),
        "estimated_max_if_all_600_output_tokens_cny": estimate,
        "retry_and_unknown_buffer_cny": 5.0,
        "input_body_bytes_min_median_max": [min(jobs_bytes), sorted(jobs_bytes)[len(jobs_bytes)//2], max(jobs_bytes)],
        "cleaned_chars_min_median_p95_max": [sizes[0], sizes[len(sizes)//2], sizes[int(.95*len(sizes))], sizes[-1]],
        "cleaned_total_replacements": sum(x["final_phrase_replacements"] for x in f4),
        "cleaned_count_with_replacements": sum(x["final_phrase_replacements"] > 0 for x in f4),
        "truncated_section_count": sum(x["truncated_sections"] for x in f4),
        "cleaned_inputs_sha256": base.digest((OUT / "cleaned_inputs.jsonl").read_bytes()),
        "jobs_sha256": base.digest((OUT / "extraction_jobs.jsonl").read_bytes()),
        "cleaning_code_sha256": base.digest(Path(__file__).read_bytes()),
        "native_manifest_sha256": base.digest((OUT / "source_manifest.jsonl").read_bytes()),
        "evaluation_GT_read": False,
        "preflight_rule": "first 3 request IDs in sorted job list; successful responses reused in full run",
    })
    print(json.dumps({"F4": len(f4), "unique_jobs": len(jobs),
                      "worst_request_reservation_cny": round(estimate, 4),
                      "input_bytes_max": max(jobs_bytes),
                      "cleaned_chars_p95": sizes[int(.95*len(sizes))],
                      "phrases_removed": sum(x["final_phrase_replacements"] for x in f4)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
