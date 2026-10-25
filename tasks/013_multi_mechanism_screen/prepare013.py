"""Freeze selections and single-component requests before receiving new outputs."""
from pathlib import Path
from collections import Counter
import argparse,copy
import study013 as s
import mechanisms013 as m

CONTRACT_CASES=['N050','N104','N139','N188','N262','N264','N359','N388']
AUX_CASES=['N071','N104','N248','N264','N395','N526','N561','N585']
ANCHORS={
 'N071':['4e47d56e804b0fa070e44ba7d61e446c58c3be624aa522d1212d1f74c0739fd9'],
 'N395':['1088d673981fe3d72c8dea46f3f0b2f08fc00b9ec783dc40781a3b70ca21b2b1','4232e28e7b1f145f9d421a59ed9b7b961349db50eede917a1e0c1219daa52755'],
 'N561':['adceb58ef52b98850db596a20e97c924c636b529c783538cfbff5bc5b9898d2a'],
 'N526':['01fba133b6d73ebbf6ef75d8405dbe1b82d6e7abbb0720850b879b08377dda9d','04e3824a1a95a0bf4d8505f29b8926b7d2653c68250a7746aad616b7a1db6356'],
}

def source_data():
    items=s.pilot.jsonl(s.NINE/'judge_preparation/inputs.jsonl')
    passages={p['passage_id']:p for p in s.pilot.jsonl(s.NINE/'preparation/corpus.jsonl')}
    notes={n['ROW_ID']:n for n in s.pilot.jsonl(s.TWELVE/'materials_001/ehr_notes.jsonl')}
    prompts=s.read_json(s.ROOT/'outputs/011_evidence_integrity_packaging/offline_003/judge_prompts.json')
    return items,passages,notes,prompts

def estimate(jobs):
    result=0
    for j in jobs:
        if j['kind']=='chat':
            # Calibrated against 009/010 receipt ratios; extra allowance for selector.
            chars=sum(len(x['content']) for x in j['body']['messages'])
            result+=(chars*.34*3+(300 if j['body']['max_tokens']==2048 else 300)*9)/1e6
        else:result+=s.native.bound(j)
    return result

def save_jobs(phase,jobs,assignments=None,dependencies=()):
    out=s.OUT/f'{phase}_preparation_001';out.mkdir(parents=True,exist_ok=False)
    jobs=sorted(jobs,key=lambda j:s.pilot.digest_text('013/schedule/v1:'+j['request_id']))
    s.pilot.write_jsonl(out/'jobs.jsonl',jobs)
    if assignments is not None:s.pilot.write_csv(out/'assignments.csv',assignments)
    summary=dict(phase=phase,requests=len(jobs),estimated_peak_cny=estimate(jobs),single_stage_ceiling=s.STAGE_CAPS[phase],
        whole_task_cap=40,byte_reservations_in_runner=True,logical_conditions=len(assignments) if assignments is not None else len(jobs))
    s.pilot.write_json(out/'summary.json',summary)
    s.freeze(out,[s.OUT/'protocol_001.md',*dependencies],[Path(__file__),s.TASK/'mechanisms013.py',s.TASK/'study013.py'])
    print(s.pilot.canonical(summary));return summary

def init():
    items,pp,notes,prompts=source_data();bycase={x['case_id']:x for x in items}
    rows=s.pilot.jsonl(s.TWELVE/'diagnosis_001/ledger.jsonl')
    chosen={r['proposition_id'] for r in rows if r['error_union']};controls=[]
    for sid in sorted({r['subject_id'] for r in rows}):
        for a in ('llm','human'):
            options=[r for r in rows if r['subject_id']==sid and r['author_type']==a and r['correctness_pattern']=='111']
            controls+=sorted(options,key=lambda r:s.pilot.digest_text('013/control/v1:'+r['proposition_id']))[:3]
    chosen|={r['proposition_id'] for r in controls};assert len(chosen)==231
    out=s.OUT/'preparation_001';out.mkdir(parents=True,exist_ok=False)
    cohort=s.pilot.read_csv(s.NINE/'preparation/cohort.csv')[1]
    selected=[r for r in cohort if r['proposition_id'] in chosen]
    s.pilot.write_csv(out/'screen_cohort.csv',selected)
    s.pilot.write_json(out/'selection.json',dict(error_union=195,stable_controls=[r['proposition_id'] for r in controls],
        selected_ids=[r['proposition_id'] for r in selected],class_counts={a:dict(Counter(r['human_gt'] for r in selected if r['author_type']==a)) for a in ('llm','human')},
        unit_contract=CONTRACT_CASES,unit_aux=AUX_CASES,diagnostic_anchors=ANCHORS,
        prospective_eight=s.old.patient_order()[24:32],prospective_with_selector=s.old.patient_order()[24:28]))
    s.pilot.write_json(out/'judge_prompts.json',prompts)
    repairs=[]
    for x in items:
        baseline=s.core.select_evidence(x['retrieval']['C48']['candidate_ids'],x['scores'],pp,x['admission'])
        assert baseline['reference']==x['retrieval']['C48']['reference']
        r=m.text_guard(x,pp,notes)
        repairs.append(dict(case_id=x['case_id'],proposition_id=x['proposition_id'],contract=m.literal_contract(x['text']),
            reference_changed=r['reference']!=baseline['reference'],repairs=r['repairs'],
            lost_ids=sorted(set(baseline['selected_ids'])-set(r['selected_ids'])),added_ids=sorted(set(r['selected_ids'])-set(baseline['selected_ids']))))
    s.pilot.write_jsonl(out/'offline_coverage.jsonl',repairs)
    # Known raw-mechanism assertions, independent of their physician verdicts.
    assert 'Text: No nausea' in m.text_guard(bycase['N086'],pp,notes)['reference']
    assert 'If there are any\n   concerns for aspiration on this diet, please keep patient\n   STRICT NPO' in m.text_guard(bycase['N642'],pp,notes)['reference']
    assert set(ANCHORS['N526'])<=set(m.wide_pool(bycase['N526']))
    assert not (set(ANCHORS['N526'])&set(bycase['N526']['retrieval']['C48']['candidate_ids']))
    assert all(set(x['retrieval']['C48']['candidate_ids'])<=set(m.wide_pool(x)) for x in items)
    s.pilot.write_json(out/'offline_checks.json',dict(baseline_reconstructed=650,text_guard_probe=True,wide_pool_superset=True,
        contract_span_concatenation=all(c is None or c['subject']+c['predicate']==x['text'] for x in items for c in [m.literal_contract(x['text'])]),
        changed_references=sum(r['reference_changed'] for r in repairs),contract_applicable=sum(r['contract'] is not None for r in repairs)))
    sources=[s.NINE/'judge_preparation/inputs.jsonl',s.NINE/'preparation/corpus.jsonl',s.NINE/'preparation/cohort.csv',
        s.TWELVE/'diagnosis_001/ledger.jsonl',s.TWELVE/'materials_001/ehr_notes.jsonl',s.ROOT/'outputs/003_error_analysis/patient_groups.json']
    s.freeze(out,[s.OUT/'protocol_001.md',*sources],[Path(__file__),s.TASK/'study013.py',s.TASK/'mechanisms013.py'])
    aux=[j for cid in AUX_CASES for j in [m.rerank_job(bycase[cid],pp),m.selector_job(bycase[cid],pp)]]
    save_jobs('unit_aux',aux,dependencies=[out/'manifest.json'])
    jobs={};assign=[]
    for cid in CONTRACT_CASES:
        x=bycase[cid]
        for arm in ('baseline','contract'):
            body=(m.contract_body if arm=='contract' else s.judge_body)(x,x['retrieval']['C48']['reference'],prompts)
            sha=s.pilot.fingerprint(body);rid='unit:r0:'+sha
            jobs[rid]=dict(request_id=rid,kind='chat',body=body)
            assign.append(dict(case_id=cid,proposition_id=x['proposition_id'],arm=arm,round=0,request_id=rid,body_sha256=sha))
    save_jobs('unit_judge',list(jobs.values()),assign,[out/'manifest.json'])
    # Upper expected screening scenario uses all candidates before gate, not new labels.
    screen=[x for x in items if x['proposition_id'] in chosen]
    aux_expected=estimate([j for x in screen for j in (m.rerank_job(x,pp),m.selector_job(x,pp))])
    judge_expected=0
    for x in screen:
        ref=x['retrieval']['C48']['reference'];b=s.judge_body(x,ref,prompts)
        judge_expected+=estimate([dict(kind='chat',body=b)])*3 # baseline, wide, selector
        if m.literal_contract(x['text']):judge_expected+=estimate([dict(kind='chat',body=m.contract_body(x,ref,prompts))])
        r=m.text_guard(x,pp,notes)
        if r['reference']!=ref:judge_expected+=estimate([dict(kind='chat',body=s.judge_body(x,r['reference'],prompts))])
    s.pilot.write_json(s.OUT/'budget_plan_001.json',dict(unit_expected=estimate(aux)+estimate(list(jobs.values())),
        screen_aux_expected=aux_expected,screen_judge_expected_without_refresh_duplicates=judge_expected,
        confirmation_eight_claims=789,confirmation_with_selector_four_claims=372,
        task_cap_cny=40,expected_total_cny=estimate(aux)+estimate(list(jobs.values())),role='only mechanism-unit calls currently planned; unconditional all-branches plus confirmation may exceed 40, later gates and actual requests must be re-estimated before sending',
        pricing_url='https://docs.siliconflow.cn/docs/release-notes/overview'))

if __name__=='__main__':init()
