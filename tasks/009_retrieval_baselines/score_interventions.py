"""Offline diagnostic scoring; never updates the primary predictions."""
from pathlib import Path
from collections import Counter
import argparse
import study009 as s
from io009 import stage,normalize


def score(output):
    output=output.resolve()
    prep=s.OUT/'interventions_001/preparation'
    s.check(prep)
    assert not (s.OUT/'live/diagnostics/runner.lock').exists()
    values,attempts=stage('diagnostics')
    assignments=s.pilot.read_csv(prep/'assignments.csv')[1]
    pids={a['request_id']:a['proposition_id'] for a in assignments}
    normalized={rid:normalize(v['job'],v['receipt'],pids[rid]) for rid,v in values.items()}
    cache=s.read_json(prep/'cache_bindings.json')
    for sha,binding in cache.items():
        folder=s.OUT/binding['folder']
        s.check(folder/'analysis_001')
        original=next(x for x in s.pilot.jsonl(folder/'analysis_001/normalized_responses.jsonl') if x['request_id']==binding['request_id'])
        assert original==binding['result'] and original['request_sha256']==sha
        normalized[binding['request_id']]=original
    rows=[]
    for a in assignments:
        result=normalized[a['request_id']]
        if result['status']=='success':
            assert result['request_sha256']==a['body_sha256']
        rows.append(dict(a,status=result['status'],verdict=result.get('verdict')))
    cases=s.read_json(prep/'cases.json')
    table,readings=[],[]
    for case in cases:
        cid=case['spec']['case_id']
        own={r['variant']:r for r in rows if r['case_id']==cid}
        row=dict(case_id=cid,gt=case['gt'],original_receiver=case['original_receiver_verdict'],original_donor=case['original_donor_verdict'])
        row.update({mode:r['verdict'] for mode,r in own.items()})
        row['donor_removal_control_missing']=case['donor_removal_control_missing']
        table.append(row)
        text=[f'# {cid}：原claim不变的事后证据诊断',case['claim'],
            '这不是新方法性能或医生证据标签。原预测：'+s.pilot.canonical(row),
            '片段与控制选择见 ../preparation/cases.json 及 ../protocol.md。']
        for mode,r in own.items():
            result=normalized[r['request_id']]
            text.extend(['## '+mode,s.pilot.canonical(dict(status=r['status'],verdict=r['verdict'],source=r['source'],
                request_id=r['request_id'],body_sha256=r['body_sha256'],body_characters=case['variants'][mode]['body_characters'])),
                '```json\n'+str(result.get('output_text'))+'\n```'])
        readings.append((cid,'\n\n'.join(text)+'\n'))
    repeats=[(r[mode],r[original]) for r in table for mode,original in (('receiver_repeat','original_receiver'),('donor_repeat','original_donor'))]
    summary=dict(cases=len(table),logical_conditions=len(rows),new_jobs=len(values),cached_conditions=len(assignments)-len(values),
        successful_conditions=sum(r['status']=='success' for r in rows),failures=[r for r in rows if r['status']!='success'],
        repeat_pairs=len(repeats),repeat_changes=sum(a!=b for a,b in repeats),
        costs_this_phase=sum(x['charge_cny'] for x in attempts),http_status_counts=dict(Counter(x['http_status'] for x in attempts)),
        primary_predictions_replaced=False,clinical_causality_or_gold_evidence_not_established=True)
    output.mkdir(parents=True,exist_ok=False)
    (output/'cases').mkdir()
    for cid,text in readings:
        (output/'cases'/(cid+'.md')).write_text(text,encoding='utf-8')
    s.pilot.write_jsonl(output/'normalized_responses.jsonl',list(normalized.values()))
    s.pilot.write_json(output/'case_results.json',table)
    s.pilot.write_csv(output/'conditions.csv',rows)
    s.pilot.write_csv(output/'attempts.csv',attempts)
    s.pilot.write_json(output/'summary.json',summary)
    s.seal(output,[prep/'manifest.json',s.OUT/'live/diagnostics/state.json',s.OUT/'interventions_001/protocol.md'],[Path(__file__),s.TASK/'io009.py'])
    print(s.pilot.canonical(summary))
    for row in table:
        print(s.pilot.canonical(row))


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=s.OUT/'interventions_001/analysis_001')
    score(ap.parse_args().output)
