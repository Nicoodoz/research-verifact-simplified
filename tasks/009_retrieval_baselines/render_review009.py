"""Validate source anchors, trace every retrieval gate, and save full review packets."""
from collections import Counter
from pathlib import Path
import argparse
import re
import study009 as s


def render(folder,notes_file,output):
    packets={p["row"]["case_id"]:p for p in s.pilot.jsonl(folder/"review_001/packets.jsonl")}
    notes=s.read_json(notes_file)
    assert {x["case_id"] for x in notes["cases"]}==set(packets)
    corpus=s.pilot.jsonl(folder/"preparation/corpus.jsonl")
    pp={p["passage_id"]:p for p in corpus}
    anchors,texts=[],[]
    for note in notes["cases"]:
        cid=note["case_id"]
        pack=packets[cid]
        item=pack["input"]
        extras={}
        for original in note["anchors"]:
            a=dict(original,case_id=cid)
            if a["kind"]=="ehr":
                matches=[p for p in corpus if p["subject_id"]==item["subject_id"] and p["note_id"]==a["note_id"] and p["start"]==a["start"]]
                assert len(matches)==1,(cid,a)
                p=matches[0]
                key=p["passage_id"]
                text=p["text"]
                eq={q["passage_id"] for q in corpus if q["subject_id"]==p["subject_id"] and (q["date"],q["category"],q["text"])==(p["date"],p["category"],p["text"])}
                ranks=item["rankings"]
                a.update(passage_id=key,note_sha256=p["note_sha256"],date=p["date"],time=p["time"],
                    actual_shared_reranker_saw_exact_id=key in item["scores"],shared_rerank_score=item["scores"].get(key),
                    route_rank_positions={route:next((i for i,v in enumerate(ranks[route],1) if (v if route=="hybrid" else v[0])==key),None) for route in ("bm25","dense","hybrid")},
                    literal_equivalents=sorted(eq),branch_gates={})
                for method in ("A48","B48","C48"):
                    r=item["retrieval"][method]
                    pool=set(r.get("candidate_ids",[]))
                    selected=set(r.get("selected_ids",[]))
                    ranked=sorted(pool,key=lambda k:(-item["scores"][k],k))
                    a["branch_gates"][method]=dict(candidate_eligible=bool(eq&pool),selected=bool(eq&selected),
                        exact_rerank_position=ranked.index(key)+1 if key in ranked else None,
                        disposition={k:"selected" if k in selected else next((z["reason"] for z in r.get("selection_skips",[]) if z["passage_id"]==k),"outside_branch_candidates") for k in sorted(eq)})
                if key not in pack["passages"]:
                    extras[key]=p
            elif a["kind"]=="judge":
                text=pack["outputs"][a["method"]]["output_text"]
                a["request_id"]=pack["outputs"][a["method"]]["request_id"]
            else:
                raise ValueError("Unknown anchor kind")
            assert a["quote"] and a["quote"] in text,(cid,a)
            a["text_sha256"]=s.pilot.digest_text(text)
            a["positions"]=[[m.start(),m.end()] for m in re.finditer(re.escape(a["quote"]),text)]
            anchors.append(a)
        row=pack["row"]
        parts=[f"# {cid}：执行者阅读记录",f"GT={row['human_gt']}；A48={row['A48']}；B48={row['B48']}；C48={row['C48']}。",
            "选例："+"；".join(pack["reasons"]),"直接观察："+note["observation"],"可能解释："+note["interpretation"],"仍不确定："+note["uncertainty"],
            "这不是新医生GT或独立审计结论。", "## 原claim",item["text"],"## 实际EHR（共享片段只展示一次）"]
        for key,p in sorted(pack["passages"].items(),key=lambda kv:(kv[1]["date"],kv[1]["time"],kv[1]["note_id"],kv[1]["start"])):
            members={a:item["retrieval"][a]["selected_ids"].index(key)+1 for a in ("A48","B48","C48") if key in item["retrieval"][a].get("selected_ids",[])}
            parts.extend([f"### Note {p['note_id']} / {p['date']} {p['time']} / [{p['start']},{p['end_exclusive']})",str(members),"```text\n"+p["text"]+"\n```"])
        if extras:
            parts.append("## 另作索引追溯的原文（未自动加入以上Judge输入）")
            for p in extras.values():
                parts.extend([f"Note {p['note_id']} / {p['date']} / [{p['start']},{p['end_exclusive']})","```text\n"+p["text"]+"\n```"])
        for method in ("A48","B48","C48"):
            parts.extend(["## 完整Judge："+method,"```json\n"+str(pack["outputs"][method].get("output_text"))+"\n```"])
        texts.append((cid,"\n\n".join(parts)+"\n"))
    output.mkdir(parents=True,exist_ok=False)
    (output/"cases").mkdir()
    for cid,text in texts:
        (output/"cases"/(cid+".md")).write_text(text,encoding="utf-8")
    s.pilot.write_json(output/"notes_snapshot.json",notes)
    s.pilot.write_json(output/"anchors.json",anchors)
    summary=dict(cases=len(packets),anchors=len(anchors),distinct_full_Judge_outputs=len({r.get("request_id") for p in packets.values() for r in p["outputs"].values() if r}),
        per_case_unique_ehr_blocks=sum(len(p["passages"]) for p in packets.values()),unique_ehr_blocks=len({k for p in packets.values() for k in p["passages"]}),
        diagnostic_not_new_gold=True,all_anchor_quotes_validated=True)
    s.pilot.write_json(output/"summary.json",summary)
    s.seal(output,[folder/"review_001/manifest.json",notes_file],[Path(__file__)])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    p.add_argument("notes",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    folder=args.folder.resolve()
    render(folder,args.notes.resolve(),args.output.resolve() if args.output else folder/"review_001/semantic_001")
