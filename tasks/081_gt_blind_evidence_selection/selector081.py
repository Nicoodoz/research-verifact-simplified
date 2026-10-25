"""Shared U/T selector prompts and parsers; no data or GT file access."""
from __future__ import annotations

import json

MODEL = "qwen3.8-27b"
PLAN_SYSTEM = (
    "Plan verification of one complete clinical proposition using only the patient's supplied C48 evidence. "
    "Decompose material conditions including event completion, time, negation, certainty, number, attribution, and scope. "
    "A clinician_label field may optionally be present. If present, you may use it to prioritize which requirements "
    "need direct support, contradiction, or boundary checking; if absent, stay label-blind. "
    "Do not invent medical facts or treat the proposition as evidence. "
    "Return JSON only: requirements (1-6 nonempty strings) and goal (one short string)."
)
COMPOSE_SYSTEM = (
    "Select original EHR passages from the complete frozen C48 candidate list for judging the entire proposition. "
    "A clinician_label field may optionally be present. If present, use it only to prioritize diagnostic passages; "
    "if absent, stay label-blind. Do not omit a material contradiction, qualifier, or competing event merely to force a label. "
    "For Supported, check all material requirements. For Not Supported, preserve evidence addressing the claim but "
    "showing contradiction, partial support, wrong time/scope, plan instead of completion, or unsupported precision. "
    "For Not Addressed, select the closest relevant context without treating absence as contradiction. "
    "Select 1-16 distinct Cxx IDs from the supplied candidates, with at most two from any note, aiming for an "
    "8000-character displayed evidence body. The formatter will enforce the exact same budget and preserve original text. "
    "Return JSON only: selected (ID array in priority order), why (short), unresolved (array of short strings). "
    "Never paraphrase or generate evidence text. Your explanation will not be shown to the final verifier."
)


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def plan_body(claim, label=None):
    payload = {"proposition": claim}
    if label is not None:
        payload["clinician_label"] = label
    return {"model": MODEL, "messages": [{"role": "system", "content": PLAN_SYSTEM},
                                  {"role": "user", "content": compact(payload)}],
            "temperature": 0, "max_tokens": 700, "enable_thinking": False,
            "response_format": {"type": "json_object"}}


def candidate_line(short_id, passage):
    return (f"{short_id} | Date {passage.get('date')} | Time {passage.get('time')} | "
            f"{passage.get('category')} | Note {passage.get('note_id')} | Text: {passage.get('text', '')}")


def compose_body(claim, requirements, candidate_lines, label=None):
    payload = {"proposition": claim, "requirements": requirements, "candidates": candidate_lines}
    if label is not None:
        payload["clinician_label"] = label
    return {"model": MODEL, "messages": [{"role": "system", "content": COMPOSE_SYSTEM},
                                  {"role": "user", "content": compact(payload)}],
            "temperature": 0, "max_tokens": 1000, "enable_thinking": False,
            "response_format": {"type": "json_object"}}


def unpack_answer(transport):
    if transport.get("http_status") != 200:
        return None, None, None
    raw = json.loads(transport["body_text"])
    assert raw.get("model") == MODEL
    content = raw["choices"][0]["message"]["content"]
    obj = json.loads(content)
    assert isinstance(obj, dict)
    return obj, raw.get("usage") or {}, content


def parse_plan(transport):
    result = {"status": "invalid", "requirements": [], "goal": None, "errors": []}
    try:
        obj, usage, content = unpack_answer(transport)
        assert obj is not None
        req = obj.get("requirements")
        assert isinstance(req, list) and 1 <= len(req) <= 6 and all(isinstance(x, str) and x.strip() for x in req)
        assert isinstance(obj.get("goal"), str)
        result.update(status="valid", requirements=req, goal=obj["goal"], usage=usage, output_text=content)
    except (AssertionError, KeyError, TypeError, ValueError, IndexError) as exc:
        result["errors"].append(type(exc).__name__ + ":" + str(exc)[:120])
    return result


def parse_compose(transport, allowed):
    result = {"status": "invalid", "selected": [], "why": None, "unresolved": [], "errors": []}
    try:
        obj, usage, content = unpack_answer(transport)
        assert obj is not None
        selected = obj.get("selected")
        assert isinstance(selected, list) and 1 <= len(selected) <= 16
        assert all(isinstance(x, str) and x in allowed for x in selected)
        assert len(selected) == len(set(selected))
        assert isinstance(obj.get("why"), str)
        assert isinstance(obj.get("unresolved"), list) and all(isinstance(x, str) for x in obj["unresolved"])
        result.update(status="valid", selected=selected, why=obj["why"],
                      unresolved=obj["unresolved"], usage=usage, output_text=content)
    except (AssertionError, KeyError, TypeError, ValueError, IndexError) as exc:
        result["errors"].append(type(exc).__name__ + ":" + str(exc)[:120])
    return result
