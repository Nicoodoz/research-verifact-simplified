"""Validate execution-reader anchors and save complete, traceable reading packets."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import argparse
import json
import re
import common as c
from build_stages import seal


def materialize(output_dir=None):
    review=c.OUT/"run_001/review_001"
    packs={x["row"]["case_id"]:x for x in c.pilot.jsonl(review/"case_packets.jsonl")}
    notes=c.read_json(c.TASK/"semantic_notes.json")
    assert {x["case_id"] for x in notes["cases"]}==set(packs)
    corpus=c.pilot.jsonl(c.OUT/"preparation_001/corpus.jsonl")
    anchors=[]
    rendered=[]
    for note in notes["cases"]:
        cid=note["case_id"]
        p=packs[cid]
        row=p["row"]
        for anchor in note["anchors"]:
            a=dict(anchor,case_id=cid)
            if a["kind"]=="ehr":
                matches=[x for x in corpus if x["subject_id"]==row["subject_id"] and x["note_id"]==a["note_id"] and x["start"]==a["passage_start"]]
                assert len(matches)==1,(cid,a)
                passage=matches[0]
                text=passage["text"]
                pid=passage["passage_id"]
                equivalents={x["passage_id"] for x in corpus if x["subject_id"]==row["subject_id"] and
                    (x["date"],x["category"],x["text"])==(passage["date"],passage["category"],passage["text"])}
                a.update(passage_id=pid,note_sha256=passage["note_sha256"],
                    candidate_membership={arm:pid in p["candidate"]["candidate_ids"][arm] for arm in c.METHODS},
                    selected_membership={arm:pid in p["evidence"]["retrieval"][arm]["selected_ids"] for arm in c.METHODS},
                    shared_rerank_score=p["evidence"]["scores"].get(pid))
                a["literal_equivalent_ids"]=sorted(equivalents)
                a["candidate_literal_equivalent_membership"]={arm:bool(equivalents&set(p["candidate"]["candidate_ids"][arm])) for arm in c.METHODS}
                a["selected_literal_equivalent_membership"]={arm:bool(equivalents&set(p["evidence"]["retrieval"][arm]["selected_ids"])) for arm in c.METHODS}
                a["selection_disposition"]={arm:{key:("selected" if key in p["evidence"]["retrieval"][arm]["selected_ids"] else
                    next((s["reason"] for s in p["evidence"]["retrieval"][arm]["selection_skips"] if s["passage_id"]==key),"not_in_candidate_pool")) for key in sorted(equivalents)} for arm in c.METHODS}
                direct=p["candidate"]["query_rankings"][0]
                a["direct_query_ranks"]={kind:next((i for i,x in enumerate(direct[kind],1) if (x[0] if kind!="hybrid" else x)==pid),None) for kind in ("bm25","dense","hybrid")}
            elif a["kind"]=="judge":
                output=p["outputs"][a["method"]]
                text=output["output_text"]
                a["request_id"]=output["request_id"]
            elif a["kind"]=="planner":
                text=p["planner"]["output_text"]
            elif a["kind"]=="source":
                text=p["original"]["source"]["local"]
            elif a["kind"]=="claim":
                text=p["original"]["text"]
            else:
                raise ValueError("Unknown anchor kind")
            assert a["quote"] and a["quote"] in text,(cid,a)
            a["text_sha256"]=c.pilot.digest_text(text)
            a["positions"]=[[m.start(),m.end()] for m in re.finditer(re.escape(a["quote"]),text)]
            anchors.append(a)
        parts=[f"# {cid}：执行者阅读记录",f"原医生 GT：{row['human_gt']}；direct={row['direct']}；simple={row['simple']}；planner={row['planner']}。", 
            "选例依据："+"、".join(p["selection_reasons"]),"直接观察："+note["observation"],"可能解释："+note["interpretation"],"仍不确定："+note["uncertainty"],
            "这是执行者诊断，不是医生新增标签或独立审计结论。","## 原 claim",p["original"]["text"],"## 未核验的来源上下文",p["original"]["source"]["local"],
            "## 完整 planner 输出",f"状态：{p['planner']['status']}；错误：{p['planner']['error']}","```json\n"+p["planner"]["output_text"]+"\n```","## 三臂实际 EHR（相同片段只展示一次）"]
        for pid,span in sorted(p["passages"].items(),key=lambda kv:(kv[1]["date"],kv[1]["time"],kv[1]["note_id"],kv[1]["start"])):
            membership={arm:p["evidence"]["retrieval"][arm]["selected_ids"].index(pid)+1 for arm in c.METHODS if pid in p["evidence"]["retrieval"][arm]["selected_ids"]}
            parts.extend([f"### Note {span['note_id']} / {span['date']} {span['time']} / [{span['start']},{span['end_exclusive']})",str(membership),"```text\n"+span["text"]+"\n```"])
        for arm in c.METHODS:
            parts.extend(["## 完整 Judge："+arm,"body SHA："+p["evidence"]["retrieval"][arm]["body_sha256"],"```json\n"+p["outputs"][arm]["output_text"]+"\n```"])
        rendered.append((cid,"\n\n".join(parts)+"\n"))
    out=Path(output_dir) if output_dir else review/"semantic_003"
    assert out.resolve().is_relative_to(c.OUT.resolve()),"Review output must stay inside 008"
    out.mkdir(parents=True,exist_ok=False)
    (out/"cases").mkdir()
    for cid,text in rendered:
        (out/"cases"/(cid+".md")).write_text(text,encoding="utf-8")
    c.pilot.write_json(out/"notes_snapshot.json",notes)
    c.pilot.write_json(out/"evidence_anchors.json",anchors)
    coverage=dict(cases=len(packs),unique_full_judge_outputs=len({v["request_id"] for p in packs.values() for v in p["outputs"].values()}),
        full_planner_outputs=len(packs),selected_ehr_blocks_summed_over_cases=sum(len(p["passages"]) for p in packs.values()),
        unique_selected_passages=len({pid for p in packs.values() for pid in p["passages"]}),anchors=len(anchors),
        tags=dict(Counter(tag for n in notes["cases"] for tag in n.get("tags",[]))),not_population_failure_rates=True)
    c.pilot.write_json(out/"coverage.json",coverage)
    c.pilot.write_json(out/"manifest.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),
        dependencies={p.relative_to(c.ROOT).as_posix():c.pilot.digest_file(p) for p in [review/"manifest.json",c.TASK/"semantic_notes.json"]},
        code_sha256={Path(__file__).relative_to(c.ROOT).as_posix():c.pilot.digest_file(Path(__file__))},
        files={p.relative_to(out).as_posix():c.pilot.digest_file(p) for p in out.rglob("*") if p.is_file()}))
    print(c.pilot.canonical(coverage))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    materialize(args.output)
