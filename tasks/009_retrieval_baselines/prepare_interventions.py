"""Freeze literal evidence interventions with matched-block and repeat controls."""
from pathlib import Path
import re
import study009 as s


def reference(ids,pp,admission):
    ordered=sorted(ids,key=lambda k:(pp[k]["date"],pp[k]["time"],pp[k]["note_id"],pp[k]["start"]))
    lines=[s.core.display_line(i,pp[k]) for i,k in enumerate(ordered,1)]
    body_chars=sum(len(line)+1 for line in lines)
    header=f"Hospital Admission Start: {admission['ADMITTIME']}\nHospital Admission End: {admission['DISCHTIME']}\nElectronic Health Record Context\nOrdered by Time (Earliest to Latest):\n"
    return dict(selected_ids=ordered,reference=header+("\n".join(lines) or "No Electronic Health Record Context Found."),body_characters=body_chars)


def prepare():
    specs=s.read_json(s.TASK/"intervention_specs.json")
    jobs,assignments,records,cache={},[],[],{}
    previews=[]
    for spec in specs["cases"]:
        folder=s.OUT/spec["folder"]
        s.check(folder/"analysis_001")
        inputs=s.pilot.jsonl(folder/"judge_preparation/inputs.jsonl")
        item=next(x for x in inputs if x["case_id"]==spec["case_id"])
        corpus=s.pilot.jsonl(folder/"preparation/corpus.jsonl")
        pp={p["passage_id"]:p for p in corpus if p["subject_id"]==item["subject_id"]}
        prompts=s.read_json(folder/"preparation/judge_prompts.json")
        normalized={x["request_id"]:x for x in s.pilot.jsonl(folder/"analysis_001/normalized_responses.jsonl")}
        cohort=s.pilot.read_csv(folder/"preparation/cohort.csv")[1]
        gt=next(r["human_gt"] for r in cohort if r["proposition_id"]==item["proposition_id"])
        local_cache={}
        for row in inputs:
            for arm,r in row["retrieval"].items():
                if r.get("status")=="ready":
                    local_cache[r["body_sha256"]]=dict(folder=spec["folder"],request_id=r["request_id"],result=normalized[r["request_id"]])
        keys=[next(k for k,p in pp.items() if p["note_id"]==nid and p["start"]==start) for nid,start in spec["keys"]]
        receiver=item["retrieval"][spec["receiver"]]
        donor=item["retrieval"][spec["donor"]]
        assert set(keys)<=set(donor["selected_ids"]) and not set(keys)&set(receiver["selected_ids"])
        avoid=re.compile(spec["avoid"],re.I)
        banned=set(receiver["selected_ids"]+donor["selected_ids"])
        controls=[]
        remove_controls=[]
        removal_control_missing=False
        for key in keys:
            pool=[k for k,p in pp.items() if k not in banned and not avoid.search(p["text"]) and len(p["text"].strip())>=100]
            assert pool,"No usable matched-size control"
            control=min(pool,key=lambda k:(abs(len(pp[k]["text"])-len(pp[key]["text"])),s.pilot.digest_text("009/control/v1:"+k)))
            controls.append(control)
            banned.add(control)
            removable=[k for k in donor["selected_ids"] if k not in keys+remove_controls and not avoid.search(pp[k]["text"])]
            if removable:
                remove_controls.append(min(removable,key=lambda k:(abs(len(pp[k]["text"])-len(pp[key]["text"])),s.pilot.digest_text("009/removal-control/v1:"+k))))
            else:
                removal_control_missing=True
        kept=list(receiver["selected_ids"])
        removed=[]
        weakest=[k for k in reversed(receiver["relevance_order"]) if k not in keys]
        while any(reference(kept+addition,pp,item["admission"])["body_characters"]>8000 or len(kept+addition)>16 for addition in (keys,controls)):
            key=weakest[len(removed)]
            kept.remove(key)
            removed.append(key)
        variants={"receiver_repeat":receiver["selected_ids"],"receiver_plus_key":kept+keys,"receiver_plus_control":kept+controls,
            "donor_repeat":donor["selected_ids"],"donor_minus_key":[k for k in donor["selected_ids"] if k not in keys],
            "donor_minus_control":[k for k in donor["selected_ids"] if k not in remove_controls]}
        if removal_control_missing:
            variants.pop("donor_minus_control")
        variant_data={}
        for variant,ids in variants.items():
            r=reference(ids,pp,item["admission"])
            assert r["body_characters"]<=8000 and len(r["selected_ids"])<=16
            body=s.prior_stages.judge_body(item,r["reference"],prompts)
            sha=s.pilot.fingerprint(body)
            repeat=variant.endswith("repeat")
            if repeat:
                expected=receiver if variant=="receiver_repeat" else donor
                assert sha==expected["body_sha256"]
            source="new"
            if not repeat and sha in local_cache:
                source="cached_primary"
                rid=local_cache[sha]["request_id"]
                cache[sha]=local_cache[sha]
            else:
                rid=("diag_repeat:"+spec["case_id"]+":"+variant) if repeat else "diag:"+sha
                jobs[rid]=dict(request_id=rid,kind="chat",body=body)
            assignments.append(dict(case_id=spec["case_id"],folder=spec["folder"],proposition_id=item["proposition_id"],variant=variant,request_id=rid,body_sha256=sha,source=source))
            variant_data[variant]=dict(r,body_sha256=sha,request_id=rid,source=source)
        records.append(dict(spec=spec,proposition_id=item["proposition_id"],subject_id=item["subject_id"],author_type=item["author_type"],gt=gt,claim=item["text"],keys=keys,
            recipient_replaced_ids=removed,addition_control_ids=controls,donor_removal_control_ids=remove_controls,variants=variant_data,
            donor_removal_control_missing=removal_control_missing,
            original_receiver_verdict=normalized[receiver["request_id"]]["verdict"],original_donor_verdict=normalized[donor["request_id"]]["verdict"],
            evidence={k:pp[k] for k in set(keys+controls+remove_controls+removed)}))
        previews.append(f"## {spec['case_id']} / {spec['interpretation']}\n\n原claim：{item['text']}\n")
        for title,ids in (("关键段",keys),("增加的对照段",controls),("供体移除对照段",remove_controls),("接收方共同替换的段",removed)):
            for key in ids:
                p=pp[key]
                previews.append(f"### {title}：Note {p['note_id']} / {p['date']} / [{p['start']},{p['end_exclusive']})\n\n```text\n{p['text']}\n```\n")
    ordered=sorted(jobs.values(),key=lambda j:s.pilot.digest_text("009/diagnostic-order/v1:"+j["request_id"]))
    out=s.OUT/"interventions_001/preparation"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"jobs.jsonl",ordered)
    s.pilot.write_csv(out/"assignments.csv",assignments)
    s.pilot.write_json(out/"cases.json",records)
    s.pilot.write_json(out/"cache_bindings.json",cache)
    (out/"control_review.md").write_text("\n".join(previews),encoding="utf-8")
    summary=dict(cases=len(records),logical_conditions=len(assignments),new_calls=len(ordered),cached_conditions=sum(x["source"]!="new" for x in assignments),
        expected_peak_cny=sum((sum(len(m["content"]) for m in j["body"]["messages"])*.4*3+350*9)/1e6 for j in ordered),
        budget_stage="diagnostics",cap_cny=5,primary_metrics_unchanged=True,posthoc_diagnostic_not_deployable_performance=True)
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[s.TASK/"intervention_specs.json",s.OUT/"development_001/analysis_001/manifest.json",s.OUT/"confirmation_001/analysis_001/manifest.json"],
        [Path(__file__),s.TASK/"study009.py"])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    prepare()
