"""GT-blind R1 response parser. Envelope paths must be frozen from A/B preflight."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

LABELS = ("Supported", "Not Supported", "Not Addressed")
THINK = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)


def path_get(obj: Any, path: list[str | int] | None) -> Any:
    if path is None:
        return None
    value = obj
    for key in path:
        value = value[key]
    return value


@dataclass(frozen=True)
class ParserProfile:
    content_path: list[str | int]
    finish_path: list[str | int] | None = None
    usage_path: list[str | int] | None = None
    reasoning_path: list[str | int] | None = None
    truncation_values: tuple[str, ...] = ("length", "max_tokens", "max_new_tokens", "truncated")

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> "ParserProfile":
        if obj.get("status") != "FROZEN_AFTER_AB_NO_GT":
            raise ValueError("Parser profile has not been frozen after A/B without GT")
        return cls(content_path=obj["content_path"], finish_path=obj.get("finish_path"),
                   usage_path=obj.get("usage_path"), reasoning_path=obj.get("reasoning_path"),
                   truncation_values=tuple(obj.get("truncation_values", cls.truncation_values)))


def split_thinking(text: str) -> tuple[str | None, str, bool]:
    matches = list(THINK.finditer(text))
    if matches:
        reasoning = "\n".join(m.group(1) for m in matches)
        final = THINK.sub("", text).strip()
        return reasoning, final, False
    if re.search(r"<think>", text, re.IGNORECASE):
        return None, text, True  # unclosed thinking: do not guess a final answer
    return None, text.strip(), False


def json_candidates(text: str) -> list[dict[str, Any]]:
    """Find balanced objects even amid prose/fences; do not infer labels from prose."""
    found = []
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "verdict" in value:
            found.append(value)
    return found


def parse(raw: bytes | str | dict[str, Any], profile: ParserProfile) -> dict[str, Any]:
    result: dict[str, Any] = {"valid": False, "invalid_reason": None, "reasoning": None,
        "final_text": None, "verdict": None, "label_scores": None, "reason": None,
        "checks": None, "finish": None, "usage": None, "truncated": None}
    try:
        envelope = json.loads(raw) if isinstance(raw, (bytes, str)) else raw
        content = path_get(envelope, profile.content_path)
        finish = path_get(envelope, profile.finish_path)
        usage = path_get(envelope, profile.usage_path)
        separate_reasoning = path_get(envelope, profile.reasoning_path)
        if not isinstance(content, str):
            raise ValueError("content_not_string")
        result["finish"] = finish
        result["usage"] = usage
        result["truncated"] = (str(finish).lower() in profile.truncation_values) if finish is not None else None
        reasoning, final, unclosed = split_thinking(content)
        result["reasoning"] = separate_reasoning if isinstance(separate_reasoning, str) else reasoning
        result["final_text"] = final
        if unclosed:
            raise ValueError("unclosed_thinking")
        if result["truncated"]:
            raise ValueError("generation_truncated")
        candidates = json_candidates(final)
        if len(candidates) != 1:
            raise ValueError("zero_or_multiple_verdict_objects")
        obj = candidates[0]
        verdict = obj.get("verdict")
        if verdict not in LABELS:
            raise ValueError("invalid_verdict")
        result["verdict"] = verdict
        scores = obj.get("label_scores")
        if isinstance(scores, dict) and set(scores) == set(LABELS) and all(
            type(scores[k]) is int and 0 <= scores[k] <= 100 for k in LABELS
        ) and sum(scores.values()) == 100:
            result["label_scores"] = {k: scores[k] for k in LABELS}
        result["reason"] = obj.get("reason") if isinstance(obj.get("reason"), str) else None
        result["checks"] = obj.get("checks") if isinstance(obj.get("checks"), list) else None
        result["valid"] = True  # raw verdict is primary; scores/checks may be absent
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        result["invalid_reason"] = str(exc)
    return result
