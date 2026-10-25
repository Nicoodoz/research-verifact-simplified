"""Preregistered headroom gate. Outcomes are used only after action freezing."""
from collections import Counter
import math
import common017 as c

def assess(records,labels,gt,providers):
    events=[];cases=[]
    for item in records:
        pid=item['proposition_id'];truth=gt[pid];b=[labels[(pid,'baseline',r)] for r in (0,1)]
        bp=[providers[(pid,'baseline',r)] for r in (0,1)]
        stable=b[0]==b[1] and bp[0]==bp[1]
        row=dict(proposition_id=pid,subject_id=item['subject_id'],author_type=item['author_type'],split=item['split'],human_gt=truth,
            stable_correct=stable and b[0]==truth,stable_wrong=stable and b[0]!=truth,baseline_label_flip=b[0]!=b[1],
            baseline_provider_flip=bp[0]!=bp[1],eligible=any(item['interventions'][arm]['eligible'] for arm in c.SWAPS),rescued=False,same_pool_rescued=False,harmed=False)
        for arm in c.SWAPS:
            v=[labels[(pid,arm,r)] for r in (0,1)];pp=[providers[(pid,arm,r)] for r in (0,1)]
            comparable=len(set(bp+pp))==1
            stable_variant=v[0]==v[1] and comparable
            rescue=row['stable_wrong'] and stable_variant and v[0]==truth and item['interventions'][arm]['eligible']
            harm=row['stable_correct'] and stable_variant and v[0]!=truth and item['interventions'][arm]['eligible']
            row['rescued']|=rescue;row['harmed']|=harm
            if arm!='wide_swap':row['same_pool_rescued']|=rescue
            events.append(dict(proposition_id=pid,subject_id=item['subject_id'],author_type=item['author_type'],split=item['split'],human_gt=truth,
                arm=arm,eligible=item['interventions'][arm]['eligible'],same_provider=comparable,stable_variant=stable_variant,
                rescue=rescue,harm=harm,utility=1 if rescue else -1 if harm else 0,
                round0_delta=int(v[0]==truth)-int(b[0]==truth),round1_delta=int(v[1]==truth)-int(b[1]==truth)))
        cases.append(row)
    wrong=[r for r in cases if r['stable_wrong']];correct=[r for r in cases if r['stable_correct']]
    rescued=[r for r in cases if r['rescued']];same=[r for r in cases if r['same_pool_rescued']];harmed=[r for r in cases if r['harmed']]
    train=[r for r in events if r['split']=='train' and r['utility']]
    checks=dict(complete=len(records)==192 and len(labels)==192*len(c.ARMS)*2,
        eligible=sum(r['eligible'] for r in cases)>=144,stable_error_coverage=len(wrong)>=24,stable_correct_coverage=len(correct)>=80,
        substantial_rescue=len(rescued)>=max(12,math.ceil(.25*len(wrong))),rescue_patients=len({r['subject_id'] for r in rescued})>=4,
        both_authors_rescue=all(sum(r['author_type']==a for r in rescued)>=3 for a in ('llm','human')),
        same_pool_rescue=len(same)>=6 and len({r['subject_id'] for r in same})>=3,
        harm_rate=len(harmed)<=.20*len(correct),baseline_flip_rate=sum(r['baseline_label_flip'] for r in cases)<=.15*len(cases),
        train_pairs=len(train)>=16 and len({r['subject_id'] for r in train})>=3)
    gate=dict(passed=all(checks.values()),conditions=checks,stable_errors=len(wrong),stable_correct=len(correct),stable_rescued=len(rescued),
        stable_harmed=len(harmed),same_pool_rescued=len(same),wide_only_rescued=len(rescued)-len(same),
        selection_fixable_fraction=len(rescued)/len(wrong) if wrong else None,train_nonzero_pairs=len(train),
        baseline_label_flips=sum(r['baseline_label_flip'] for r in cases),provider_mixed_baselines=sum(r['baseline_provider_flip'] for r in cases),
        reason='proceed_to_fixed_ranker' if all(checks.values()) else 'stop_insufficient_headroom_or_supervision')
    return gate,cases,events
