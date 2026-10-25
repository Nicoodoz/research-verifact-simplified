"""Predefine pilot repeats and main contemporaneous requests before inference."""
from pathlib import Path
import study011 as s


def build(phase):
    offline=s.OUT/'offline_003';s.check(offline)
    items=s.pilot.jsonl(offline/'inputs.jsonl')
    selected=s.read_json(offline/'pilot_selection.json')
    prompts=s.read_json(offline/'judge_prompts.json')
    jobs={};assignments=[]
    for item in items:
        if phase=='pilot' and item['case_id'] not in selected:continue
        rounds=range(3) if phase=='pilot' else range(2 if item['case_id'] in selected else 1)
        for repeat in rounds:
            for arm in s.METHODS:
                body=s.judge_body(item,item['retrieval'][arm]['reference'],prompts)
                digest=s.pilot.fingerprint(body)
                # Share identical complete inputs across arms, independently per round.
                rid=f'{phase}:r{repeat}:'+digest
                jobs[rid]=dict(request_id=rid,kind='chat',body=body)
                assignments.append(dict(proposition_id=item['proposition_id'],case_id=item['case_id'],arm=arm,round=repeat,request_id=rid,body_sha256=digest))
    jobs=sorted(jobs.values(),key=lambda j:s.pilot.digest_text('011/schedule/v1:'+j['request_id']))
    # Conservative peak planning estimate; online byte reservations independently cap spend.
    estimate=sum((sum(len(m['content']) for m in j['body']['messages'])*.4*3+400*9)/1e6 for j in jobs)
    out=s.OUT/f'{phase}_preparation_001';out.mkdir()
    s.pilot.write_jsonl(out/'jobs.jsonl',jobs)
    s.pilot.write_csv(out/'assignments.csv',assignments)
    summary=dict(phase=phase,claims=len({a['proposition_id'] for a in assignments}),logical_conditions=len(assignments),unique_requests=len(jobs),
        expected_peak_cny=estimate,cap_cny=s.STAGE_CAPS[phase],cache='same complete body within the same phase and repeat round; never reuse old answers or a pilot answer in main')
    s.pilot.write_json(out/'summary.json',summary)
    s.seal(out,[offline/'manifest.json'],[Path(__file__),s.TASK/'study011.py'])
    print(s.pilot.canonical(summary))


if __name__=='__main__':
    build('pilot');build('main')
