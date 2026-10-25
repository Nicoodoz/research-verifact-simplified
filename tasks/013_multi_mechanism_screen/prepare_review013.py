"""Balanced review sampling defined before reading new Judge results."""
from collections import defaultdict
import study013 as s
from score009 import movement

def choose(rows,inputs,gates):
    selected=defaultdict(list)
    for arm,g in gates.items():
        if g['statistical_gate']:
            for r in rows:
                if movement(r['baseline'],r[arm],r['human_gt']) in ('improved','worsened','changed_wrong'):
                    selected[(r['proposition_id'],arm)].append('all_flips_statistical_candidate')
        else:
            for author in ('llm','human'):
                for direction in ('improved','worsened','changed_wrong'):
                    options=[r for r in rows if r['author_type']==author and movement(r['baseline'],r[arm],r['human_gt'])==direction]
                    for r in sorted(options,key=lambda r:s.pilot.digest_text('013/review/v1:'+arm+direction+r['proposition_id']))[:1]:
                        selected[(r['proposition_id'],arm)].append('stopped_branch_author_direction_hash')
        for author in ('llm','human'):
            for direction in ('stable_correct','stable_wrong'):
                options=[r for r in rows if r['author_type']==author and movement(r['baseline'],r[arm],r['human_gt'])==direction
                    and (arm=='contract' or inputs[r['proposition_id']]['retrieval'][arm]['reference']!=inputs[r['proposition_id']]['retrieval']['baseline']['reference'])]
                for r in sorted(options,key=lambda r:s.pilot.digest_text('013/control-review/v1:'+arm+direction+r['proposition_id']))[:1]:
                    selected[(r['proposition_id'],arm)].append('stable_control_hash')
    return [dict(proposition_id=p,arm=a,reasons=reasons) for (p,a),reasons in selected.items()]

def run():
    rows=s.pilot.jsonl(s.OUT/'screen_analysis_001/transitions.jsonl')
    inputs={r['proposition_id']:r for r in s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl')}
    selected=choose(rows,inputs,s.read_json(s.OUT/'screen_analysis_001/mechanical_gates.json'))
    lookup={r['proposition_id']:r for r in rows}
    for r in selected:r.update(case_id=lookup[r['proposition_id']]['case_id'],author_type=lookup[r['proposition_id']]['author_type'],
        direction=movement(lookup[r['proposition_id']]['baseline'],lookup[r['proposition_id']][r['arm']],lookup[r['proposition_id']]['human_gt']))
    out=s.OUT/'review_001';out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(out/'selection.json',selected)
    print(s.pilot.canonical(selected))

if __name__=='__main__':run()
