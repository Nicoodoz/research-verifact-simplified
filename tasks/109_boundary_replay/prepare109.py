"""Reuse106 data/marks and107 source assets; CPU only, never opens a GPU/SSH."""
from collections import Counter,defaultdict
from pathlib import Path
import argparse,shutil,sys
import common109 as c

AMBIGUOUS_TAGS={'ambiguous_terminology','deidentification_ambiguity','reference_ambiguity',
    'ambiguous_attribution','ambiguous_specificity','ambiguous_abbreviation','ambiguous_reference',
    'uncertainty_preserved','clinical_context_required'}

def prepare():
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    config=c.read(c.TASK/'config.json');old=c.ROOT/'outputs/106_label_preparation'
    index=c.rows(old/'data_pool_index.jsonl');assert len(index)==3675
    roles=c.read(c.ROOT/'outputs/103_lora_selection/patient_roles.json')['patients'];allowed=set(map(str,roles['train']))
    assert len(allowed)==40 and not allowed&set(map(str,roles['selection']+roles['confirmation']))
    source=c.ROOT/'.local_models/107_support_aux/5090/evidence/results_run/train/label_only'
    pointer=c.read(source/'resume.json');complete=c.read(source/pointer['slot']/'checkpoint_complete.json');done=c.read(source/'training_done.json')
    if pointer['step']!=50 or pointer['consumed']!=392 or pointer['fingerprint']['arm']!='label_only' or complete['has_aux_head']:raise ValueError('107 final label_only source required')
    adapter=source/pointer['slot']/'adapter_model.safetensors'
    if c.sha(adapter)!=c.SOURCE_ADAPTER_SHA or complete['files']['adapter_model.safetensors']!=c.SOURCE_ADAPTER_SHA:raise ValueError('Source is not the recorded107 final label_only adapter')
    train107=c.rows(c.ROOT/'.local_models/107_support_aux/gpu_bundle_5090_run/data/train/label_only.jsonl')
    source_ids={r['id'] for r in train107}
    ordinary_ids={r['id'] for r in c.rows(old/'data_ordinary_sample_manifest.jsonl')}
    boundary_ids={r['id'] for r in c.rows(old/'data_boundary_cover_manifest.jsonl')};union=ordinary_ids|boundary_ids
    # Use the already checked training-only source; do not reread raw EHR/GT archives.
    raw={}
    with (c.ROOT/'.local_models/103_lora_selection/eligible.jsonl').open(encoding='utf-8-sig') as stream:
        import json
        for line in stream:
            row=json.loads(line)
            if row['role']=='train':
                if str(row['sid']) not in allowed:raise ValueError('Unexpected training patient')
                raw[row['id']]=row
    if set(raw)!={r['id'] for r in index}:raise ValueError('106 training pool identity changed')
    explicit={r['id'] for r in c.rows(old/'data_isolation.jsonl')}|{r['id'] for r in c.rows(old/'data_additional_isolation.jsonl')}
    pair_flags=set()
    for pair in c.rows(old/'semantic_training_pairs.jsonl'):
        for side,status in [('S',pair['S_input_status']),('nonS',pair['nonS_input_status'])]:
            if any(word in status for word in ('ambiguity','not_identified','reference_gap','not_identifiable')):pair_flags.add(pair['ids'][side])
    excluded=[];eligible=[]
    for m in index:
        reasons=[]
        if m['id'] in explicit or m['semantic104_status']=='reference_gap':reasons.append('known_actual_input_gap_104_106')
        if m['semantic104_status']=='unresolved':reasons.append('unresolved104_not_promoted_by_current_error')
        if AMBIGUOUS_TAGS.intersection(m['issue_tags104']):reasons.append('known_ambiguity_tags')
        if m['id'] in pair_flags:reasons.append('106_actual_training_pair_review_uncertain')
        if reasons:excluded.append(dict(id=m['id'],sid=m['sid'],GT=m['GT'],reasons=reasons))
        else:eligible.append(m)
    duplicates=defaultdict(list)
    for m in eligible:duplicates[(str(m['sid']),m['claim_sha256'],m['reference_sha256'])].append(m)
    meta={}
    for key,group in duplicates.items():
        if len({m['GT'] for m in group})>1:
            excluded.extend(dict(id=m['id'],sid=m['sid'],GT=m['GT'],reasons=['identical_patient_input_conflicting_original_GT_no_relabel']) for m in group);continue
        ordered=sorted(group,key=lambda m:(m['id'] not in source_ids,m['id']))
        for m in ordered[1:]:excluded.append(dict(id=m['id'],sid=m['sid'],GT=m['GT'],reasons=['duplicate_actual_input_keep_one_original_ID']))
        m=dict(ordered[0]);m.update(eligible_109=True,prompt_token_sha256=m['input_token_sha256']);meta[m['id']]=m
    stage_a=sorted((i for i,m in meta.items() if i in union|source_ids and m['GT']!='Supported'),key=lambda i:(meta[i]['input_tokens'],i))
    # Same cheap106 lexical representation; no new claim-only classifier or labels.
    ids=sorted(meta);vectorizer=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),min_df=2,max_features=30000,dtype=np.float32)
    features=vectorizer.fit_transform([raw[i]['claim'] for i in ids]);position={i:j for j,i in enumerate(ids)}
    supported=defaultdict(list)
    for i in ids:
        if meta[i]['GT']=='Supported':supported[str(meta[i]['sid'])].append(i)
    neighbors={};minimum=config['selection']['minimum_lexical_similarity']
    for i in stage_a:
        peers=supported[str(meta[i]['sid'])];values=(features[position[i]]@features[[position[j] for j in peers]].T).toarray()[0]
        ranked=sorted(zip(peers,values),key=lambda item:(-float(item[1]),item[0]))
        neighbors[i]=[dict(id=j,similarity=float(s),selection_proxy_only=True) for j,s in ranked if s>=minimum][:3]
    source_eligible=sorted(source_ids&set(meta));packed=set(stage_a)|{i for i in source_eligible if meta[i]['GT']=='Supported'}|{n['id'] for values in neighbors.values() for n in values}
    sys.path.insert(0,str(c.ROOT/'tasks/104_supervision_evidence'));from training104 import messages,canonical
    pool=[]
    for i in sorted(packed):
        original=raw[i];m=meta[i]
        if original['GT']!=m['GT'] or str(original['sid'])!=str(m['sid']):raise ValueError('106 original GT/patient mismatch')
        if c.digest(original['claim'])!=m['claim_sha256'] or c.digest(original['reference'])!=m['reference_sha256']:raise ValueError('Own original clinical input changed')
        answer=canonical(dict(verdict=m['GT']))
        pool.append(dict(id=i,sid=m['sid'],author=m['author'],GT=m['GT'],role='train',claim=original['claim'],
            reference=original['reference'],reference_id=original['reference_id'],reference_sha256=m['reference_sha256'],
            claim_sha256=m['claim_sha256'],messages=messages(original['claim'],original['reference']),answer=answer,answer_text=answer))
    c.putl(c.PRIVATE/'data/pool.jsonl',pool);c.putl(c.PRIVATE/'data/pool_metadata.jsonl',[meta[i] for i in sorted(packed)])
    c.put(c.PRIVATE/'data/neighbors.json',neighbors);c.put(c.PRIVATE/'data/source_ids.json',source_eligible);c.put(c.PRIVATE/'data/stage_a_ids.json',stage_a)
    baseline=[r for r in c.rows(c.ROOT/'outputs/107_support_aux/predictions_sanitized.jsonl') if r['arm']=='label_only']
    if len(baseline)!=500 or set(r['id'] for r in baseline)&set(meta):raise ValueError('Evaluation/training leakage')
    c.putl(c.PRIVATE/'data/baseline107.jsonl',baseline)
    for src,dst in [('data/eval_inputs.jsonl','data/eval_inputs.jsonl'),('frozen/eval_token_lengths.jsonl','frozen/eval_token_lengths.jsonl'),('frozen/eval_batches.json','frozen/eval_batches.json')]:
        target=c.PRIVATE/dst;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/'.local_models/107_support_aux/gpu_bundle_5090_run'/src,target)
    # Carry only the active source slot, preserving the immutable old107 checkpoint.
    checkpoint=c.PRIVATE/'source107';checkpoint.mkdir(exist_ok=True)
    for name in ('resume.json','training_done.json'):shutil.copyfile(source/name,checkpoint/name)
    folder=checkpoint/pointer['slot'];folder.mkdir(exist_ok=True)
    for name in complete['files']:shutil.copyfile(source/pointer['slot']/name,folder/name)
    shutil.copyfile(source/pointer['slot']/'checkpoint_complete.json',folder/'checkpoint_complete.json')
    modeldir=c.ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b'
    sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'));from tokenizer_cpu105 import CPUPinnedTokenizer
    from data105 import encode
    tokenizer=CPUPinnedTokenizer(modeldir);by={r['id']:r for r in pool}
    checks=set(max(packed,key=lambda i:meta[i]['input_tokens']) for _ in [0])
    checks.update(next(i for i in sorted(packed) if meta[i]['GT']==g) for g in c.LABELS)
    for i in checks:
        encoded=encode(tokenizer,by[i])
        if encoded['prompt_tokens']!=meta[i]['input_tokens'] or encoded['prompt_token_sha256']!=meta[i]['input_token_sha256']:raise ValueError('Reused106 token cache differs from original105/107 interface')
    current_eval={r['id'] for r in baseline};current_training=set(meta);intersection=current_eval&current_training
    source_receipt=dict(source_task=107,source_arm='label_only',step=50,consumed=392,
        final_slot=pointer['slot'],adapter_sha256=c.SOURCE_ADAPTER_SHA,adapter_bytes=adapter.stat().st_size,
        full_optimizer_state_bytes=(source/pointer['slot']/'training_state.pt').stat().st_size,
        full_optimizer_local=True,source_fingerprint=pointer['fingerprint'],source_adapter_hash_checked_once=True,
        original_backup_receipt_reused='outputs/107_support_aux/backup_receipt.json',base_weights_local=False,
        baseline500_cache_N=500,current_checkpoint_train_pool_predictions_N=0,
        training_intersection_with_baseline500=len(intersection),R1_TFIDF_105_108_not_accepted_as_current_predictions=True)
    c.put(c.OUT/'source_assets.json',source_receipt)
    c.putl(c.OUT/'exclusions.jsonl',excluded)
    manifest=[dict(id=i,sid=meta[i]['sid'],GT=meta[i]['GT'],author=meta[i]['author'],
        input_tokens=meta[i]['input_tokens'],prompt_token_sha256=meta[i]['input_token_sha256'],
        semantic104_status=meta[i]['semantic104_status'],eligible_109=True,role='train',
        candidate_use='mining_nonS' if i in stage_a else 'possible_S_prediction_not_yet_requested',
        original107=i in source_ids,ordinary106=i in ordinary_ids,boundary106=i in boundary_ids) for i in sorted(packed)]
    c.putl(c.OUT/'candidate_manifest.jsonl',manifest)
    summary=dict(task=109,preparation_only=True,original_training_pool_N=3675,training_patients=40,
        original_pool_GT=dict(Counter(r['GT'] for r in index)),union106_candidate_N=len(union),
        eligible_after_marks_dedup_N=len(meta),excluded_N=len(excluded),exclusion_reasons=dict(Counter(r for x in excluded for r in x['reasons'])),
        stage_a_N=len(stage_a),stage_a_GT=dict(Counter(meta[i]['GT'] for i in stage_a)),
        stage_a_prompt_tokens=sum(meta[i]['input_tokens'] for i in stage_a),
        packed_patients=len({meta[i]['sid'] for i in packed}),stage_a_patients=len({meta[i]['sid'] for i in stage_a}),
        stage_b_max_N=3*64+len([i for i in source_eligible if meta[i]['GT']=='Supported']),
        packed_N=len(packed),packed_GT=dict(Counter(meta[i]['GT'] for i in packed)),
        source107_eligible_GT=dict(Counter(meta[i]['GT'] for i in source_eligible)),
        possible_max_prompt_tokens=max(meta[i]['input_tokens'] for i in packed),
        required_context_tokens=max(max(meta[i]['input_tokens'] for i in packed)+384,13097),
        possible_max_training_tokens=max(meta[i]['input_tokens'] for i in packed)+9,
        stage_a_without_lexical_neighbors=sum(not neighbors[i] for i in stage_a),
        direct_tokenization_smoke_N=len(checks),reused106_full_pool_token_cache=True,
        actual_current_checkpoint_training_predictions_available=False,hard_examples_selected=False,
        selected_train_file_created=False,training_size_if_gates_pass=192,
        candidate_is_certified_clinical_pair=False,confirmation40_used=False,
        new_GPU_calls=0,new_paid_API_cny=0,original_GT_and_reference_changed=False)
    c.put(c.OUT/'data_summary.json',summary);c.put(c.PRIVATE/'data_summary.json',summary)
    c.put(c.PRIVATE/'frozen/tokenizer109.json',dict(tokenizer_files=c.read(c.ROOT/'outputs/107_support_aux/tokenizer_summary.json')['tokenizer_files'],required_context_tokens=summary['required_context_tokens']))
    print(c.canonical(summary))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args();prepare()
