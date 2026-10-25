"""Same-cohort release extraction and exact as-produced reference comparison."""
from pathlib import Path
from collections import Counter
import statistics
import duckdb
import pandas as pd
import alignment_common as s


def prepare():
    for name in ('preparation','judge_preparation','analysis_001'):
        s.previous.check(s.PRIOR/name)
    cohort_path=s.PRIOR/'preparation/cohort.csv'
    cohort=s.pilot.read_csv(cohort_path)[1]
    ids={r['proposition_id'] for r in cohort}
    assert len(ids)==len(cohort)==650
    patients=sorted({r['subject_id'] for r in cohort})
    assert patients==sorted(s.previous.patient_order()[18:24])
    oldinputs={x['proposition_id']:x for x in s.pilot.jsonl(s.PRIOR/'judge_preparation/inputs.jsonl')}
    raw_names=['propositions/propositions.csv.gz','verifact/verdicts.parquet','verifact/reference_payloads.parquet','verifact/rater_configurations.csv','verifact/model_metadata.csv']
    formal=s.read_json(s.ROOT/'outputs/002_reproduce_paper_results/run_003/manifest.json')
    raw_hashes={name:s.pilot.digest_file(s.RAW/name) for name in raw_names}
    assert all(raw_hashes[name]==formal['input_sha256'][name] for name in raw_names)
    expected=dict(model='R1-70B',fact_type='sentence',top_n='100',retrieval_method='rerank',reference_format='absolute_time',reference_only_admission='True',deduplicate_text='True')
    configurations=[r for r in s.pilot.read_csv(s.RAW/'verifact/rater_configurations.csv')[1] if all(r[k]==v for k,v in expected.items())]
    assert len(configurations)==1
    cfg=configurations[0]
    assert cfg['rater_alias']=='v1.1.0-rater-121'
    props=s.pilot.subset_csv(s.RAW/'propositions/propositions.csv.gz','proposition_id',ids)
    assert len(props)==650
    props={p['proposition_id']:p for p in props}
    with duckdb.connect() as db:
        db.register('selected',pd.DataFrame({'proposition_id':sorted(ids)}))
        values=db.execute('SELECT v.proposition_id,v.reference_id,v.verdict,v.model,v.rater_alias FROM read_parquet(?) v JOIN selected USING(proposition_id) WHERE v.rater_alias=?',
            [str(s.RAW/'verifact/verdicts.parquet'),cfg['rater_alias']]).fetchall()
        assert len(values)==650 and len({r[0] for r in values})==650
        refs={r[1] for r in values}
        db.register('wanted',pd.DataFrame({'reference_id':sorted(refs)}))
        payloads=db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN wanted USING(reference_id)',[str(s.RAW/'verifact/reference_payloads.parquet')]).fetchall()
        assert len(payloads)==len(refs)==len(dict(payloads))
    payloads=dict(payloads)
    assert all(s.pilot.digest_text(text)==key for key,text in payloads.items())
    predictions=[]
    link={}
    for pid,ref,label,model,rater in values:
        assert model=='R1-70B' and rater==cfg['rater_alias']
        predictions.append(dict(proposition_id=pid,verdict=label))
        link[pid]=ref
    # Independent comparison to 002 exported baseline predictions on exactly these IDs.
    exported=[]
    for author in ('llm','human'):
        exported+=s.pilot.read_csv(s.ROOT/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv')[1]
    assert {x['proposition_id']:x['verdict'] for x in predictions}=={x['proposition_id']:x['verdict'] for x in exported if x['proposition_id'] in ids}
    prompts=s.read_json(s.PRIOR/'preparation/judge_prompts.json')
    inputs,jobs,assignments=[],{},[]
    for row in cohort:
        pid=row['proposition_id']
        old=oldinputs[pid]
        assert old['text']==props[pid]['text']
        assert old['subject_id']==row['subject_id']==s.pilot.integer_id(props[pid]['subject_id'])
        assert row['hadm_id']==s.pilot.integer_id(props[pid]['hadm_id']) and row['invalid']=='False' and row['proposition_type']=='claim'
        refs=dict(verifact_reference=payloads[link[pid]],c48_reference=old['retrieval']['C48']['reference'])
        item={k:old[k] for k in ('case_id','proposition_id','subject_id','author_type','text','admission')}
        item.update(reference_id=link[pid],reference_rater_alias=cfg['rater_alias'],references=refs,
            previous_c48_body_sha256=old['retrieval']['C48']['body_sha256'],previous_c48_request_id=old['retrieval']['C48']['request_id'])
        for arm,ref in refs.items():
            nums=s.pilot.reference_numbers(ref)
            assert nums and nums==list(range(1,len(nums)+1))
            body=s.judge_body(item,ref,prompts)
            digest=s.pilot.fingerprint(body)
            if arm=='c48_reference':
                assert digest==item['previous_c48_body_sha256']
            rid='judge:'+digest
            jobs[rid]=dict(request_id=rid,kind='chat',body=body)
            assignments.append(dict(case_id=item['case_id'],proposition_id=pid,arm=arm,request_id=rid,body_sha256=digest))
        inputs.append(item)
    repeats=[]
    for sid in patients:
        for author in ('llm','human'):
            item=min([x for x in inputs if x['subject_id']==sid and x['author_type']==author],key=lambda x:s.pilot.digest_text('010/repeat/v1:'+x['proposition_id']))
            for arm in s.METHODS:
                a=next(a for a in assignments if a['proposition_id']==item['proposition_id'] and a['arm']==arm)
                rid='repeat:'+arm+':'+item['proposition_id']
                jobs[rid]=dict(request_id=rid,kind='chat',body=jobs[a['request_id']]['body'])
                repeats.append(dict(a,canonical_request_id=a['request_id'],request_id=rid))
    ordered=sorted(jobs.values(),key=lambda j:s.pilot.digest_text('010/request-order/v1:'+j['request_id']))
    # Conservative practical planning, not an exact tokenizer or total-byte upper bound.
    estimated=sum((sum(len(m['content']) for m in j['body']['messages'])*.4*3+400*9)/1e6 for j in ordered)
    out=s.OUT/'preparation_001'
    out.mkdir(parents=True,exist_ok=False)
    (out/'cohort.csv').write_bytes(cohort_path.read_bytes())
    s.pilot.write_jsonl(out/'inputs.jsonl',inputs)
    s.pilot.write_csv(out/'released_predictions.csv',sorted(predictions,key=lambda x:x['proposition_id']))
    s.pilot.write_jsonl(out/'jobs.jsonl',ordered)
    s.pilot.write_csv(out/'assignments.csv',assignments)
    s.pilot.write_json(out/'repeats.json',repeats)
    s.pilot.write_json(out/'judge_prompts.json',prompts)
    metrics={'released_system':s.evaluate_separately(cohort,predictions)}
    for method in ('A48','C48'):
        p=s.pilot.read_csv(s.PRIOR/'analysis_001'/('predictions_'+method+'.csv'))[1]
        metrics['009_'+method]=s.evaluate_separately(cohort,p)
    s.pilot.write_json(out/'system_reference_metrics.json',metrics)
    metadata=dict(configuration=cfg,model_metadata=[r for r in s.pilot.read_csv(s.RAW/'verifact/model_metadata.csv')[1] if r['model']=='R1-70B'],
        raw_sha256=raw_hashes,release_predictions_match_002_export=True,no_reference_is_doctor_gold=True)
    s.pilot.write_json(out/'release_binding.json',metadata)
    summary=dict(claims=650,patient_ids=patients,authors=dict(Counter(r['author_type'] for r in cohort)),logical_conditions=1300,
        new_requests=len(ordered),repeat_requests=len(repeats),canonical_requests=len(ordered)-len(repeats),
        estimated_peak_cny=estimated,cap_cny=40,old_judge_answers_reused_in_primary=False,
        references={arm:dict(mean_characters=statistics.mean(len(x['references'][arm]) for x in inputs),max_characters=max(len(x['references'][arm]) for x in inputs),
            mean_blocks=statistics.mean(len(s.pilot.reference_numbers(x['references'][arm])) for x in inputs)) for arm in s.METHODS},
        experiment='as-produced full references; same Judge, unequal evidence content/length/format, not a pure packaging ablation')
    s.pilot.write_json(out/'summary.json',summary)
    deps=[cohort_path,s.PRIOR/'judge_preparation/manifest.json',s.PRIOR/'analysis_001/manifest.json']+[s.RAW/n for n in raw_names]
    s.seal(out,deps,[Path(__file__),s.TASK/'alignment_common.py'])
    print(s.pilot.canonical(summary))
    print(s.pilot.canonical({m:{a:{k:v[k] for k in ('n','percent_agreement','gwet_ac1','mcc')} for a,v in aa.items()} for m,aa in metrics.items()}))


if __name__=='__main__':
    prepare()
