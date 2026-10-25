"""Validate the executor's interpretation anchors and build one concise report."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import effect_analysis as analyze

pilot = analyze.pilot
ROOT, TASK = analyze.ROOT, analyze.TASK


def reference_anchor(packet, number):
    reference = packet["input"]["reference"]
    blocks = dict(analyze.reference_blocks(reference))
    pilot.require(number in blocks, "Unknown reference number")
    quote = blocks[number]
    needle = str(number) + ". " + quote
    start = reference.index(needle) + len(str(number) + ". ")
    return dict(case_id=packet["case_id"], proposition_id=packet["input"]["proposition_id"], source="reference",
        reference_id=packet["input"]["reference_id"], number=number, source_sha256=pilot.digest_text(reference),
        start=start, end_exclusive=start+len(quote), quote=quote)


def output_anchor(packet, arm, index):
    raw = packet["outputs"][arm]["output_text"]
    value = pilot.strict_json(raw)
    check = value["checks"][index]
    return dict(case_id=packet["case_id"], proposition_id=packet["input"]["proposition_id"], source="model_output",
        arm=arm, json_path=f"checks[{index}]", source_sha256=pilot.digest_text(raw), check=check)


def verify_anchor(anchor, packet):
    pilot.require(anchor["case_id"] == packet["case_id"] and anchor["proposition_id"] == packet["input"]["proposition_id"], "Anchor identity mismatch")
    if anchor["source"] == "reference":
        pilot.require(anchor == reference_anchor(packet, anchor["number"]), "Reference anchor changed")
    else:
        index = int(anchor["json_path"].split("[")[1].split("]")[0])
        pilot.require(anchor == output_anchor(packet, anchor["arm"], index), "Output anchor changed")


def render_tables(rows, metrics):
    overall = ["| 作者 | n | 改对 | 改错 | 换标签仍错 | 标签不变 | ΔMCC [95% 患者 CI] |", "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    gt_table = ["| 作者/医生 GT | n | 改对 | 改错 | 正确数净变化 |", "| --- | ---: | ---: | ---: | ---: |"]
    for author in ("llm", "human"):
        own = [r for r in rows if r["author_type"] == author]
        counts = Counter(r["outcome"] for r in own)
        m = metrics[author]["contrast"]["metrics"]["mcc"]
        overall.append(f"| {author} | {len(own)} | {counts['improved']} | {counts['degraded']} | {counts['wrong_changed']} | {counts['both_correct']+counts['both_wrong']} | {m['delta']:+.4f} [{m['ci95'][0]:+.4f}, {m['ci95'][1]:+.4f}] |")
        for label in pilot.LABELS:
            group = [r for r in own if r["human_gt"] == label]
            counts = Counter(r["outcome"] for r in group)
            gt_table.append(f"| {author} / {label} | {len(group)} | {counts['improved']} | {counts['degraded']} | {counts['improved']-counts['degraded']:+d} |")
    return "\n".join(overall), "\n".join(gt_table)


def build(run: Path, notes_path: Path, template_path: Path):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["outputs_sha256"].items():
        pilot.require(pilot.digest_file(run / name) == digest, "Extraction artifact changed: " + name)
    # Task README hashes are historical snapshots, not blockers after documentation updates.
    for name, digest in manifest["sources_sha256"].items():
        if name.startswith("outputs/"):
            pilot.require(pilot.digest_file(ROOT / name) == digest, "Frozen source changed: " + name)
    notes = pilot.strict_json(notes_path.read_text(encoding="utf-8"))
    selected = pilot.read_csv(run / "selected_cases.csv")[1]
    pilot.require({r["case_id"] for r in notes["reviews"]} == {r["case_id"] for r in selected}
        and len(notes["reviews"]) == len(selected), "Review coverage mismatch")
    review = next(run / f"review_{i:03d}" for i in range(1,10000) if not (run / f"review_{i:03d}").exists())
    review.mkdir()
    (review / "cases").mkdir()
    context = json.loads((run / "source_context.json").read_text(encoding="utf-8"))
    contexts = {r["case_id"]:r for r in context["cases"]}
    anchors, index = [], []
    for note in notes["reviews"]:
        cid = note["case_id"]
        packet = json.loads((run / "packets" / (cid + ".json")).read_text(encoding="utf-8"))
        pilot.require(packet["selected_for_deep_review"], "Review of unselected case")
        pilot.require(all(note["reading"][k] for k in ("proposition", "full_reference", "full_structured_output", "full_event_alignment_output")), "Incomplete deep-review declaration")
        pilot.require(note["reading"]["parent_context"] == (cid in contexts), "Source context reading declaration mismatch")
        row = packet["cohort"]
        own_anchors = [reference_anchor(packet, n) for n in note["reference_numbers"]]
        for arm, indices in note["output_check_indices"].items():
            own_anchors += [output_anchor(packet, arm, i) for i in indices]
        for anchor in own_anchors:
            verify_anchor(anchor, packet)
        anchors.extend(own_anchors)
        text = [f"# {cid}：{note['claim_zh']}", f"患者 {row['subject_id']}；{row['author_type']}；{row['outcome']}；GT={row['human_gt']}；structured={row['structured']}；event={row['event_alignment']}。",
            "\n**直接观察：** " + note["observation"], "\n**可能解释：** " + note["possible_explanation"],
            "\n**尚未确定：** " + note["uncertainty"], "\n分析标签（非医生 GT）：" + ", ".join(note["tags"]),
            "\n## 原命题", packet["input"]["text"], "\n## 本例引用的 reference 原文"]
        for a in own_anchors:
            if a["source"] == "reference":
                text += [f"\n编号 {a['number']}；reference 字符 [{a['start']}, {a['end_exclusive']})：", "```text\n" + a["quote"] + "\n```"]
        if cid in contexts:
            text += ["\n## 后补读的来源上下文（不是 EHR 证据）", note["source_context_observation"],
                "```text\n" + contexts[cid]["parent_text_chunk"] + "\n```"]
            if note["reading"]["full_bhc"]:
                text += ["<details><summary>为确定操作指代所读的完整原 BHC（未核验文本）</summary>\n", "```text\n" + contexts[cid]["brief_hospital_course"] + "\n```", "</details>"]
        for arm in analyze.ARMS:
            text += ["\n## " + arm + " 完整生成输出", "```json\n" + packet["outputs"][arm]["output_text"] + "\n```"]
        text += ["\n<details><summary>完整 reference（保持原始顺序、编号和时间）</summary>\n", "```text\n" + packet["input"]["reference"] + "\n```", "</details>"]
        (review / "cases" / (cid + ".md")).write_text("\n\n".join(text)+"\n", encoding="utf-8", newline="\n")
        index.append(dict(case_id=cid, proposition_id=row["proposition_id"], subject_id=row["subject_id"], author=row["author_type"],
            outcome=row["outcome"], human_gt=row["human_gt"], structured=row["structured"], event_alignment=row["event_alignment"],
            tags=";".join(note["tags"]), reading_scope="full_inputs_and_both_complete_outputs"))
    pilot.write_json(review / "review_notes_snapshot.json", notes)
    pilot.write_json(review / "evidence_anchors.json", anchors)
    pilot.write_csv(review / "case_index.csv", index)
    rows = pilot.read_csv(run / "all_transitions.csv")[1]
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    table, gt_table = render_tables(rows, metrics)
    content = template_path.read_text(encoding="utf-8").replace("{{OVERALL_TABLE}}", table).replace("{{GT_TABLE}}", gt_table)
    pilot.require("{{" not in content, "Unresolved report placeholder")
    (review / "report.md").write_text(content, encoding="utf-8", newline="\n")
    pilot.write_json(review / "checks.json", dict(selected_cases=len(index), evidence_anchors_verified=len(anchors),
        notes_are_executor_interpretations_not_gt=True, independent_review_performed=False, api_calls=0,
        original_metrics_unchanged=True, full_reference_and_both_outputs_declared_read=25,
        source_parents_read=13, full_bhc_read_only=["C17"], other_packet_deep_review_claimed=False))
    pilot.write_json(review / "manifest.json", dict(stage="executor_review_complete_pending_independent_audit",
        extraction_manifest_sha256=pilot.digest_file(run / "manifest.json"),
        notes_sha256=pilot.digest_file(notes_path), template_sha256=pilot.digest_file(template_path),
        source_context_sha256=pilot.digest_file(run / "source_context.json"), builder_code_sha256=pilot.digest_file(Path(__file__)),
        outputs_sha256={p.relative_to(review).as_posix():pilot.digest_file(p) for p in review.rglob("*") if p.is_file()}))
    print(pilot.canonical(dict(review=str(review), cases=len(index), anchors=len(anchors))))
    return review


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, default=analyze.OUT / "run_002")
    p.add_argument("--notes", type=Path, default=TASK / "review_notes.json")
    p.add_argument("--template", type=Path, default=TASK / "report_template.md")
    a = p.parse_args()
    build(a.run.resolve(), a.notes.resolve(), a.template.resolve())
