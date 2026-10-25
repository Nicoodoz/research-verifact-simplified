"""Fixed002 evaluation and preregistered headroom decision; no new calls or method tuning."""
from pathlib import Path
from collections import Counter
import argparse
import common017 as c
from io017 import logical
from gate017 import assess

def analyze(out):
    c.require(not out.exists(),'Analysis already exists')
    values,norm,attempts,total,labels,providers,provenance=logical()
    records=c.jsonlines(c.OUT/'preparation_001/inputs.jsonl');cohort=c.csvrows(c.OUT/'evaluation_cohort.csv');gt={r['proposition_id']:r['human_gt'] for r in cohort}
    gate,cases,events=assess(records,labels,gt,providers)
    out.mkdir(parents=True);c.write_json(out/'gate.json',gate);c.write_csv(out/'cases.csv',cases);c.write_csv(out/'utility_events.csv',events)
    c.write_csv(out/'attempts.csv',attempts);c.write_csv(out/'canonical_provenance.csv',provenance);c.write_lines(out/'normalized_responses.jsonl',list(norm.values()))
    c.write_csv(out/'cohort.csv',cohort)
    metrics={};paired={};core=[];classes=[];patients=[];changes=[];rates=[]
    for repeat in (0,1):
        preds={arm:[dict(proposition_id=r['proposition_id'],verdict=labels[(r['proposition_id'],arm,repeat)]) for r in cohort] for arm in c.ARMS}
        for arm,pp in preds.items():c.write_csv(out/f'predictions_r{repeat}_{arm}.csv',pp)
        metrics[str(repeat)]={};paired[str(repeat)]={}
        for author in ('llm','human'):
            own=[r for r in cohort if r['author_type']==author];ids={r['proposition_id'] for r in own}
            pp={arm:[r for r in p if r['proposition_id'] in ids] for arm,p in preds.items()}
            mm={arm:c.evaluate(own,p,iterations=1000,missing='error') for arm,p in pp.items()};metrics[str(repeat)][author]=mm
            paired[str(repeat)][author]={arm:c.paired_compare(own,pp['baseline'],p,iterations=1000) for arm,p in pp.items() if arm!='baseline'}
            for arm,m in mm.items():
                core.append(dict(repeat=repeat,author=author,arm=arm,n=m['n'],correct=sum(m['confusion_matrix'][i][i] for i in range(3)),PA=m['percent_agreement'],AC1=m['gwet_ac1'],MCC=m['mcc']))
                for label,v in m['per_class'].items():classes.append(dict(repeat=repeat,author=author,arm=arm,label=label,**v))
                for sid in sorted({r['subject_id'] for r in own}):
                    rr=[r for r in own if r['subject_id']==sid]
                    patients.append(dict(repeat=repeat,author=author,subject_id=sid,arm=arm,n=len(rr),correct=sum(labels[(r['proposition_id'],arm,repeat)]==r['human_gt'] for r in rr)))
                if arm!='baseline':
                    fixed=sum(labels[(r['proposition_id'],arm,repeat)]==r['human_gt'] and labels[(r['proposition_id'],'baseline',repeat)]!=r['human_gt'] for r in own)
                    broken=sum(labels[(r['proposition_id'],arm,repeat)]!=r['human_gt'] and labels[(r['proposition_id'],'baseline',repeat)]==r['human_gt'] for r in own)
                    changes.append(dict(repeat=repeat,author=author,arm=arm,rescue=fixed,harm=broken,net=fixed-broken))
            own_cases=[r for r in cases if r['author_type']==author]
            if repeat==0:
                for group,key in [('stable_wrong','stable_wrong'),('stable_correct','stable_correct')]:
                    sub=[r for r in own_cases if r[key]]
                    rates.append(dict(author=author,group=group,n=len(sub),rescued=sum(r['rescued'] for r in sub),harmed=sum(r['harmed'] for r in sub),same_pool_rescued=sum(r['same_pool_rescued'] for r in sub)))
    stability={author:c.paired_compare([r for r in cohort if r['author_type']==author],
        [dict(proposition_id=r['proposition_id'],verdict=labels[(r['proposition_id'],'baseline',0)]) for r in cohort if r['author_type']==author],
        [dict(proposition_id=r['proposition_id'],verdict=labels[(r['proposition_id'],'baseline',1)]) for r in cohort if r['author_type']==author],iterations=1000) for author in ('llm','human')}
    strata=[]
    for key in ('subject_id','author_type','human_gt','split'):
        for value in sorted({r[key] for r in cases}):
            sub=[r for r in cases if r[key]==value]
            strata.append(dict(dimension=key,value=value,n=len(sub),stable_wrong=sum(r['stable_wrong'] for r in sub),stable_correct=sum(r['stable_correct'] for r in sub),
                stable_rescued=sum(r['rescued'] for r in sub),stable_harmed=sum(r['harmed'] for r in sub),same_pool_rescued=sum(r['same_pool_rescued'] for r in sub)))
    diagnostics=[]
    for bucket,eligible in [('rescue',[r for r in cases if r['rescued']]),('harm',[r for r in cases if r['harmed']]),('unstable',[r for r in cases if r['baseline_label_flip']])]:
        diagnostics.extend(dict(r,selection_bucket=bucket) for r in sorted(eligible,key=lambda r:c.rank_id(r['proposition_id']))[:2])
    c.write_csv(out/'selected_diagnostics.csv',diagnostics,list(cases[0])+['selection_bucket'])
    snapshots=out/'diagnostic_packets';snapshots.mkdir()
    byid={r['proposition_id']:r for r in records};assignment={(a['proposition_id'],a['arm'],int(a['repeat'])):a['request_id'] for a in provenance}
    for pid in sorted({r['proposition_id'] for r in diagnostics}):
        item=byid[pid]
        c.write_json(snapshots/(item['case_id']+'.json'),dict(item=item,human_gt=gt[pid],outputs={arm:[norm[assignment[(pid,arm,r)]] for r in (0,1)] for arm in c.ARMS}))
    summary=dict(status='complete',claims=192,patients=12,unique_requests=len(norm),logical_conditions=len(labels),
        HTTP_attempts=len(attempts),status_counts=dict(Counter(a['http_status'] for a in attempts)),accounts=dict(Counter(a['account'] for a in attempts)),
        providers=dict(Counter(v['receipt']['provider'] for v in values.values())),used_or_reserved_cny=total,
        unknown_reservations_cny=sum(a['charge_cny'] for a in attempts if 'unknown' in a['charge_basis']),cap_cny=80,
        gate_passed=gate['passed'],decision=gate['reason'],new10_clinical_data_used=False,reserved_test_used=False,selector_trained=False,
        actual_usage=dict(input_tokens=sum(n['usage']['input_tokens'] for n in norm.values()),output_tokens=sum(n['usage']['output_tokens'] for n in norm.values())),
        adherence_flagged=sum(bool(n['adherence_errors']) for n in norm.values()),
        corpus_and_scores_reused=True,wide_pool_not_equal013_top80=True)
    for name,data in [('metrics',metrics),('paired',paired),('baseline_repeat_comparison',stability),('summary',summary)]:c.write_json(out/(name+'.json'),data)
    for name,data in [('core_results',core),('classes',classes),('patients',patients),('changes',changes),('stable_rates',rates),('strata',strata)]:c.write_csv(out/(name+'.csv'),data)
    c.seal(out,[c.OUT/'preparation_001/manifest.json',c.OUT/'evaluation_cohort.csv',c.OUT/'live/ledger.json',c.OUT/'execution_policy_001.json'],[Path(__file__),c.TASK/'gate017.py',c.TASK/'io017.py'])
    print(c.canonical(summary));print(c.canonical(gate))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'analysis_001');analyze(p.parse_args().output.resolve())
