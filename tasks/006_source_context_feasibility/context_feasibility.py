"""Deterministic, offline preparation for the source-context feasibility pilot."""
from __future__ import annotations

from collections import Counter
import itertools
import json
from pathlib import Path
import re
import sys

import duckdb
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/"outputs/006_source_context_feasibility"
RAW=ROOT/"data/00_raw/verifact-bhc/1.1.0"
FORMAL=ROOT/"outputs/002_reproduce_paper_results/run_003"
sys.path.insert(0,str(ROOT/"tasks/004_event_alignment_pilot"))
import pilot
import siliconflow as sf

ARMS=("structured","source_context","repeat_claim")
SEED="006_source_context_feasibility/selection/v1:"
ORDER_SEED="006_source_context_feasibility/order/v1:"
ROLE_POLICY="""The user data may also contain unverified_source_text from the document being checked, or repeated wording of the proposition. This text is NOT patient-record evidence. Verify only the proposition as written against the numbered EHR reference. You may use source wording to understand terms or referents, but do not turn extra source assertions into new verification requirements or silently replace an explicit date, dose, quantity, negation or certainty in the proposition. If resolving a referent requires assuming a more specific event, time, dose or scope than the proposition establishes, state that limitation in your existing checks/reason. Do not assume the source statement is true. Cite only existing EHR reference numbers as evidence. Do not use the source text or the proposition to prove itself. Keep the same output schema and word allowance."""


def fresh(prefix):
    OUT.mkdir(parents=True,exist_ok=True)
    p=next(OUT/f"{prefix}_{i:03d}" for i in range(1,10000) if not (OUT/f"{prefix}_{i:03d}").exists())
    p.mkdir()
    return p


def select(rows,patients):
    selected=[]
    for sid in patients:
        for author in ("llm","human"):
            group=sorted((r for r in rows if r["subject_id"]==sid and r["author_type"]==author),
                key=lambda r:pilot.digest_text(SEED+r["proposition_id"]))
            picked=[]
            for label in ("Not Supported","Not Addressed"):
                picked.extend([r for r in group if r["human_gt"]==label][:5])
            picked.extend([r for r in group if r["human_gt"]=="Supported"][:16-len(picked)])
            used={r["proposition_id"] for r in picked}
            picked.extend([r for r in group if r["proposition_id"] not in used][:16-len(picked)])
            pilot.require(len(picked)==16,"Insufficient planned stratum; do not substitute patients")
            selected.extend(picked)
    return sorted(selected,key=lambda r:int(r["human_csv_order"]))


def source_window(prop,prefix_chars=240):
    parent,bhc=prop["parent_text_chunk"],prop["brief_hospital_course"]
    matches=[m.start() for m in re.finditer(re.escape(parent),bhc)] if parent else []
    pilot.require(len(matches)==1,"Parent must have exactly one literal BHC location")
    pstart=matches[0]
    start,end=max(0,pstart-prefix_chars),pstart+len(parent)
    text=bhc[start:end]
    pilot.require(len(text)<=1200,"Source context exceeds registered limit")
    return dict(text=text,start=start,end_exclusive=end,parent_start=pstart,parent_end_exclusive=end,
        prefix_left_boundary_truncated=start>0,context_sha256=pilot.digest_text(text),bhc_sha256=pilot.digest_text(bhc))


def context_flags(claim,context):
    numbers=lambda text:set(re.findall(r"\b\d+(?:\.\d+)?\b",text))
    return dict(additional_number_strings=sorted(numbers(context)-numbers(claim)),
        visible_deidentification=bool(re.search(r"\[\*\*|\bMonth\s+\d+",context)),
        potential_event_reference=bool(re.search(r"\b(the|this|that)\s+(procedure|operation|treatment|dose|condition|course)|\b(it|this|these|those)\b",claim,re.I)),
        context_not_proven_semantically_equivalent=True)


def repeated_claim(claim,target_length):
    n=max(1,int(target_length/(len(claim)+1)+.5))
    return "\n".join([claim]*n)


def messages(item,arm,prompts):
    pilot.require(arm in ARMS,"Unknown arm")
    auxiliary=item["source_context"]["text"] if arm=="source_context" else repeated_claim(item["text"],len(item["source_context"]["text"])) if arm=="repeat_claim" else ""
    return [dict(role="system",content=prompts["common"]+"\n"+prompts["structured"]+"\n"+ROLE_POLICY),
        dict(role="user",content=pilot.canonical(dict(proposition=item["text"],reference=item["reference"],unverified_source_text=auxiliary)))]


def prepare():
    split_path=ROOT/"outputs/003_error_analysis/patient_groups.json"
    split=json.loads(split_path.read_text(encoding="utf-8"))
    order=sorted(split["groups"]["development"],key=lambda sid:pilot.digest_text(split["seed"]+sid))
    pilot.require(order[:6]==["93147","29426","85689","91315","45979","98790"],"Unexpected prior cohort")
    patients=order[6:8]
    pilot.require(patients==["45115","89909"],"Development order changed")
    master=FORMAL/"cohort_master.csv"
    fm=json.loads((FORMAL/"manifest.json").read_text(encoding="utf-8"))
    pilot.require(pilot.digest_file(master)==fm["output_sha256"]["cohort_master.csv"],"002 cohort changed")
    all_rows=pilot.subset_csv(master,"subject_id",set(patients))
    universe=[r for r in all_rows if r["proposition_type"]=="claim" and r["invalid"]=="False"]
    cohort=select(universe,patients)
    ids={r["proposition_id"] for r in cohort}
    paths=["propositions/propositions.csv.gz","verifact/verdicts.parquet","verifact/reference_payloads.parquet","verifact/rater_configurations.csv"]
    before={name:pilot.digest_file(RAW/name) for name in paths}
    pilot.require(all(before[k]==fm["input_sha256"][k] for k in paths),"Raw source differs from 002")
    configs=[r for r in pilot.read_csv(RAW/paths[3])[1] if r["rater_alias"]=="v1.1.0-rater-121"]
    expected=dict(model="R1-70B",fact_type="sentence",top_n="100",retrieval_method="rerank",reference_format="absolute_time",reference_only_admission="True",deduplicate_text="True")
    pilot.require(len(configs)==1 and all(configs[0][k]==v for k,v in expected.items()),"Unexpected reference source")
    props={r["proposition_id"]:r for r in pilot.subset_csv(RAW/paths[0],"proposition_id",ids)}
    with duckdb.connect(config={"threads":2,"memory_limit":"2GB"}) as con:
        con.register("selected",pd.DataFrame({"proposition_id":sorted(ids)}))
        links=con.execute("SELECT v.proposition_id,v.reference_id FROM read_parquet(?) v JOIN selected USING(proposition_id) WHERE v.rater_alias=?",[str(RAW/paths[1]),"v1.1.0-rater-121"]).fetchall()
        pilot.require(len(links)==len(ids)==len(dict(links)),"Reference coverage incomplete")
        refids={rid for pid,rid in links}
        con.register("refs",pd.DataFrame({"reference_id":sorted(refids)}))
        payloads=dict(con.execute("SELECT r.reference_id,r.reference FROM read_parquet(?) r JOIN refs USING(reference_id)",[str(RAW/paths[2])]).fetchall())
    pilot.require(set(payloads)==refids,"Missing reference payload")
    refs=dict(links)
    inputs=[]
    for row in cohort:
        pid=row["proposition_id"]
        prop=props[pid]
        pilot.require(pilot.integer_id(prop["subject_id"])==row["subject_id"] and pilot.integer_id(prop["hadm_id"])==row["hadm_id"],"Source identity mismatch")
        context=source_window(prop)
        ref=payloads[refs[pid]]
        pilot.require(pilot.digest_text(ref)==refs[pid],"Reference text hash mismatch")
        inputs.append(dict(proposition_id=pid,subject_id=row["subject_id"],hadm_id=row["hadm_id"],author_type=row["author_type"],
            text=prop["text"],reference_id=refs[pid],reference=ref,source_context=context,
            context_flags=context_flags(prop["text"],context["text"])))
    prompts={name:(ROOT/"tasks/004_event_alignment_pilot/prompts"/(name+".md")).read_text(encoding="utf-8") for name in ("common","structured")}
    jobs=[]
    permutations=list(itertools.permutations(ARMS))
    for i,item in enumerate(sorted(inputs,key=lambda x:pilot.digest_text(ORDER_SEED+x["proposition_id"]))):
        for arm in permutations[i%len(permutations)]:
            body=dict(model=sf.MODEL,messages=messages(item,arm,prompts),temperature=0,max_tokens=2048,enable_thinking=False,n=1,stream=False,response_format=sf.response_schema())
            byte_screen=len(pilot.canonical(body).encode("utf-8"))+1000
            bound=(byte_screen*3+2048*9)/1e6
            jobs.append(dict(request_id=arm+":"+item["proposition_id"],body=body,max_cost_cny=bound))
    prep=fresh("preparation")
    pilot.write_csv(prep/"cohort.csv",cohort)
    pilot.write_csv(prep/"candidate_universe.csv",universe)
    pilot.write_csv(prep/"not_selected.csv",[r for r in universe if r["proposition_id"] not in ids])
    pilot.write_csv(prep/"excluded_invalid.csv",[r for r in all_rows if r["proposition_type"]=="claim" and r["invalid"]=="True"],fields=list(all_rows[0]))
    pilot.write_jsonl(prep/"inputs.jsonl",inputs)
    pilot.write_jsonl(prep/"requests.jsonl",jobs)
    pilot.write_json(prep/"prompts.json",dict(prompts,role_policy=ROLE_POLICY))
    pilot.write_csv(prep/"input_scope_flags.csv",[dict(proposition_id=x["proposition_id"],author=x["author_type"],
        **{k:pilot.canonical(v) for k,v in x["context_flags"].items()},context_characters=len(x["source_context"]["text"])) for x in inputs])
    # Heuristic estimate only; original 004 token/character ratio is reported as a scenario.
    old_inputs={r["proposition_id"]:r for r in pilot.jsonl(ROOT/"outputs/004_event_alignment_pilot/run_003/inputs.jsonl")}
    old=pilot.jsonl(ROOT/"outputs/004_event_alignment_pilot/run_003/analysis/normalized_responses.jsonl")
    old_structured=[r for r in old if r["arm"]=="structured"]
    old_chars=sum(len(old_inputs[r["proposition_id"]]["reference"])+len(old_inputs[r["proposition_id"]]["text"]) for r in old_structured)
    token_ratio=sum(r["usage"]["input_tokens"] for r in old_structured)/old_chars
    estimates={a:sum((sum(len(m["content"]) for m in j["body"]["messages"])*token_ratio*3+350*9)/1e6 for j in jobs if j["request_id"].startswith(a+":")) for a in ARMS}
    summary=dict(stage="offline_prepared_awaiting_budget_approval",patients=patients,candidate_claims=len(universe),selected_claims=len(cohort),
        planned_requests=len(jobs),by_author={a:dict(Counter(r["human_gt"] for r in cohort if r["author_type"]==a)) for a in ("llm","human")},
        expected_peak_cny_scenario=sum(estimates.values()),expected_by_arm=estimates,planning_ratio_from_004=token_ratio,
        whole_schedule_reservation_screen_cny=sum(j["max_cost_cny"] for j in jobs),
        max_request_input_byte_screen=max(len(pilot.canonical(j["body"]).encode("utf-8"))+1000 for j in jobs),
        proposed_total_cap_cny=8,exact_tokenizer_available=False,price_settlement_verified=False,api_calls=0,
        gt_meaning="Agreement with original independent-proposition clinician labels; not contextual clinical accuracy",
        model_version="Provider alias only; no immutable weight revision")
    pilot.write_json(prep/"summary.json",summary)
    pilot.require(before=={name:pilot.digest_file(RAW/name) for name in paths},"Source changed during preparation")
    code=[Path(__file__),ROOT/"tasks/004_event_alignment_pilot/siliconflow.py",ROOT/"src/verifact_research/inference/siliconflow_pool.py",*sorted((ROOT/"src/verifact_research/evaluation").glob("*.py"))]
    pilot.write_json(prep/"manifest.json",dict(stage=summary["stage"],raw_sha256=before,patient_split_sha256=pilot.digest_file(split_path),
        selection_seed=SEED,code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in code},
        output_sha256={p.relative_to(prep).as_posix():pilot.digest_file(p) for p in prep.iterdir() if p.is_file()}))
    print(pilot.canonical(dict(preparation=str(prep),**summary)))
    return prep


if __name__=="__main__":
    prepare()
