"""Validate literal anchors for eleven actually read cases; no medical relabeling."""
import csv
import common019 as c

def check():
    folder=c.OUT/'boundary_cases_001'
    index=c.read(folder/'index.json'); notes=c.read(folder/'reading_notes.json')
    inputs={r['proposition_id']:r for r in c.jsonlines(c.OUT/'selection/preparation/inputs.jsonl')}
    norm={r['request_id']:r for r in c.jsonlines(c.OUT/'selection/analysis_001/normalized.jsonl')}
    with (c.OUT/'selection/preparation/assignments.csv').open(encoding='utf-8-sig',newline='') as f:
        assignments=list(csv.DictReader(f))
    answers={(r['proposition_id'],r['arm']):norm[r['request_id']] for r in assignments}
    lookup={r['case_id']:r for r in index}
    c.require(set(lookup)=={r['case_id'] for r in notes},'Read cases not fully documented')
    checks=[];patients=set();characters=0
    for note in notes:
        row=lookup[note['case_id']];pid=row['proposition_id'];inp=inputs[pid]
        c.require(c.file_hash(c.OUT/row['file'])==row['sha256'],'Case packet changed')
        patients.add(inp['subject_id']);characters+=len(inp['reference'])
        sources=dict(claim=inp['text'],reference=inp['reference'],B=answers[(pid,'B')]['output_text'],S=answers[(pid,'S')]['output_text'])
        for anchor in note['anchors']:
            text=sources[anchor['source']];offset=text.find(anchor['quote'])
            c.require(offset>=0,'Missing literal anchor: '+note['case_id']+' / '+anchor['quote'])
            checks.append(dict(case_id=note['case_id'],source=anchor['source'],quote=anchor['quote'],
                start=offset,end_exclusive=offset+len(anchor['quote']),source_sha256=c.fingerprint(text)))
    c.write_json(folder/'anchor_checks.json',checks)
    coverage=dict(created_utc=c.now(),actually_read_cases=len(notes),patients=len(patients),
        complete_references_read=len(notes),reference_characters=characters,complete_outputs_read=2*len(notes),
        literal_anchors=len(checks),post_hoc=True,illustrative_lambda=1.5,selected_winner=False,
        reading_scope='Full original claim, full fixed C48 and full B/S responses for all eleven listed cases',
        generated_U0_packets_not_counted=21,no_new_medical_gold=True,independent_audit=False,
        unreviewed_650_minus_read=650-len(notes),medical_mechanism_prevalence_not_estimated=True)
    c.write_json(folder/'reading_coverage.json',coverage)
    lines=['# 019有限语义深读：已实际阅读11例','',
        '事后选择lambda=1.5作为已登记网格中的机制示例；不是通过门槛的参数。每例完整读取原claim、C48全文、B/S完整输出。',
        '共6名既用患者、22份模型输出。仅单次回答，没有稳定性结论或新增医生gold。原case_packets的21份U0材料只生成，不计作完整深读。','']
    for note in notes:
        row=lookup[note['case_id']]
        lines+=['## '+note['case_id']+'（'+', '.join(row['groups'])+'）',
                note['observation'],'',note['interpretation'],'',
                '**边界：** '+note['uncertainty'],'',
                '[完整材料]('+row['case_id']+'.md)；字面锚点见anchor_checks.json。','']
    (folder/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    c.write_json(folder/'manifest.json',dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in folder.iterdir() if p.is_file()}))
    print(c.canonical(coverage),flush=True)

if __name__=='__main__':
    check()
