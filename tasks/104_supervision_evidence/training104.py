"""104 paired supervision interface; no model loading, network, or training.

The two arms share this exact prompt. Only the supervised answer changes.
``encode_lists(tokenizer, row)`` has the 103 worker's return contract and can be
imported by a future, separately authorized worker without changing optimizer,
LoRA, or input handling. Source offsets stay in metadata, not model answers.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

LABELS = ("Supported", "Not Supported", "Not Addressed")
PAIR_FIELDS = (
    "id", "sid", "author", "GT", "claim", "reference", "reference_id",
    "reference_sha256",
)
SYSTEM = (
    "You are judging whether text written about a patient is supported by "
    "information from the patient's electronic health record."
)
INSTRUCTIONS = '''## Task:
Using the provided reference from the patient's electronic health record, determine whether the text is supported, not supported, or not addressed by the reference context.

## Detailed Instructions:
1. Compare the text and reference in the input JSON. Treat the reference as the source of truth.
2. First determine whether the specific assertion is addressed by the reference context. A related topic or entity alone need not address the assertion's event, participant, time, or key qualification.
3. Use exactly one verdict:
   - "Not Addressed": the text is not addressed by the reference context.
   - "Supported": the text is addressed and fully supported by the reference context.
   - "Not Supported": the text is addressed but not fully supported, including partially supported text. Absence of a matching word alone is not contradictory evidence.
4. Return a JSON object with the required key "verdict". Optional keys are "evidence" (a list of brief, exact quotations from the reference) and "relation" (a concise explanation of the decisive factual correspondence). If supplied, evidence and relation must concern this reference, preserve subject, event, time, and qualifications, and must not invent missing facts. Missing evidence does not prove that a fact is absent from the patient's full EHR. Do not give a long chain of thought.

## Input JSON:
'''


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def messages(claim: str, reference: str) -> list[dict[str, str]]:
    """No GT, teacher prediction, review status, or arm is an input argument."""
    if not isinstance(claim, str) or not claim.strip():
        raise ValueError("An unchanged nonempty claim is required")
    if not isinstance(reference, str):
        raise ValueError("The actual reference must be a string")
    payload = json.dumps({"text": claim, "reference": reference}, ensure_ascii=False, indent=4)
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": INSTRUCTIONS + payload},
    ]


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_answer(row: dict[str, Any], arm: str | None = None) -> dict[str, Any]:
    """Validate labels and literal quotation provenance, never adjudicate GT."""
    if row.get("GT") not in LABELS:
        raise ValueError("Unknown physician label")
    answer = row.get("answer")
    if not isinstance(answer, str):
        raise ValueError("answer must be a JSON string")
    if "answer_text" in row and row["answer_text"] != answer:
        raise ValueError("answer and answer_text disagree")

    def unique_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate answer key")
            value[key] = item
        return value

    value = json.loads(answer, object_pairs_hook=unique_keys)
    if not isinstance(value, dict) or value.get("verdict") != row["GT"]:
        raise ValueError("The answer must preserve the original physician verdict")
    if set(value) not in ({"verdict"}, {"evidence", "relation", "verdict"}):
        raise ValueError("Unexpected answer schema")
    is_brief = "relation" in value
    if arm == "label_only" and is_brief:
        raise ValueError("label_only must contain only verdict")
    if arm == "evidence_brief" and not is_brief:
        raise ValueError("evidence_brief requires evidence, relation and verdict")
    if digest(row["reference"]) != row["reference_sha256"]:
        raise ValueError("Reference SHA mismatch")
    if is_brief:
        evidence, relation = value["evidence"], value["relation"]
        if not isinstance(evidence, list) or not all(isinstance(q, str) and q for q in evidence):
            raise ValueError("evidence must contain exact nonempty quotation strings")
        if not isinstance(relation, str) or not relation.strip():
            raise ValueError("relation must be nonempty")
        if not evidence and row["GT"] != "Not Addressed":
            raise ValueError("Only reviewed NA examples may lack a direct positive quotation")
        spans = row.get("metadata", {}).get("evidence_spans", row.get("evidence_spans", []))
        if len(spans) != len(evidence):
            raise ValueError("Each quotation requires its own source span")
        for quote, span in zip(evidence, spans):
            if span.get("reference_sha256", row["reference_sha256"]) != row["reference_sha256"]:
                raise ValueError("Quotation belongs to another reference")
            if span.get("quote", span.get("text", quote)) != quote:
                raise ValueError("Evidence string and span disagree")
            if span.get("quote_sha256", digest(quote)) != digest(quote):
                raise ValueError("Quotation SHA mismatch")
            expected = []
            start = 0
            while True:
                start = row["reference"].find(quote, start)
                if start < 0:
                    break
                expected.append((start, start + len(quote)))
                start += 1
            if "occurrences" in span:
                occurrences = span["occurrences"]
                if not isinstance(occurrences, list) or not occurrences:
                    raise ValueError("Quotation has no source occurrence")
                actual = []
                for occurrence in occurrences:
                    start, end = occurrence.get("start"), occurrence.get("end")
                    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(row["reference"]):
                        raise ValueError("Invalid source span")
                    if row["reference"][start:end] != quote or occurrence.get("quote_sha256", digest(quote)) != digest(quote):
                        raise ValueError("Quotation is not the exact current reference slice")
                    actual.append((start, end))
                if actual != expected or span.get("occurrence_count", len(actual)) != len(actual):
                    raise ValueError("All repeated quote locations must be retained in source order")
            else:
                # Compatibility for old single-span synthetic fixtures, never
                # silently select one location when the quote occurs repeatedly.
                start, end = span.get("start"), span.get("end")
                if type(start) is not int or type(end) is not int or [(start, end)] != expected:
                    raise ValueError("Invalid or unresolved repeated source span")
    return value


def validate_pairs(
    label_rows: list[dict[str, Any]],
    brief_rows: list[dict[str, Any]],
    allowed_patients: set[str],
    excluded_patients: set[str] | None = None,
) -> dict[str, Any]:
    if not label_rows or len(label_rows) != len(brief_rows):
        raise ValueError("Paired data must have the same nonzero N")
    if allowed_patients & (excluded_patients or set()):
        raise ValueError("Training and excluded patient roles overlap")
    seen: set[str] = set()
    for label, brief in zip(label_rows, brief_rows):
        if any(label.get(k) != brief.get(k) for k in PAIR_FIELDS):
            raise ValueError("Pair changes ID, physician GT, claim, source, patient, or reference")
        if label["id"] in seen:
            raise ValueError("Duplicate training ID")
        seen.add(label["id"])
        if str(label["sid"]) not in allowed_patients:
            raise ValueError("A non-training patient entered the training package")
        if str(label["sid"]) in (excluded_patients or set()):
            raise ValueError("An excluded patient entered training")
        parse_answer(label, "label_only")
        parse_answer(brief, "evidence_brief")
        expected_messages = messages(label["claim"], label["reference"])
        if expected_messages != messages(brief["claim"], brief["reference"]):
            raise ValueError("Prompt differs across paired answers")
        for row in (label, brief):
            if "messages" in row and row["messages"] != expected_messages:
                raise ValueError("Stored builder messages differ from the actual training prompt")
    return {
        "N": len(label_rows),
        "patients": len({str(r["sid"]) for r in label_rows}),
        "same_input_and_order": True,
        "original_GT_preserved": True,
        "reference_truncation": False,
        "same_prompt_both_arms": True,
        "quotes_exact_current_reference_slices": True,
    }


def prompt_ids(tok, row: dict[str, Any]) -> list[int]:
    expected_messages = messages(row["claim"], row["reference"])
    if "messages" in row and row["messages"] != expected_messages:
        raise ValueError("Stored builder messages differ from the actual training prompt")
    ids = tok.apply_chat_template(
        expected_messages, tokenize=True,
        add_generation_prompt=True, enable_thinking=False, reasoning_effort="low",
    )
    if not isinstance(ids, list) or not ids:
        raise ValueError("Tokenizer returned an empty or non-list prompt")
    return ids


def encode_lists(tok, row: dict[str, Any]):
    """103-compatible: return full IDs, loss labels, supervised token count."""
    parse_answer(row)
    prefix = prompt_ids(tok, row)
    answer = row["answer"]
    answer_ids = tok.encode(answer, add_special_tokens=False)
    eos = tok.convert_tokens_to_ids("<|im_end|>")
    if not isinstance(eos, int) or eos < 0:
        raise ValueError("The pinned Qwen end-of-message token is unavailable")
    suffix = answer_ids + [eos]
    if tok.decode(answer_ids, skip_special_tokens=False) != answer:
        raise ValueError("Answer tokenization is not lossless")
    ids, labels = prefix + suffix, [-100] * len(prefix) + suffix
    assert len(ids) == len(labels) and labels[:len(prefix)] == [-100] * len(prefix)
    return ids, labels, len(suffix)


def pad_batch(encoded_rows, pad_token_id: int):
    """Right padding is never supervised; useful for CPU checks and future loaders."""
    if not encoded_rows:
        raise ValueError("Cannot pad an empty batch")
    maximum = max(len(item[0]) for item in encoded_rows)
    batch = {"input_ids": [], "attention_mask": [], "labels": []}
    for ids, labels, _ in encoded_rows:
        extra = maximum - len(ids)
        batch["input_ids"].append(ids + [pad_token_id] * extra)
        batch["attention_mask"].append([1] * len(ids) + [0] * extra)
        batch["labels"].append(labels + [-100] * extra)
    return batch


def encoded(tok, row, torch, device="cpu"):
    """103-shaped tensor output; CPU by default, explicit CUDA only in future work."""
    ids, labels, supervised = encode_lists(tok, row)
    batch = {
        "input_ids": torch.tensor([ids], device=device),
        "attention_mask": torch.ones((1, len(ids)), dtype=torch.long, device=device),
        "labels": torch.tensor([labels], device=device),
    }
    return batch, len(ids), supervised


def optimizer_batches(rows, gradient_accumulation: int = 8, start_sample: int = 0):
    """CPU-only batch plan with exact tail accounting and sample-mean scaling.

    Each row is one microbatch, as in 103. Divide each microbatch's mean loss by
    ``loss_divisor``; this keeps equal sample weights when the final optimizer
    batch contains fewer than eight rows. No GPU, optimizer, or training runs.
    """
    if type(gradient_accumulation) is not int or gradient_accumulation < 1:
        raise ValueError("gradient_accumulation must be a positive integer")
    if type(start_sample) is not int or not 0 <= start_sample <= len(rows):
        raise ValueError("start_sample must be an exact consumed-row offset")
    if start_sample != len(rows) and start_sample % gradient_accumulation:
        raise ValueError("Resume only after a complete optimizer batch, not halfway through accumulation")
    for start in range(start_sample, len(rows), gradient_accumulation):
        end = min(start + gradient_accumulation, len(rows))
        micro_rows = rows[start:end]
        yield {
            "optimizer_step": start // gradient_accumulation + 1,
            "start_sample": start, "end_sample": end,
            "micro_rows": micro_rows, "microbatch_count": len(micro_rows),
            "loss_divisor": len(micro_rows), "is_final_batch": end == len(rows),
        }


def checkpoint_due(batch: dict[str, Any], sample_interval: int = 256) -> bool:
    """Save at a crossed interval or the real final batch, including short tails."""
    if type(sample_interval) is not int or sample_interval < 1:
        raise ValueError("sample_interval must be a positive integer")
    return bool(batch["is_final_batch"] or batch["end_sample"] // sample_interval > batch["start_sample"] // sample_interval)
