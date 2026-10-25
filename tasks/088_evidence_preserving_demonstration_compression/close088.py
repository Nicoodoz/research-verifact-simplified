"""Close the pre-registered input-equivalence branch without target inference."""
from collections import Counter
import subprocess,unittest
from common088 import *
import api088 as api
import construct088 as build
import test088

def main():
    templates=read(OUT/'templates.json');original=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl')
    demos=read(OUT/'demonstrations.json');summary=read(OUT/'construction_summary.json');units=read(OUT/'source_units.json')
    cf=read(OUT/'constructor_freeze.json');df=read(OUT/'demonstration_freeze.json')
    checks=[]
    def ok(v,name):
        if not v:raise AssertionError(name)
        checks.append(name)
    for rel,digest in cf['sources'].items():ok(sha(ROOT/rel)==digest,'constructor_sources_frozen')
    for rel,digest in df['files'].items():ok(sha(OUT/rel)==digest,'demonstration_artifacts_frozen')
    ok(templates['systems']['P4']==templates['systems']['Q4']==templates['systems']['F4'],'three_systems_byte_identical')
    ok(not templates['measurable'],'pre_registered_stop_condition')
    ok(templates['systems']['F4']==read(ROOT/'outputs/087_f4_evidence_intervention/templates.json')['systems']['F4'],'original_F4_exact')
    ok(all([x['proposition_id'] for x in demos[a]]==[x['proposition_id'] for x in original] for a in ARMS),'identities_fixed')
    for a in ARMS:
        for i,x in enumerate(demos[a]):
            old=original[i];src=units[old['proposition_id']]
            ok(x['claim']==old['claim'] and x['physician_label']==old['physician_label'] and x['sid']==old['sid'],'claim_label_patient_fixed')
            ok(x['reference']==old['reference'],'original_reference_retained')
            ids=build.all_ids(src) if a=='F4' else summary[i][a]['selected_ids']
            ok(source_check(old['reference'],src,ids,x['reference']),'source_verbatim_order_metadata')
    for ex in original:
        src=units[ex['proposition_id']]
        for u in src['units']:
            ok(ex['reference'][u['start']:u['end']]==u['text'],'unit_offsets_and_full_text')
            ok(h(u['text'])==u['sha256'],'unit_sha')
    rows,success,counts=api.state();ok(len(rows)==len(success)==2,'only_two_constructor_calls')
    ledger=[]
    for x in rows:
        req=read(ROOT/x['request_source']);receipt=read(ROOT/x['receipt_source']);tr=receipt['transport'];body=req['job']['body']
        ok(receipt['request_sha256']==sha(ROOT/x['request_source']),'receipt_binding')
        ok(x['phase']=='construct' and x['arm']=='P4','no_main_or_review_Q_calls')
        ok(x['created_utc']>=cf['created_utc'],'call_after_constructor_freeze')
        ok(body['model']==BUILDER and body['enable_thinking'] is False and body['max_tokens']==3000 and body['temperature']==0,'constructor_model_parameters')
        ok(len(canonical(body).encode())+2000<128000,'within_Qwen_first_price_tier')
        native=json.loads(tr['body_text']);payload=json.loads(body['messages'][1]['content'])
        ok(native['model']==BUILDER,'returned_exact_snapshot')
        ok(payload['physician_label']==next(z['physician_label'] for z in original if z['proposition_id']==x['id']),'training_label_only')
        obj=json.loads(native['choices'][0]['message']['content']);ok(obj['preserve_full'] is True,'actual_original_retention_decision')
        ok(req['reserved_cny']>=x['cost_or_unknown_cny'],'cost_within_reserved_bound')
        ledger.append({**x,'usage':native['usage'],'returned_model':native['model'],'finish_reason':native['choices'][0]['finish_reason'],
                       'elapsed_seconds':tr['client_elapsed_seconds'],'original_price_cny':api.charge(req,tr)})
    total=sum(x['original_price_cny'] for x in ledger);ok(total<=2 and total<=20,'construction_and_total_cap')
    ok(all(x==1 for x in counts.values()),'no_retries_or_success_repeats')
    ok(not (OUT/'main_freeze.json').exists() and not (OUT/'main_jobs.jsonl').exists(),'no_phantom_target_freeze')
    # Verify reusable target-body invariance with synthetic content, without reading target patients.
    template=dict(model=MODEL,messages=[dict(role='system',content=''),dict(role='user',content='')],temperature=0,
                  max_tokens=8192,enable_thinking=True,reasoning_effort='high',response_format=dict(type='json_object'))
    bodies={a:make_body(template,templates['systems'][a],'synthetic target claim','synthetic target reference') for a in ARMS}
    ok(len({h(canonical(v)) for v in bodies.values()})==1,'same_target_three_request_bodies_identical')
    ok(all(json.loads(x['messages'][1]['content'])==dict(proposition='synthetic target claim',reference='synthetic target reference') for x in bodies.values()),'target_unchanged')
    suite=unittest.defaultTestLoader.loadTestsFromModule(test088)
    result=unittest.TestResult();suite.run(result);ok(result.wasSuccessful(),'eight_offline_unit_tests')
    cost=dict(cap_original_cny=20,constructor_cap_cny=2,total_original_or_unknown_cny=total,
              by_phase_cny=dict(construct=total,review=0,main=0),attempts=2,http200=2,retries=0,unknown_reserved_cny=0,
              input_tokens=sum(x['usage']['prompt_tokens'] for x in ledger),output_tokens=sum(x['usage']['completion_tokens'] for x in ledger),
              price_input=.2,price_output=2,price_source='https://help.aliyun.com/zh/model-studio/qwen3-5-flash',discounts_ignored=True,
              deployment_fee_saving_vs_F4=0,amortization_note='Same final prompt; no main inference measured. One-time constructor cost/n is pure additional cost.',
              amortized_constructor_cny_per_case={str(n):total/n for n in (100,1000,10000)})
    putl(OUT/'attempt_ledger.jsonl',ledger);put(OUT/'cost_ledger.json',cost)
    decision=dict(status='STOP_INPUT_EQUIVALENCE_NO_COMPRESSION',created_utc=now(),reason='P4=F4; section 6 explicitly skips uninformative main repeats',
        F4_P4_Q4_system_sha256=h(templates['systems']['F4']),system_chars=templates['chars'],
        reference_chars={a:[len(x['reference']) for x in demos[a]] for a in ARMS},
        target_n=0,target_patients=0,main_calls=0,Q_constructor_calls=0,source_review_calls=0,clinical_performance=None,
        quality_effect='NOT_EVALUATED',P_specific_mechanism='NOT_TESTED',compression_ratio=1.0,
        important_limit='Constructor judgments are not clinical GT and do not prove the source is fundamentally incompressible.',
        no_next_variant=True,default_unchanged=True,API_closed=True)
    put(OUT/'decision.json',decision)
    put(OUT/'selfcheck.json',dict(status='PASS',checks=len(checks),check_counts=dict(Counter(checks)),
         offline_unit_tests=result.testsRun,independent_audit=False,new_main_calls=0,created_utc=now()))
    print(canonical(dict(decision=decision,cost=cost,selfcheck_count=len(checks),offline_tests=result.testsRun)))

if __name__=='__main__':main()
