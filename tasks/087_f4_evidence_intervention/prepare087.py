"""Read only development input archives, select without GT/scores, freeze all jobs."""
import collections, difflib, statistics, subprocess
from common087 import *

def main():
    if OUT.exists():raise FileExistsError('087 already prepared')
    sources={}
    def source(rel,kind='json'):
        p=ROOT/rel;sources[rel]=sha(p)
        return lines(p) if kind=='jsonl' else read(p)
    split=source('outputs/079_f4_priorg_adaptation/freeze.json')
    evalp=set(split['eval_patients'])
    priorp=set(source('outputs/051_thinking_mode_validation/freeze.json')['patient_pool'])
    examples=source('outputs/071_judge_icl_feasibility/examples.jsonl','jsonl')
    demop={x['sid'] for x in examples}
    teachp=set(source('outputs/071_judge_icl_feasibility/freeze.json')['training_patients'])
    assert len(evalp)==22 and not evalp&(priorp|demop)
    semantics=source('outputs/085_r1_70b_model_swap/prompt_semantics.json')
    base=semantics['B_system_content'];app=semantics['F4_appendix_exact']
    header=app[:app.index('{"physician_label"')]
    systems={a:render(base,header,examples,a) for a in ARMS}
    assert systems['F4']==semantics['F4_system_content']
    assert len(systems['X4'])==len(systems['F4'])
    template=next(x['body'] for x in source('outputs/053_thinking_prior_validation/main_jobs.jsonl','jsonl') if x['condition']=='T-S')
    assert template['messages'][0]['content']==base
    broad=source('outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl','jsonl')
    broad=[x for x in broad if x['subject_id'] in evalp]
    assert len(broad)==2034
    clean={x['id'] for x in source('outputs/084_f4_coverage_validation/eligible_blind.jsonl','jsonl')}
    # A compact index of exact previous requests, without reading results or GT.
    cache=collections.defaultdict(list); scanned=0
    for folder in sorted((ROOT/'outputs').iterdir()):
        if not folder.is_dir() or not folder.name[:3].isdigit() or not 51<=int(folder.name[:3])<=86:continue
        if folder.name.startswith('085'):continue
        for p in sorted(folder.rglob('request.json')):
            q=read(p);body=q.get('body') or q.get('job',{}).get('body')
            if not isinstance(body,dict) or body.get('model')!=MODEL:continue
            msgs=body.get('messages',[])
            if not msgs or msgs[0].get('content') not in (systems['B'],systems['F4']):continue
            scanned+=1;cache[h(canonical(body))].append(p.relative_to(ROOT).as_posix())
    exposures=collections.defaultdict(list)
    rels=['outputs/066_oracle_headroom/error_cases.jsonl','outputs/067_conservative_evidence_packing/cases_blind.jsonl',
          'outputs/067_conservative_evidence_packing/cases_blind_v2.jsonl','outputs/068_final_pack_utility_diagnosis/diagnostic_cases.jsonl',
          'outputs/068_final_pack_utility_diagnosis/diagnostic_v2_cases.jsonl','outputs/069_final_pack_controlled_repair/stage1_final_cases.jsonl',
          'outputs/070_fixed_evidence_reasoning_diagnosis/all_cases.jsonl','outputs/081_gt_blind_evidence_selection/sample_blind.jsonl',
          'outputs/071_judge_icl_feasibility/evaluation_blind.jsonl','outputs/072_adaptive_judge_examples/target_blind.jsonl',
          'outputs/073_clinical_example_matching/target_blind.jsonl','outputs/074_anchor_dynamic_examples/target_blind.jsonl',
          'outputs/075_annotated_static_examples/target_blind.jsonl','outputs/084_f4_coverage_validation/sample_blind.jsonl',
          'outputs/086_global_demonstration_selection/E_cases_blind.jsonl']
    for rel in rels:
        if (ROOT/rel).exists():
            for x in source(rel,'jsonl'):
                pid=x.get('id') or x.get('proposition_id')
                if pid:exposures[pid].append(rel)
    bysid=collections.defaultdict(list);inventory=[]
    for x in broad:
        pid=x['proposition_id'];sid=x['subject_id']
        historical={a:cache.get(h(canonical(make_body(template,systems[a],x['text'],x['reference']))),[]) for a in ('B','F4')}
        tier=0 if not any(historical.values()) and pid in clean else 1 if not any(historical.values()) else 2
        row=dict(id=pid,sid=sid,author=x['author_type'],claim=x['text'],reference=x['reference'],
                 reference_sha256=h(x['reference']),fallback_U2=LABELS[x['u2']],
                 prior_exact_requests=historical,selection_tier=tier,
                 prior_target_exposure=exposures[pid],teaching_candidate_patient_overlap=sid in teachp)
        bysid[sid].append(row)
    chosen={}
    for sid in sorted(evalp):
        ordered=sorted(bysid[sid],key=lambda x:(x['selection_tier'],h('087/sample/v1:'+x['id']),x['id']))
        chosen[sid]=ordered[:5];assert len(chosen[sid])==5
        inventory.append(dict(sid=sid,legal=len(ordered),tier_counts=dict(collections.Counter(x['selection_tier'] for x in ordered)),
                              chosen_tiers=[x['selection_tier'] for x in chosen[sid]],teaching_candidate_patient_overlap=sid in teachp))
    sample=[];jobs=[]
    for rank in range(5):
        for sid in sorted(evalp,key=lambda s:h('087/patient-order/v1:'+s)):
            x=chosen[sid][rank];x['patient_rank']=rank+1;sample.append(x)
            for arm in sorted(ARMS,key=lambda a:h('087/arm-order/v1:'+x['id']+a)):
                body=make_body(template,systems[arm],x['claim'],x['reference'])
                jobs.append(dict(id=x['id'],sid=sid,arm=arm,body=body,body_sha256=h(canonical(body)),request_id=f"087_{arm}_{x['id']}"))
    assert len(sample)==110 and len(jobs)==440
    # Historical actual usage; estimate prompt tokens from each arm's actual UTF8 length.
    history=source('outputs/084_f4_coverage_validation/new_predictions.jsonl','jsonl')
    # Scores are present in this historical file but never enter selection above or this cost-only projection.
    averages={a:{k:statistics.mean(x['arms'][a]['usage'][k] for x in history) for k in ('prompt_tokens','completion_tokens')} for a in ('B','F4')}
    oldjobs=source('outputs/084_f4_coverage_validation/main_jobs.jsonl','jsonl')
    oldbytes={a:statistics.mean(len(canonical(j['body']).encode()) for j in oldjobs if j['arm']==a) for a in ('B','F4')}
    forecast={}
    for a in ARMS:
        parent='B' if a in ('B','CL4') else 'F4'
        newbytes=statistics.mean(len(canonical(j['body']).encode()) for j in jobs if j['arm']==a)
        inp=averages[parent]['prompt_tokens']*newbytes/oldbytes[parent]
        # CL4 unseen output length conservatively uses larger B/F4 historical mean.
        out=max(v['completion_tokens'] for v in averages.values()) if a=='CL4' else averages[parent]['completion_tokens']
        forecast[a]=dict(input_tokens_mean_estimate=inp,output_tokens_mean_estimate=out,original_cny=110*(3*inp+9*out)/1e6)
    total=sum(x['original_cny'] for x in forecast.values());assert total<=17.0
    OUT.mkdir()
    putl(OUT/'sample_blind.jsonl',sample);putl(OUT/'jobs.jsonl',jobs)
    put(OUT/'templates.json',dict(systems=systems,header=header,example_ids=[x['proposition_id'] for x in examples],
                                 system_hashes={a:h(v) for a,v in systems.items()},system_chars={a:len(v) for a,v in systems.items()}))
    diff=''.join(difflib.unified_diff(systems['F4'].splitlines(True),systems['CL4'].splitlines(True),fromfile='F4',tofile='CL4'))
    diff+='\n'+''.join(difflib.unified_diff(systems['F4'].splitlines(True),systems['X4'].splitlines(True),fromfile='F4',tofile='X4'))
    text(OUT/'template_changes.diff',diff)
    put(OUT/'reference_permutation.json',dict(permutation_one_based=[i+1 for i in PERMUTATION],
        slots=[dict(slot=i+1,claim_id=ex['proposition_id'],label=ex['physician_label'],
                    original_reference_sha256=h(ex['reference']),new_reference_sha256=h(examples[PERMUTATION[i]]['reference']),
                    original_reference_sid=ex['sid'],new_reference_sid=examples[PERMUTATION[i]]['sid']) for i,ex in enumerate(examples)],
        reference_multiset_unchanged=True,X4_is_artificial_diagnostic_not_clinician_labeled_pair=True))
    put(OUT/'coverage.json',dict(patients=inventory,scanned_exact_template_requests=scanned,eval_patients=sorted(evalp),
        prior_source_patients=sorted(priorp),actual_demo_patients=sorted(demop),historical_teaching_pool=sorted(teachp),
        chosen_tier_counts=dict(collections.Counter(x['selection_tier'] for x in sample)),selection_used_GT=False))
    put(OUT/'budget.json',dict(cap=20,forecast=forecast,total_forecast=total,length_retry_unknown_buffer=20-total,
        historical_mean_usage=averages,price_source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',
        checked_utc=now(),input_original_cny_per_million=3,output_original_cny_per_million=9,
        ignored_cache_and_offpeak_discounts=True,max_workers=8,max_attempts_per_job=3))
    sources.update({p.relative_to(ROOT).as_posix():sha(p) for p in TASK.glob('*.py')})
    sources['tasks/087_f4_evidence_intervention/protocol.md']=sha(TASK/'protocol.md')
    sources['docs/087_Codex_F4证据信息干预与紧凑示范验证_执行提示词.md']=sha(ROOT/'docs/087_Codex_F4证据信息干预与紧凑示范验证_执行提示词.md')
    put(OUT/'freeze.json',dict(status='FROZEN_BEFORE_087_API_AND_TARGET_GT',created_utc=now(),n=110,jobs=440,cap=20,
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},sources=sources,
        fallback_rule='032 frozen nonthinking U2, identical per ID in all arms; retain native missing values',
        historical_fallback_alternatives='Retain any old-answer fallback provenance at post-freeze evaluation; never use it for 087',
        target_GT_used_for_sampling=False,previously_exposed_development=True))
    print(canonical(dict(n=110,patients=22,jobs=440,tiers=dict(collections.Counter(x['selection_tier'] for x in sample)),forecast=total,buffer=20-total)))

if __name__=='__main__':main()
