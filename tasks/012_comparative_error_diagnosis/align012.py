"""Align all three systems; select cases by the prewritten text-blind rule."""
from pathlib import Path
from collections import Counter
import duckdb
import pandas as pd
import argparse
import study012 as s

def choose(rows):
    selected={};counts=Counter();vc=Counter();gc=Counter()
    def add(pool,why):
        pool=[r for r in pool if r['proposition_id'] not in selected]
        if not pool:return
        r=min(pool,key=lambda r:(bool(r['prior_case_membership']),counts[r['subject_id']],vc[(r['author_type'],r['V']==r['human_gt'])],gc[(r['author_type'],r['human_gt'])],s.pilot.digest_text('012/deep/v1:'+r['proposition_id'])))
        selected[r['proposition_id']]=[why];counts[r['subject_id']]+=1;vc[(r['author_type'],r['V']==r['human_gt'])]+=1;gc[(r['author_type'],r['human_gt'])]+=1
    dirs=('old_wrong_new_correct','old_correct_new_wrong','both_wrong','both_correct')
    for author in ('llm','human'):
        for d in dirs:
            pool=[r for r in rows if r['author_type']==author and r['O_to_C']==d]
            for _ in range(min(3,len(pool))):add(pool,'author/O_to_C/'+d)
    for author in ('llm','human'):
        for d in dirs:
            if not any(r['proposition_id'] in selected and r['author_type']==author and r['O_to_V']==d for r in rows):
                add([r for r in rows if r['author_type']==author and r['O_to_V']==d],'supplement author/O_to_V/'+d)
    for sid in sorted({r['subject_id'] for r in rows}):
        for author in ('llm','human'):
            if not any(r['proposition_id'] in selected and r['subject_id']==sid and r['author_type']==author for r in rows):
                add([r for r in rows if r['subject_id']==sid and r['author_type']==author],'supplement patient/author')
    return selected

def align(out):
    for folder in (s.TEN/'preparation_001',s.TEN/'analysis_001'):s.source.check(folder)
    cohort=s.pilot.read_csv(s.TEN/'preparation_001/cohort.csv')[1]
    inp={x['proposition_id']:x for x in s.pilot.jsonl(s.TEN/'preparation_001/inputs.jsonl')}
    assert len(cohort)==len(inp)==650
    assert {r['subject_id'] for r in cohort}==set(s.source.previous.patient_order()[18:24])
    with duckdb.connect() as db:
        db.register('chosen',pd.DataFrame({'proposition_id':list(inp)}))
        data=db.execute('SELECT v.* FROM read_parquet(?) v JOIN chosen USING(proposition_id) WHERE rater_alias=?',[str(s.RAW/'verifact/verdicts.parquet'),'v1.1.0-rater-121']).fetchdf()
    original={r['proposition_id']:r for r in data.where(pd.notna(data),None).to_dict('records')}
    assert len(original)==650
    assignments=s.pilot.read_csv(s.TEN/'preparation_001/assignments.csv')[1]
    responses={r['request_id']:r for r in s.pilot.jsonl(s.TEN/'analysis_001/normalized_responses.jsonl')}
    jobs={j['request_id']:j for j in s.pilot.jsonl(s.TEN/'preparation_001/jobs.jsonl')}
    amap={(a['proposition_id'],a['arm']):a for a in assignments}
    exports={a:{p['proposition_id']:p['verdict'] for p in s.pilot.read_csv(s.TEN/'analysis_001'/('predictions_'+a+'.csv'))[1]} for a in ('verifact_reference','c48_reference')}
    prior={}
    paths=[s.NINE/'review_002/packets.jsonl',s.TEN/'review_002/packets.jsonl',s.ROOT/'outputs/011_evidence_integrity_packaging/pilot_review_001/packets.jsonl']
    for path in paths:
        for r in s.pilot.jsonl(path):
            pid=r.get('input',{}).get('proposition_id',r.get('row',{}).get('proposition_id'))
            prior.setdefault(pid,[]).append(path.relative_to(s.ROOT).as_posix())
    rows=[];full=[]
    for row in cohort:
        pid=row['proposition_id'];item=inp[pid];o=original[pid]
        assert o['reference_id']==item['reference_id']==s.pilot.digest_text(item['references']['verifact_reference'])
        new={};bodies={}
        for arm in ('verifact_reference','c48_reference'):
            a=amap[(pid,arm)];r=responses[a['request_id']];body=jobs[a['request_id']]['body']
            assert r['status']=='success' and r['verdict']==exports[arm][pid]
            assert r['request_sha256']==a['body_sha256']==s.pilot.fingerprint(body)
            user=s.pilot.strict_json(body['messages'][1]['content'])
            assert user==dict(proposition=item['text'],reference=item['references'][arm])
            new[arm]=r;bodies[arm]=body
        verdicts=dict(O=o['verdict'],V=new['verifact_reference']['verdict'],C=new['c48_reference']['verdict'])
        parsed=s.final_json(o['reasoning_final_answer'])
        status='matches' if len(parsed)==1 and parsed[0]['value']['verdict']==o['verdict'] else 'mismatch_or_unparsed'
        r=dict(row,case_id=item['case_id'],text=item['text'],**verdicts,error_union=any(v!=row['human_gt'] for v in verdicts.values()),
            prior_case_membership=prior.get(pid,[]),original_final_output_status=status,
            O_to_V=s.direction(verdicts['O'],verdicts['V'],row['human_gt']),O_to_C=s.direction(verdicts['O'],verdicts['C'],row['human_gt']),V_to_C=s.direction(verdicts['V'],verdicts['C'],row['human_gt']),
            correctness_pattern=''.join('1' if verdicts[a]==row['human_gt'] else '0' for a in s.SYSTEMS),
            semantic_review_status='not_reviewed_in_012',selection_reasons=[],upstream_original_status='unavailable_candidate_logs',causal_attribution='not_from_labels')
        rows.append(r)
        full.append(dict(row=r,input=item,original=o,original_final_json_check=parsed,current_outputs=new,current_bodies=bodies,
            original_input_observability='Claim and actual reference known; no released full serialized request/candidate logs'))
    selected=choose(rows)
    for r in rows:
        if r['proposition_id'] in selected:r['semantic_review_status']='selected_pending_read';r['selection_reasons']=selected[r['proposition_id']]
    summary=dict(claims=650,error_union=sum(r['error_union'] for r in rows),all_three_correct=sum(r['correctness_pattern']=='111' for r in rows),
        authors={a:{pair:dict(Counter(r[pair] for r in rows if r['author_type']==a)) for pair in ('O_to_C','O_to_V','V_to_C','correctness_pattern')} for a in ('llm','human')},
        selected_cases=[r['case_id'] for r in rows if r['proposition_id'] in selected],selected_n=len(selected),
        selected_previously_in_case_packets=sum(bool(r['prior_case_membership']) for r in rows if r['proposition_id'] in selected),
        original_final_output_checks=dict(Counter(r['original_final_output_status'] for r in rows)),zero_api_calls=True)
    out.mkdir(parents=True,exist_ok=False)
    (out/'cohort.csv').write_bytes((s.TEN/'preparation_001/cohort.csv').read_bytes())
    s.pilot.write_csv(out/'ledger.csv',rows)
    s.pilot.write_jsonl(out/'ledger.jsonl',rows)
    s.pilot.write_jsonl(out/'aligned_materials.jsonl',full)
    s.pilot.write_json(out/'selection.json',selected)
    s.pilot.write_json(out/'summary.json',summary)
    s.seal(out,[s.OUT/'protocol_001.md',s.TEN/'preparation_001/manifest.json',s.TEN/'analysis_001/manifest.json',s.RAW/'verifact/verdicts.parquet',*paths],[Path(__file__),s.TASK/'study012.py'])
    print(s.pilot.canonical(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=s.OUT/'alignment_002')
    align(p.parse_args().output)
