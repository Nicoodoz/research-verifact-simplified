"""CPU-only final evidence assembly, historical integrity and public privacy checks."""
from collections import Counter
from pathlib import Path
import json
import subprocess
import common106 as c


def privacy_check():
    forbidden={'claim','reference','full_reference','content','reason','reasoning_chain','exact_text','quote'}
    # These two files use reason for manually checked abstract isolation metadata,
    # not for an LLM's verbatim clinical rationale. Keep all other reason blocked.
    abstract_isolation_files={'data_isolation.jsonl','data_additional_isolation.jsonl'}
    errors=[]
    def inspect(value,path,trail=''):
        if isinstance(value,dict):
            for key,item in value.items():
                abstract_reason=key=='reason' and path.name in abstract_isolation_files
                if key in forbidden and not abstract_reason and isinstance(item,str) and item:
                    errors.append(dict(file=path.name,key=trail+'/'+key))
                inspect(item,path,trail+'/'+key)
        elif isinstance(value,list):
            for item in value:inspect(item,path,trail+'[]')
    for path in c.OUT.glob('*.json*'):
        if path.suffix=='.jsonl':
            for row in c.rows(path):inspect(row,path)
        else:inspect(c.read(path),path)
    # An additional exact-claim scan includes public task code/documents, not
    # merely JSON field names. It emits IDs/file names only, never source text.
    texts={p:p.read_text(encoding='utf-8-sig') for root in (c.TASK,c.OUT) for p in root.iterdir()
           if p.is_file() and p.suffix in {'.py','.md','.json','.jsonl'}}
    source=c.rows(c.PRIVATE/'training_pool.jsonl')+c.rows(c.ROOT/'.local_models/105_brief_supervision/eval_inputs.jsonl')
    claims={r['id']:r['claim'] for r in source if len(r['claim'])>=32}
    for pid,claim in claims.items():
        for path,text in texts.items():
            if claim in text:errors.append(dict(file=path.name,claim_id=pid,kind='verbatim_clinical_claim'))
    if errors:raise ValueError('Public privacy findings: '+c.canonical(errors))
    return dict(public_json_text_keys_checked=True,public_task_code_and_documents_exact_claim_scan=True,
                claim_source_N=len(claims),findings=0,not_a_complete_deidentification_certification=True)


def assemble_semantics():
    dossier={r['id']:r for r in c.rows(c.PRIVATE/'A_source_review_dossiers.jsonl')}
    paths=['semantic_A_natural.jsonl','semantic_A_kept.jsonl','semantic_A_pressure.jsonl']
    records=[r for path in paths for r in c.rows(c.OUT/path)]
    assert len(records)==53 and len({r['id'] for r in records})==53 and set(dossier)=={r['id'] for r in records}
    for row in records:
        d=dossier[row['id']]
        assert all(row[key]==d[key] for key in ('reference_sha256','claim_sha256','GT','before','after','panel'))
        assert c.digest(d['full_reference'])==row['reference_sha256']
        assert (row.get('full_current_reference_read') or row.get('complete_reference_read') or row.get('full_actual_reference_content_read')) is True
        if 'source_spans' in row:
            for span in row['source_spans']:
                assert c.digest(d['full_reference'][span['start']:span['end']])==span['sha256']
        elif 'cited_source_locations' in row:
            for span in row['cited_source_locations']:
                assert span['case_id']==row['id'] and c.digest(d['full_reference'][span['start']:span['end']])==span['sha256']
        else:
            for key in ('decisive_spans','counterevidence_spans'):
                for span in row[key]:
                    for loc in span['occurrences']:
                        assert c.digest(d['full_reference'][loc['start']:loc['end']])==span['quote_sha256']
    b=c.rows(c.OUT/'semantic_B.jsonl')
    assert len(b)==16 and all(r['full_actual_reference_read'] for r in b)
    assert not {r['sid'] for r in b}&{r['sid'] for r in records}
    risk=[r for r in records if 'all_new_false_S' in r['groups']]
    prevent=[r for r in records if 'all_prevented_false_S' in r['groups']]
    assert len(risk)==14 and len(prevent)==1
    c.put(c.OUT/'source_review_coverage.json',dict(
        A_total=53,A_all_new_false_S=14,A_all_prevented_false_S=1,B_total=16,
        A_by_panel=dict(Counter(r['panel'] for r in records)),
        B_by_category=dict(Counter(r['category'] for r in b)),
        all_A_source_hashes_and_spans_verified=True,
        all_A_current_references_completely_read_by_designated_reviewer=True,
        reviewer_assertions_are_not_independent_doctor_gold=True,
        current_service_permission_confirmed_by_user=True,
        clinical_originals_sent_to_web_or_separate_API=False,
        all_clinical_quotes_private=True,
        A_no_training_examples_or_rules=True,
        fixed_training_pairs=3,not_all192_pairs_semantically_validated=True,
        files={path:c.sha(c.OUT/path) for path in paths+['semantic_B.jsonl','semantic_training_pairs.jsonl']}))
    # Update the current public index to point to completed source readings;
    # the original pre-permission private dossier remains a provenance artifact.
    index=c.rows(c.OUT/'label_case_index.jsonl')
    for row in index:row['semantic_review_status']='completed_see_semantic_A_tables_not_doctor_adjudication'
    c.putl(c.OUT/'label_case_index.jsonl',index)
    analysis=c.read(c.OUT/'label_analysis.json')
    analysis['service_permission']='user_confirmed_before_clinical_source_reading'
    analysis['source_review_completed_N']=53
    analysis['new_doctor_adjudication']=False
    analysis.pop('new_semantic_adjudication',None)
    c.put(c.OUT/'label_analysis.json',analysis)


def main():
    assemble_semantics()
    old=c.read(c.ROOT/'outputs/105_brief_supervision/final_selfcheck.json')
    preserved={name:c.sha(c.ROOT/'outputs/105_brief_supervision'/name)==value for name,value in old['files'].items()}
    assert all(preserved.values())
    assert c.sha(c.ROOT/'.local_models/104_supervision_evidence/paired/label_only.jsonl')=='6abf6abb7949e5eca1e316f117c5269ccc87984452822920847cddb37e4008dc'
    for arm in c.ARMS:
        assert c.sha(c.PRIVATE/(arm+'.jsonl'))=='6abf6abb7949e5eca1e316f117c5269ccc87984452822920847cddb37e4008dc'
    assert not c.read(c.TASK/'config.json')['preparation']['GPU_authorized']
    assert c.read(c.OUT/'api_cost_ledger.json')['attempts']==0
    frozen_diff=subprocess.check_output(['git','diff','--name-only','--','tasks/103_lora_selection','tasks/104_supervision_evidence','tasks/105_brief_supervision','outputs/103_lora_selection','outputs/104_supervision_evidence','outputs/105_brief_supervision'],cwd=c.ROOT,text=True).strip()
    assert not frozen_diff
    public=privacy_check()
    package=c.read(c.OUT/'implementation_package.json')
    bundle=Path(package['bundle'])
    assert c.sha(bundle/'manifest.json')==package['manifest_sha256'] and c.sha(package['archive'])==package['archive_sha256']
    for name,value in c.read(bundle/'manifest.json')['files'].items():assert c.sha(bundle/name)==value,name
    assert c.read(bundle/'AUTHORIZATION_REQUIRED.template.json')['explicit_user_gpu_authorization'] is False
    c.put(c.OUT/'final_selfcheck.json',dict(task=106,status='READY_FOR_NEXT_GPU_DECISION',
        objective='preparation_completed_not_GPU_execution_or_method_success',
        executed_new_9b_training=False,new_GPU_calls=0,new_paid_API_calls=0,API_actual_cny=0,
        old105_report_files_unchanged=preserved,old103_104_105_tracked_files_unchanged=True,
        original196_unchanged=True,control_and_candidate_data_byte_identical=True,
        final_experiment='label_mean_vs_globally_normalized_label_sum_same196',
        inactive_data_candidates_each_N=512,clinical_originals_private=True,public_privacy=public,
        independent_clinical_audit=False,method_pass=None,default_upgraded=False,committed=False,pushed=False,
        limitations=['one fixed seed and historically exposed development patients',
                    'GPU gate throughput/memory/full model gradients and outcomes not executed',
                    'candidate may only shift class preference; complete-label MAP differs from greedy',
                    'CPU tests and machine source review do not establish clinical effectiveness'],
        package_manifest_sha256=package['manifest_sha256'],
        files={p.name:c.sha(p) for p in sorted(c.OUT.iterdir()) if p.is_file() and p.name!='final_selfcheck.json'}))
    print(c.canonical(dict(status='READY_FOR_NEXT_GPU_DECISION',historical_files_preserved=True,
                          source_A_N=53,source_B_N=16,public_privacy_findings=0,API_actual_cny=0,GPU_executed=False)))


if __name__=='__main__':main()
