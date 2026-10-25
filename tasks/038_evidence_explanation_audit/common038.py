"""038 shared utilities: post-hoc evidence / explanation consistency audit."""
from __future__ import annotations
import csv, hashlib, json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "038_evidence_explanation_audit"
CAP = 60.0
LABELS = ("Supported", "Not Supported", "Not Addressed")
AUDIT_LABELS = LABELS + ("Uncertain",)

sys.path.insert(0, str(ROOT / "tasks" / "024_lambda2_transfer_validation"))
import common024 as a24
from transport_direct024 import DirectClient

MODELS = dict(deepseek=a24.MODELS["deepseek"], qwen=a24.MODELS["qwen"])
PRICES = a24.PRICES
Config, load_config = a24.Config, a24.load_config
canonical = a24.canonical
file_hash = a24.file_hash
now = a24.now

def require(x, msg):
    if not x:
        raise ValueError(msg)

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return [json.loads(line) for line in f if line.strip()]

def csvread(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def put(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n"); f.flush(); os.fsync(f.fileno())

def csvwrite(path, rows):
    require(rows, "empty csv")
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def stable_hash(prefix, value):
    return hashlib.sha256((prefix + str(value)).encode()).hexdigest()

def clean_json_content(text):
    require(isinstance(text, str) and text.strip(), "empty content")
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        lo, hi = t.find("{"), t.rfind("}")
        require(lo >= 0 and hi > lo, "no json object")
        return json.loads(t[lo:hi+1])

def entries(reference):
    starts = list(re.finditer(r"(?m)^(\d+)\. Date:", reference))
    out = {}
    for i, m in enumerate(starts):
        end = starts[i+1].start() if i+1 < len(starts) else len(reference)
        out[int(m.group(1))] = reference[m.start():end]
    return out

def quote_found(quote, text):
    if not isinstance(quote, str) or not quote.strip(): return False
    pattern = r"\s+".join(re.escape(s) for s in quote.split())
    return re.search(pattern, text) is not None

EVIDENCE_SYSTEM = """You audit one clinical proposition against the supplied patient reference.
You do not know any gold label or downstream model prediction. The reference is the only patient evidence.
Use these meanings:
Supported: every material part of the proposition is supported by the supplied reference.
Not Supported: the reference addresses the claim but contradicts it, or supports only part of the complete proposition.
Not Addressed: the material claimed fact is not addressed by the reference.
Uncertain: the evidence relationship cannot be determined reliably.

Decompose the proposition into only its material requirements. For each requirement, use relation supported, contradicted, unaddressed, or uncertain.
For supported or contradicted relations, cite at least one existing integer reference_id and a short exact contiguous quote from that reference entry.
Do not demand verbatim wording when the same fact is clearly established, but do not invent patient facts, silently weaken qualifiers, dates, scope, certainty, or relationships.
A missing fact is unaddressed, not contradicted. A possibility does not prove certainty. Partial support for a multi-part proposition is Not Supported.
Return JSON only with keys audit_label, coverage, requirements, summary.
coverage must be complete, partial, or uncertain. Each requirement has claim_quote, requirement, relation, evidence; evidence is a list of {reference_id, quote}.
Use at most 6 requirements and concise prose."""

REASON_SYSTEM = """You audit whether an existing explanation is semantically compatible with a supplied final label.
Do not assess whether the final label is medically correct and do not use external knowledge.
Return JSON only with keys alignment and note.
alignment must be one of consistent, contradictory, mixed_or_ambiguous.
consistent: the explanation argues for or is compatible with the final label.
contradictory: it explicitly argues a different label, says required support is absent, or otherwise conflicts with the final label.
mixed_or_ambiguous: the explanation contains mixed signals or is too incomplete to decide.
Keep note under 60 words."""

def evidence_body(proposition, reference, model):
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": EVIDENCE_SYSTEM},
            {"role": "user", "content": json.dumps({"proposition": proposition, "reference": reference}, ensure_ascii=False)},
        ],
        "temperature": 0,
        "max_tokens": 1800,
        "enable_thinking": False,
        "response_format": {"type": "json_object"},
    }

def reason_body(final_label, original_verdict, reason, checks, model):
    payload = {"final_label": final_label, "original_verdict": original_verdict,
               "reason": reason, "checks": checks}
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": REASON_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0,
        "max_tokens": 500,
        "enable_thinking": False,
        "response_format": {"type": "json_object"},
    }

def model_key(model):
    for key, value in MODELS.items():
        if value == model: return key
    raise ValueError("unknown model " + model)

def bound(job):
    ip, op = PRICES[job["model_key"]]
    body = canonical(job["body"])
    return ((len(body.encode("utf-8")) + 2000) * ip + job["body"]["max_tokens"] * op) / 1e6

def charge(job, transport):
    try:
        raw = json.loads(transport["body_text"])
        u = raw["usage"]; i = int(u["prompt_tokens"]); o = int(u["completion_tokens"])
        ip, op = PRICES[job["model_key"]]
        return (i * ip + o * op) / 1e6, "peak_no_cache_usage_estimate"
    except Exception:
        return bound(job), "unknown_usage_reservation"

def outer_content(transport):
    require(transport.get("http_status") == 200, "no http200")
    raw = json.loads(transport["body_text"])
    choice = raw["choices"][0]
    return choice["message"]["content"], raw.get("model"), raw.get("usage", {})

def parse_evidence(job, transport):
    out = dict(status="invalid", audit_label=None, coverage=None, trace_supported=False,
               citation_valid=False, requirements=[], errors=[])
    try:
        content, returned, usage = outer_content(transport)
        obj = clean_json_content(content)
        label, coverage = obj.get("audit_label"), obj.get("coverage")
        require(label in AUDIT_LABELS, "bad audit_label")
        require(coverage in ("complete", "partial", "uncertain"), "bad coverage")
        reqs = obj.get("requirements")
        require(isinstance(reqs, list) and 1 <= len(reqs) <= 6, "bad requirements")
        payload = json.loads(job["body"]["messages"][1]["content"])
        refmap = entries(payload["reference"]); checked = []; all_valid = True
        for row in reqs:
            require(isinstance(row, dict), "bad requirement row")
            relation = row.get("relation")
            require(relation in ("supported", "contradicted", "unaddressed", "uncertain"), "bad relation")
            evs = row.get("evidence", []); require(isinstance(evs, list), "bad evidence")
            cev = []
            for ev in evs:
                require(isinstance(ev, dict) and type(ev.get("reference_id")) is int, "bad evidence object")
                rid, quote = ev["reference_id"], ev.get("quote", "")
                valid = rid in refmap and quote_found(quote, refmap[rid])
                cev.append(dict(reference_id=rid, quote=quote, valid=bool(valid)))
                all_valid = all_valid and valid
            if relation in ("supported", "contradicted") and not cev: all_valid = False
            checked.append(dict(claim_quote=row.get("claim_quote"), requirement=row.get("requirement"),
                                relation=relation, evidence=cev))
        trace = label == "Supported" and coverage == "complete" and all(r["relation"] == "supported" for r in checked) and all_valid
        out.update(status="valid", audit_label=label, coverage=coverage, requirements=checked,
                   summary=obj.get("summary"), trace_supported=bool(trace), citation_valid=bool(all_valid),
                   model_returned=returned, usage=usage, output_text=content)
    except Exception as exc:
        out["errors"].append(type(exc).__name__ + ":" + str(exc)[:180])
    return out

def parse_reason(job, transport):
    out = dict(status="invalid", alignment=None, note=None, errors=[])
    try:
        content, returned, usage = outer_content(transport)
        obj = clean_json_content(content)
        alignment = obj.get("alignment")
        require(alignment in ("consistent", "contradictory", "mixed_or_ambiguous"), "bad alignment")
        out.update(status="valid", alignment=alignment, note=obj.get("note"),
                   model_returned=returned, usage=usage, output_text=content)
    except Exception as exc:
        out["errors"].append(type(exc).__name__ + ":" + str(exc)[:180])
    return out

def parse_job(job, transport):
    return parse_evidence(job, transport) if job["kind"] == "evidence" else parse_reason(job, transport)

def transport_client(model):
    cfg = load_config(ROOT / ".env.aliyun")
    return DirectClient(Config(cfg.api_key, cfg.base_url, model), timeout=180)
