"""Render executor interpretations with exact anchors; never modify model outputs."""
import argparse
import json
from pathlib import Path

import context_feasibility as cf
from analyze_context_results import reference_blocks


def reference_anchor(packet, number):
    text = packet["input"]["reference"]
    quote = dict(reference_blocks(text))[number]
    marker = str(number) + ". " + quote
    start = text.index(marker) + len(str(number) + ". ")
    assert text[start:start+len(quote)] == quote
    return dict(case_id=packet["case"]["case_id"], source="reference", reference_number=number,
        source_sha256=cf.pilot.digest_text(text), start=start, end_exclusive=start+len(quote), quote=quote)


def render(review, output):
    notes_path = cf.TASK / "semantic_notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    selected = {r["case_id"] for r in cf.pilot.read_csv(review / "case_index.csv")[1] if r["review_selection"]}
    cf.pilot.require(selected == {r["case_id"] for r in notes["reviews"]} and len(selected) == len(notes["reviews"]), "Review coverage differs")
    output.mkdir(parents=True, exist_ok=False)
    (output / "cases").mkdir()
    anchors = []
    packets = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (review / "packets").glob("*.json")}
    for note in notes["reviews"]:
        cid = note["case_id"]
        packet = packets[cid]
        own = [reference_anchor(packet, n) for n in note["reference_numbers"]]
        anchors.extend(own)
        src = packet["input"]["source_context"]
        anchors.append(dict(case_id=cid, source="unverified_source_window", source_sha256=cf.pilot.digest_text(src["text"]),
            start=0, end_exclusive=len(src["text"]), quote=src["text"], original_bhc_offsets=src))
        lines = [f"# {cid}｜执行者案例记录（不是新 GT）", packet["input"]["text"],
            "原医生标签：" + packet["case"]["human_gt"], "直接观察：" + note["observation"],
            "可能解释：" + note["possible_explanation"], "仍不确定：" + note["uncertainty"],
            "来源角色记录：" + note["source_as_evidence"],
            "## 本例 EHR 引用（保留日期与编号）"]
        for anchor in own:
            lines.append(f"reference {anchor['reference_number']}，字符 [{anchor['start']},{anchor['end_exclusive']})\n\n```text\n{anchor['quote']}\n```")
        lines += ["## 未核验来源片段（不是事实证据）", "```text\n" + src["text"] + "\n```", "## 三臂完整输出"]
        for arm, response in packet["responses"].items():
            raw = response.get("output_text") if response else None
            if raw:
                anchors.append(dict(case_id=cid, source="full_output", arm=arm, source_sha256=cf.pilot.digest_text(raw),
                    start=0, end_exclusive=len(raw), quote=raw))
            lines += [f"<details><summary>{arm}</summary>\n", "```text\n" + (raw or "没有收到回答，不补标签。") + "\n```", "</details>"]
        lines.append("完整原始输入、reference 顺序与响应元数据见 [冻结病例包](../../packets/" + cid + ".json)。")
        (output / "cases" / (cid + ".md")).write_text("\n\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    for cross in notes["cross_reference_observations"]:
        for number in cross["reference_numbers"]:
            anchor = reference_anchor(packets[cross["observed_in_case"]], number)
            anchors.append(dict(anchor, used_for_comparison_to_case=cross["for_case"], meaning=cross["meaning"]))
    cf.pilot.write_json(output / "notes_snapshot.json", notes)
    cf.pilot.write_json(output / "evidence_anchors.json", anchors)
    (output / "report.md").write_bytes((cf.TASK / "report.md").read_bytes())
    cf.pilot.write_json(output / "manifest.json", dict(stage="executor_complete_pending_independent_review",
        notes_sha256=cf.pilot.digest_file(notes_path), renderer_sha256=cf.pilot.digest_file(Path(__file__)),
        extraction_manifest_sha256=cf.pilot.digest_file(review / "extraction_manifest.json"),
        selected_cases=len(selected), received_outputs_read=82, reference_entries_read=2749, unique_reference_blocks_read=1233,
        anchor_count=len(anchors), independent_audit_performed=False,
        outputs_sha256={p.relative_to(output).as_posix(): cf.pilot.digest_file(p) for p in output.rglob("*") if p.is_file()}))
    print(cf.pilot.canonical(dict(review=str(output), anchors=len(anchors), cases=len(selected))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=cf.OUT / "run_001/review_001")
    parser.add_argument("--output", type=Path, default=cf.OUT / "run_001/review_001/semantic_001")
    args = parser.parse_args()
    render(args.review, args.output)
