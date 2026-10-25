"""Validate quoted rationale arguments and materialize fixed coarse/fine features."""
from __future__ import annotations

import json
from collections import Counter

import inventory083 as base
import run083 as runner

OUT = base.OUT
STANCE = ("supports", "opposes", "uncertain")
BASIS = ("explicit_record", "paraphrase", "inference", "explicit_wording_required",
         "contradiction", "absence", "irrelevant", "other")
DIMENSION = ("event_status", "time", "negation", "certainty", "number",
             "attribution", "scope", "other")
PAIRS = (("explicit_wording_required", "scope"), ("absence", "event_status"),
         ("absence", "time"), ("absence", "certainty"),
         ("contradiction", "negation"), ("contradiction", "event_status"),
         ("explicit_record", "time"), ("explicit_record", "event_status"),
         ("paraphrase", "time"), ("inference", "certainty"))
COARSE_NAMES = ("support_count", "oppose_count", "uncertain_count", "grounded_count",
                "grounded_fraction", "grounded_quote_chars", "evidence_id_count",
                "reason_chars", "cleaned_chars", "checks_count", "structure_missing",
                "reason_missing", "checks_missing")
FINE_NAMES = tuple("basis:" + z for z in BASIS) + tuple("dimension:" + z for z in DIMENSION) + tuple(
    "pair:" + a + "/" + b for a, b in PAIRS)


def features(arguments, claimed, row, cleaned, malformed):
    count = Counter(x["stance"] for x in arguments)
    evidence_ids = []
    checks = row.get("checks")
    if isinstance(checks, list):
        for x in checks:
            if isinstance(x, dict) and x.get("aspect") in ("relevant_evidence", "supporting_case", "opposing_case"):
                if isinstance(x.get("evidence_ids"), list):
                    evidence_ids.extend(str(z) for z in x["evidence_ids"])
    coarse = [count["supports"], count["opposes"], count["uncertain"], len(arguments),
              len(arguments) / max(1, claimed), sum(len(x["quote"]) for x in arguments),
              len(set(evidence_ids)), len(row.get("reason") or ""),
              cleaned["cleaned_chars"], len(checks) if isinstance(checks, list) else 0,
              int(malformed or claimed == 0), int(not row.get("reason")), int(not checks)]
    bcount = Counter(x["basis"] for x in arguments)
    dcount = Counter(x["dimension"] for x in arguments)
    pcount = Counter((x["basis"], x["dimension"]) for x in arguments)
    fine = [bcount[x] for x in BASIS] + [dcount[x] for x in DIMENSION] + [pcount[x] for x in PAIRS]
    assert len(coarse) == len(COARSE_NAMES) and len(fine) == len(FINE_NAMES)
    return coarse, fine


def main():
    cleaned = base.lines("outputs/083_native_rationale_information/cleaned_inputs.jsonl")
    originals = {(x["phase"], x["arm"], x["id"]): x for x in base.lines(
        "outputs/083_native_rationale_information/native_texts.jsonl")}
    attempts, answers = runner.state()
    jobs = runner.jobs()
    assert len(answers) == len(jobs)
    by_sha = {x["cleaned_sha256"]: answers[x["request_id"]] for x in jobs}
    output, failure = [], Counter()
    for c in cleaned:
        if c["arm"] != "F4":
            continue
        key = (c["phase"], c["arm"], c["id"])
        original = originals[key]
        answer = by_sha[c["cleaned_sha256"]]
        transport = answer["transport"]
        assert transport["http_status"] == 200
        response = json.loads(transport["body_text"])
        assert response["model"] == runner.MODEL
        message = response["choices"][0]["message"]
        malformed = False
        try:
            payload = json.loads(message.get("content") or "")
            claimed = payload["arguments"]
            assert isinstance(claimed, list) and len(claimed) <= 6
        except (ValueError, KeyError, AssertionError, TypeError):
            claimed, malformed = [], True
            failure["invalid_json_or_schema"] += 1
        accepted, rejected = [], []
        for item in claimed:
            why = None
            if not isinstance(item, dict):
                why = "not_object"
            elif set(item) != {"stance", "basis", "dimension", "quote"}:
                why = "wrong_keys"
            elif item["stance"] not in STANCE or item["basis"] not in BASIS or item["dimension"] not in DIMENSION:
                why = "invalid_enum"
            elif not isinstance(item["quote"], str) or not item["quote"] or item["quote"] not in c["cleaned_text"]:
                why = "quote_not_exact_substring"
            if why:
                rejected.append({"reason": why, "raw": item})
                failure[why] += 1
            else:
                accepted.append(item)
        coarse, fine = features(accepted, len(claimed), original, c, malformed)
        output.append({"phase": c["phase"], "id": c["id"], "sid": c["sid"],
                       "cleaned_sha256": c["cleaned_sha256"],
                       "extraction_request_id": answer["job"]["request_id"],
                       "extraction_receipt_source": answer["attempt"]["receipt_source"],
                       "model": runner.MODEL, "malformed": malformed,
                       "claimed_count": len(claimed), "accepted": accepted, "rejected": rejected,
                       "coarse": coarse, "fine": fine})
    assert len(output) == 1015
    base.write("structured_arguments.jsonl", output)
    base.write("extraction_quality.json", {
        "n": len(output), "attempts": len(attempts), "failures": dict(failure),
        "coarse_names": COARSE_NAMES, "fine_names": FINE_NAMES,
        "by_phase": {phase: {"n": sum(x["phase"] == phase for x in output),
                             "any_accepted": sum(x["phase"] == phase and bool(x["accepted"]) for x in output),
                             "accepted_arguments": sum(len(x["accepted"]) for x in output if x["phase"] == phase),
                             "rejected_arguments": sum(len(x["rejected"]) for x in output if x["phase"] == phase)}
                     for phase in ("train", "old352", "new180", "repeat")},
        "evaluation_GT_read": False,
        "jobs_sha256": base.digest((OUT / "extraction_jobs.jsonl").read_bytes()),
        "parser_code_sha256": base.digest(__import__("pathlib").Path(__file__).read_bytes()),
    })
    print(json.dumps({"records": len(output), "failures": dict(failure),
                      "phase": {phase: sum(x["phase"] == phase and bool(x["accepted"]) for x in output)
                                for phase in ("train", "old352", "new180", "repeat")}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
