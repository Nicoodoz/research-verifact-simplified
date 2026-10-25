"""Render one Chinese main report and traceable executor case notes for 007."""
import argparse
import json
from pathlib import Path
import re
import prepare as p
from retrieval import ARMS


def ref_anchor(cid,stage,arm,item,number):
    result=item["retrieval"][arm]
    text=result["reference"]
    matches=list(re.finditer(r"(?m)^(\d+)\. Date: ",text))
    assert 1<=number<=len(matches)
    start=matches[number-1].start()
    end=matches[number].start() if number<len(matches) else len(text)
    pid=result["reference_passage_ids"][number-1]
    passage=next(x for x in result["passages"] if x["passage_id"]==pid)
    return dict(case_id=cid,stage=stage,arm=arm,source="ehr_reference",number=number,
        source_sha256=p.pilot.digest_text(text),start=start,end_exclusive=end,quote=text[start:end],
        note_id=passage["note_id"],raw_start=passage["start"],raw_end_exclusive=passage["end_exclusive"],
        note_sha256=passage["note_sha256"],passage_id=pid)


def render(output):
    run=p.OUT/"run_001"
    review=run/"review_001"
    notes_path=p.TASK/"semantic_notes.json"
    notes=json.loads(notes_path.read_text(encoding="utf-8"))
    supp={r["proposition_id"]:r for r in p.pilot.jsonl(p.OUT/"zero_budget_sensitivity_001/inputs.jsonl")}
    supp_answers={(r["proposition_id"],r["arm"]):r for r in p.pilot.jsonl(p.OUT/"zero_budget_sensitivity_001/normalized_responses.jsonl")}
    selected=json.loads((review/"summary.json").read_text(encoding="utf-8"))["selected_cases"]
    assert sorted(n["case_id"] for n in notes["cases"] if n["stage"]=="main")==sorted(selected)
    assert sorted(n["case_id"] for n in notes["cases"] if n["stage"]=="sensitivity")==["R031","R078","R083"]
    output.mkdir(parents=True,exist_ok=False)
    (output/"cases").mkdir()
    anchors=[]
    output_count=0
    for note in notes["cases"]:
        cid,stage=note["case_id"],note["stage"]
        packet=json.loads((review/"packets"/(cid+".json")).read_text(encoding="utf-8"))
        pid=packet["case"]["proposition_id"]
        item=packet["input"] if stage=="main" else supp[pid]
        answers=packet["responses"] if stage=="main" else {a:supp_answers[(pid,a)] for a in ARMS}
        lines=[f"# {cid}｜{stage}｜执行者分析，不是新 GT",item["text"],"原医生标签："+packet["case"]["human_gt"],
            "直接观察："+note["observation"],"可能解释："+note["explanation"],"尚不确定："+note["uncertainty"],
            "## 实际检索查询（未发送给最终 Judge）", "```json\n"+json.dumps(item["queries"],ensure_ascii=False,indent=2)+"\n```",
            "## 本例关键 EHR 原文"]
        for arm,numbers in note["refs"].items():
            for number in numbers:
                anchor=ref_anchor(cid,stage,arm,item,number)
                anchors.append(anchor)
                lines.append(f"{arm} reference {number}；note {anchor['note_id']} 原字符 [{anchor['raw_start']},{anchor['raw_end_exclusive']})\n\n```text\n{anchor['quote']}\n```")
        if note.get("release_refs"):
            text=packet["released_reference"]["reference"]
            matches=list(re.finditer(r"(?m)^(\d+)\. Date: ",text))
            lines.append("## 发布 reference 对照（不是本轮模型输入）")
            for number in note["release_refs"]:
                start=matches[number-1].start()
                end=matches[number].start() if number<len(matches) else len(text)
                anchor=dict(case_id=cid,stage=stage,source="released_reference",number=number,source_sha256=p.pilot.digest_text(text),
                    start=start,end_exclusive=end,quote=text[start:end])
                anchors.append(anchor)
                lines.append(f"release reference {number}\n\n```text\n{anchor['quote']}\n```")
        lines.append("## 全部已收到输出（原文）")
        for arm,response in answers.items():
            if response is None:
                continue
            text=response["output_text"]
            output_count+=1
            anchors.append(dict(case_id=cid,stage=stage,arm=arm,source="full_output",source_sha256=p.pilot.digest_text(text),start=0,end_exclusive=len(text),quote=text))
            lines += [f"<details><summary>{arm}：{response['verdict']}</summary>\n", "```json\n"+text+"\n```", "</details>"]
        lines.append("主试验完整输入及发布 reference 见 [冻结病例包](../../packets/"+cid+".json)。补充输入另见 zero_budget_sensitivity_001。")
        (output/"cases"/(cid+"_"+stage+".md")).write_text("\n\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    assert output_count==88
    p.pilot.write_json(output/"notes_snapshot.json",notes)
    p.pilot.write_json(output/"evidence_anchors.json",anchors)
    (output/"report.md").write_bytes((p.TASK/"report.md").read_bytes())
    p.pilot.write_json(output/"manifest.json",dict(stage="executor_analysis_complete_pending_independent_review",cases=len(notes["cases"]),
        main_cases=len(selected),sensitivity_cases=3,full_outputs_read=output_count,anchors=len(anchors),
        main_reference_union_passages_read=265,additional_or_extended_sensitivity_passages_read=24,
        original_release_full_reference_read_cases=["R075","R095"],independent_audit_performed=False,
        notes_sha256=p.pilot.digest_file(notes_path),code_sha256=p.pilot.digest_file(Path(__file__)),
        output_sha256={x.relative_to(output).as_posix():p.pilot.digest_file(x) for x in output.rglob("*") if x.is_file()}))
    print(p.pilot.canonical(dict(output=str(output),cases=len(notes["cases"]),anchors=len(anchors),full_outputs=output_count)))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=p.OUT/"run_001/review_001/semantic_001")
    a=parser.parse_args()
    render(a.output)
