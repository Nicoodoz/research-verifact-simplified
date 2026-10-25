"""Paper-ready numeric tables and literal input differences; all offline."""
from collections import Counter
from pathlib import Path
import statistics
import argparse
import study009 as s
from io009 import stage


def compile(output):
    output=output.resolve()
    rows,classes,contrasts,patient,changes,loo=[],[],[],[],[],[]
    summaries={}
    for name in ('development_001','confirmation_001'):
        folder=s.OUT/name
        s.check(folder/'analysis_001')
        metrics=s.read_json(folder/'analysis_001/metrics.json')
        cohort=s.pilot.read_csv(folder/'preparation/cohort.csv')[1]
        predictions={m:s.pilot.read_csv(folder/'analysis_001'/('predictions_'+m+'.csv'))[1] for m in ('A48','B48','C48')}
        for author,section in metrics.items():
            for method,result in section['metrics'].items():
                rows.append(dict(cohort=name,author=author,method=method,n=result['n'],PA=result['percent_agreement'],AC1=result['gwet_ac1'],MCC=result['mcc']))
                for label,v in result['per_class'].items():
                    classes.append(dict(cohort=name,author=author,method=method,label=label,**v))
            for contrast,value in section['contrasts'].items():
                for metric,v in value['metrics'].items():
                    contrasts.append(dict(cohort=name,author=author,contrast=contrast,metric=metric,delta=v['delta'],ci_low=v['ci95'][0],ci_high=v['ci95'][1]))
        for row in s.read_json(folder/'analysis_001/patient_metrics.json'):
            patient.append(dict(cohort=name,subject_id=row['subject_id'],author=row['author_type'],method=row['method'],n=row['n'],PA=row['percent_agreement'],AC1=row['gwet_ac1'],MCC=row['mcc']))
        pp={p['passage_id']:p for p in s.pilot.jsonl(folder/'preparation/corpus.jsonl')}
        inputs=s.pilot.jsonl(folder/'judge_preparation/inputs.jsonl')
        old={x['proposition_id']:x for x in s.pilot.jsonl(s.PRIOR/'judge_preparation_001/inputs.jsonl')} if name=='development_001' else {}
        def sequence(r):
            return [(pp[k]['date'],pp[k]['time'],pp[k]['category'],pp[k]['text']) for k in r['selected_ids']]
        for item in inputs:
            a=item['retrieval']['A48']
            for method in ('B48','C48'):
                b=item['retrieval'][method]
                changes.append(dict(cohort=name,case_id=item['case_id'],method=method,same_body=b['body_sha256']==a['body_sha256'],
                    same_literal_sequence=sequence(a)==sequence(b),same_literal_set=set(sequence(a))==set(sequence(b)),
                    candidate_new=len(set(b['candidate_ids'])-set(a['candidate_ids'])),candidate_lost=len(set(a['candidate_ids'])-set(b['candidate_ids'])),
                    selected_new=len(set(sequence(b))-set(sequence(a))),selected_lost=len(set(sequence(a))-set(sequence(b))),
                    A_candidates=len(a['candidate_ids']),new_candidates=len(b['candidate_ids'])))
            if old:
                prev=old[item['proposition_id']]['retrieval']['direct']
                changes.append(dict(cohort=name,case_id=item['case_id'],method='009_A_vs_008_direct',same_reference=prev['reference']==a['reference'],
                    same_literal_sequence=sequence(prev)==sequence(a),same_literal_set=set(sequence(prev))==set(sequence(a))))
        summaries[name]={method:dict(n=len(own),same_body=sum(x.get('same_body',x.get('same_reference',False)) for x in own),
            same_literal_sequence=sum(x['same_literal_sequence'] for x in own),same_literal_set=sum(x['same_literal_set'] for x in own))
            for method in sorted({x['method'] for x in changes if x['cohort']==name})
            for own in [[x for x in changes if x['cohort']==name and x['method']==method]]}
        if name=='confirmation_001':
            for excluded in sorted({r['subject_id'] for r in cohort}):
                for author in ('llm','human'):
                    own=[r for r in cohort if r['author_type']==author and r['subject_id']!=excluded]
                    ids={r['proposition_id'] for r in own}
                    result={method:s.pilot.evaluate(own,[r for r in pred if r['proposition_id'] in ids],profile='none') for method,pred in predictions.items()}
                    loo.append(dict(excluded_patient=excluded,author=author,n=len(own),B_minus_A_MCC=result['B48']['mcc']-result['A48']['mcc'],
                        C_minus_A_MCC=result['C48']['mcc']-result['A48']['mcc'],posthoc_influence_not_primary=True))
    costs=[]
    for phase in s.STAGE_CAPS:
        values,attempts=stage(phase)
        usages=Counter()
        for v in values.values():
            for key,n in (v['native'] or {}).get('usage',{}).items():
                if isinstance(n,(int,float)):
                    usages[key]+=n
        costs.append(dict(phase=phase,actual_service_kinds=dict(Counter(v['job']['kind'] for v in values.values())),logical_jobs=len(values),
            http_attempts=len(attempts),http_status_counts=dict(Counter(x['http_status'] for x in attempts)),usage=dict(usages),
            rerank_pairs=sum(len(v['job'].get('passage_ids',[])) for v in values.values()),
            embedding_texts=sum(len(v['job'].get('text_ids',[])) for v in values.values()),
            used_or_reserved_cny=sum(x['charge_cny'] for x in attempts),fixed_cap_cny=s.STAGE_CAPS[phase],
            accounts_used=sorted({x['account'] for x in attempts}),invoices_verified=False))
    total=dict(costs=costs,total_cny=sum(x['used_or_reserved_cny'] for x in costs),total_jobs=sum(x['logical_jobs'] for x in costs),
        total_attempts=sum(x['http_attempts'] for x in costs),cap_cny=sum(s.STAGE_CAPS.values()),
        note='dev_embed is the recorded rerank refresh, not embeddings; initial discarded rerank and every retry counted; old cached 008 calls excluded')
    assert total['total_cny']<=total['cap_cny']==40
    output.mkdir(parents=True,exist_ok=False)
    for filename,data in [('core_results.csv',rows),('class_results.csv',classes),('paired_differences.csv',contrasts),('patient_results.csv',patient),('leave_one_patient_out.csv',loo)]:
        s.pilot.write_csv(output/filename,data)
    s.pilot.write_jsonl(output/'literal_evidence_changes.jsonl',changes)
    s.pilot.write_json(output/'input_change_summary.json',summaries)
    s.pilot.write_json(output/'costs.json',total)
    text=['|队列|作者|方案|N|PA|AC1|MCC|','|---|---|---|---:|---:|---:|---:|']
    text.extend(f"|{r['cohort']}|{r['author']}|{r['method']}|{r['n']}|{r['PA']:.4f}|{r['AC1']:.4f}|{r['MCC']:.4f}|" for r in rows)
    (output/'core_results.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    deps=[s.OUT/name/'analysis_001/manifest.json' for name in ('development_001','confirmation_001')]
    deps += [s.OUT/'live'/phase/'state.json' for phase in s.STAGE_CAPS]
    s.seal(output,deps,[Path(__file__),s.TASK/'io009.py'])
    print(s.pilot.canonical(dict(total=total,input_changes=summaries,leave_one_patient_out=loo)))


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=s.OUT/'synthesis_001')
    compile(ap.parse_args().output)
