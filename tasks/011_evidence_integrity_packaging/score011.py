"""Receipt-only unified scoring, per-round contrasts, and frozen pilot gate."""
from collections import Counter
from pathlib import Path
import argparse
import study011 as s
from io011 import stage,normalize
from score009 import evaluate_scope,movement

CONTRASTS=(('B','C'),('A','B'),('A','C'))

def score(phase,output):
    prep=s.OUT/f'{phase}_preparation_001';s.check(prep)
    offline=s.OUT/'offline_003';s.check(offline)
    inputs={r['proposition_id']:r for r in s.pilot.jsonl(offline/'inputs.jsonl')}
    allcohort=s.pilot.read_csv(offline/'cohort.csv')[1]
    assignments=s.pilot.read_csv(prep/'assignments.csv')[1]
    values,attempts=stage(phase)
    jobs={j['request_id']:j for j in s.pilot.jsonl(prep/'jobs.jsonl')}
    pid_by_rid={r['request_id']:r['proposition_id'] for r in assignments}
    results={rid:normalize(v['job'],v['receipt'],pid_by_rid[rid]) for rid,v in values.items()}
    for rid,v in results.items():
        if v['status']=='success':assert v['request_sha256']==s.pilot.fingerprint(jobs[rid]['body'])
    rounds={};rows=[];patient=[]
    for repeat in sorted({int(a['round']) for a in assignments}):
        own=[a for a in assignments if int(a['round'])==repeat]
        ids={a['proposition_id'] for a in own};cohort=[r for r in allcohort if r['proposition_id'] in ids]
        pp={arm:[dict(proposition_id=a['proposition_id'],verdict=results[a['request_id']]['verdict']) for a in own if a['arm']==arm and results[a['request_id']]['status']=='success'] for arm in s.METHODS}
        lookup={arm:{p['proposition_id']:p['verdict'] for p in ps} for arm,ps in pp.items()}
        rounds[str(repeat)]=evaluate_scope(cohort,pp,s.METHODS,CONTRASTS)
        for r in cohort:
            pid=r['proposition_id'];verdicts={a:lookup[a].get(pid) for a in s.METHODS}
            row=dict(r,case_id=inputs[pid]['case_id'],round=repeat,**verdicts)
            for a,b in CONTRASTS:row[b+'_minus_'+a]=movement(verdicts[a],verdicts[b],r['human_gt'])
            rows.append(row)
        for sid in sorted({r['subject_id'] for r in cohort}):
            for author in ('llm','human'):
                cc=[r for r in cohort if r['subject_id']==sid and r['author_type']==author]
                ids={r['proposition_id'] for r in cc}
                for arm in s.METHODS:
                    preds=[p for p in pp[arm] if p['proposition_id'] in ids]
                    if cc and len(cc)==len(preds):patient.append(dict(round=repeat,subject_id=sid,author_type=author,arm=arm,**s.pilot.evaluate(cc,preds,profile='none')))
    transitions={str(i):{author:{b+'_minus_'+a:dict(Counter(r[b+'_minus_'+a] for r in rows if r['round']==i and r['author_type']==author)) for a,b in CONTRASTS} for author in ('llm','human')} for i in sorted({r['round'] for r in rows})}
    failures=[dict(request_id=rid,status=r['status'],errors=r.get('structural_errors')) for rid,r in results.items() if r['status']!='success']
    gate=None
    if phase=='pilot':
        comparisons={}
        for a,b in (('A','B'),('B','C')):
            nets=[sum((r[b]==r['human_gt'])-(r[a]==r['human_gt']) for r in rows if r['round']==i) for i in range(3)]
            robust=[pid for pid in sorted({r['proposition_id'] for r in rows}) if sum(r[b+'_minus_'+a]=='improved' for r in rows if r['proposition_id']==pid)>=2]
            pats=sorted({inputs[pid]['subject_id'] for pid in robust})
            falseS=sum((r[b]=='Supported')-(r[a]=='Supported') for r in rows if r['human_gt']!='Supported')
            qualified=sum(x>0 for x in nets)>=2 and sum(nets)>=3 and len(robust)>=2 and len(pats)>=2 and falseS<=2
            comparisons[b+'_minus_'+a]=dict(round_net_correct=nets,sum_net_correct=sum(nets),robust_improved_ids=robust,robust_improved_patients=pats,increase_false_supported=falseS,qualified=qualified)
        offline_ok=s.read_json(s.OUT/'offline_review_003/reading_conclusion.json')['allow_pilot']
        coverage=s.read_json(offline/'summary.json')['C_B_changed']/650
        gate=dict(proceed_main=not failures and offline_ok and coverage>=.1 and any(c['qualified'] for c in comparisons.values()),
            comparisons=comparisons,complete=not failures,offline_ok=offline_ok,C_B_coverage=coverage,predefined=True,
            interpretation='Exploratory cost gate, not significance or proof that the entire research direction is ineffective.')
    repeat_rows=[]
    for pid in sorted({r['proposition_id'] for r in rows}):
        own=sorted([r for r in rows if r['proposition_id']==pid],key=lambda r:r['round'])
        if len(own)<2:continue
        repeat_rows.append(dict(proposition_id=pid,case_id=inputs[pid]['case_id'],subject_id=inputs[pid]['subject_id'],
            author_type=inputs[pid]['author_type'],human_gt=own[0]['human_gt'],verdicts={a:[r[a] for r in own] for a in s.METHODS},
            varying={a:len({r[a] for r in own})>1 for a in s.METHODS}))
    summary=dict(phase=phase,valid_requests=sum(r['status']=='success' for r in results.values()),expected_requests=len(jobs),logical_conditions=len(assignments),
        http_attempts=len(attempts),http_counts=dict(Counter(a['http_status'] for a in attempts)),cost_cny=sum(a['charge_cny'] for a in attempts),
        transitions=transitions,repeat_varying={a:sum(r['varying'][a] for r in repeat_rows) for a in s.METHODS},failures=failures,
        usage=dict(input_tokens=sum(r.get('usage',{}).get('input_tokens',0) for r in results.values()),output_tokens=sum(r.get('usage',{}).get('output_tokens',0) for r in results.values())),
        independent_audit=False)
    output.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(output/'metrics_by_round.json',rounds)
    s.pilot.write_json(output/'patient_metrics.json',patient)
    s.pilot.write_csv(output/'predictions_and_transitions.csv',rows)
    s.pilot.write_jsonl(output/'normalized_responses.jsonl',list(results.values()))
    s.pilot.write_json(output/'repeats.json',repeat_rows)
    s.pilot.write_csv(output/'attempts.csv',attempts)
    s.pilot.write_json(output/'summary.json',summary)
    if gate is not None:s.pilot.write_json(output/'gate.json',gate)
    s.seal(output,[prep/'manifest.json',s.OUT/f'live/{phase}/state.json'],[Path(__file__),s.TASK/'io011.py',s.ROOT/'tasks/009_retrieval_baselines/score009.py'])
    print(s.pilot.canonical(summary));print(s.pilot.canonical(gate))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=s.STAGE_CAPS);ap.add_argument('--output',type=Path)
    a=ap.parse_args();score(a.phase,a.output or s.OUT/f'{a.phase}_analysis_001')
