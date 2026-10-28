"""Final executor checks for real 104 data and unchanged historical tracked files."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import common104 as c
import build104 as b
import training104 as t

BASE='42e357f314a928253ed64c54dc45801e6307c1b7'


def main():
    frozen=b.load_frozen_reviews(c.PRIVATE,c.OUT)
    train=c.lines(c.PRIVATE/'train512_original.jsonl');trainmap={r['id']:r for r in train}
    labels=t.load_rows(c.PRIVATE/'paired/label_only.jsonl');briefs=t.load_rows(c.PRIVATE/'paired/evidence_brief.jsonl')
    roles=c.read(c.ROOT/'outputs/103_lora_selection/patient_roles.json')['patients']
    pairs=t.validate_pairs(labels,briefs,set(roles['train']),set(roles['selection'])|set(roles['confirmation']))
    for row in labels+briefs:
        original=trainmap[row['id']]
        assert all(row[k]==original[k] for k in ('id','sid','author','GT','claim','reference','reference_id'))
    manifest=c.read(c.OUT/'paired_manifest.json')
    assert manifest['N']==len(labels) and not manifest['candidate_only']
    for rel,sha in manifest['files'].items():assert c.sha(c.ROOT/rel)==sha,rel
    for name in ('api_audit_freeze.json',):
        for rel,sha in c.read(c.OUT/name)['files'].items():assert c.sha(c.ROOT/rel)==sha,rel
    token=c.read(c.OUT/'token_summary.json')
    assert not token['candidate_only'] and token['input_pair_folder']=='paired'
    assert token['source_files']['label_only_sha256']==c.sha(c.PRIVATE/'paired/label_only.jsonl')
    assert token['source_files']['evidence_brief_sha256']==c.sha(c.PRIVATE/'paired/evidence_brief.jsonl')
    ledger=c.read(c.OUT/'api_cost_ledger.json')
    assert ledger['used_or_reserved_cny']<=20 and ledger['unknown_or_inflight_cny']>=0
    jobs=c.lines(c.PRIVATE/'api_jobs.jsonl');audit=c.lines(c.PRIVATE/'api_quality_reviews.jsonl')
    assert len(jobs)==64 and {r['request_id'] for r in jobs}=={r['request_id'] for r in audit}
    assert len(audit)==len({r['request_id'] for r in audit})
    assert not (c.PRIVATE/'api_run.lock').exists()
    joined=c.lines(c.PRIVATE/'review_joined.jsonl')
    accepted={r['id'] for r in labels}
    assert all(r['initial_status']=='candidate_gt_explained' for r in joined if r['id'] in accepted)
    assert len(joined)==288 and len(train)==512 and len({r['sid'] for r in train})==40
    reviewed={r['id'] for r in joined}
    unreviewed=[r for r in train if r['id'] not in reviewed]
    assert len(unreviewed)==224 and all(r['GT']=='Supported' for r in unreviewed)
    # Check original tracked data/code/results rather than relying on task status.
    diff=subprocess.check_output(['git','diff','--name-only',BASE,'--'],cwd=c.ROOT).decode('utf-8').splitlines()
    allowed={'AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/TASK_INDEX.md','reviews/README.md'}
    assert all(p in allowed or p.startswith(('tasks/104_supervision_evidence/','outputs/104_supervision_evidence/','reviews/104_supervision_evidence/')) for p in diff),diff
    private_paths=[c.PRIVATE/'paired/label_only.jsonl',c.PRIVATE/'paired/evidence_brief.jsonl',c.PRIVATE/'teacher_queue.jsonl',c.PRIVATE/'api_jobs.jsonl']
    for path in private_paths:
        assert subprocess.run(['git','check-ignore','-q',str(path)],cwd=c.ROOT).returncode==0
    tests=c.read(c.OUT/'test_results.json')
    assert tests['passed'] and tests['tests']==35
    result=dict(status='PASS',executor_selfcheck_not_independent_audit=True,base_main_HEAD=BASE,
                actual_pair_check=pairs,full_inventory_N=512,semantic_primary_N=len(frozen),
                unreviewed_supported_N=224,final_paired_N=len(labels),final_GT=dict(Counter(r['GT'] for r in labels)),
                no_initial_disagreement_rescued=True,original_GT_and_input_exact=True,
                actual_tokenizer_and_loss_masks_checked=True,tests=tests,
                frozen_API_requests=len(jobs),HTTP200=ledger['HTTP200'],API_used_or_reserved_cny=ledger['used_or_reserved_cny'],
                unknown_or_inflight_cny=ledger['unknown_or_inflight_cny'],API_hard_cap_cny=20,
                duplicate_HTTP200_not_resent=True,new_GPU=0,new_training=0,new_classification_evaluation=0,
                historical_tracked_files_unchanged=True,default_unchanged=True,
                private_training_package_ignored=True,auxiliary_blind_review=c.read(c.OUT/'independent_dispute_summary.json'),
                limitations=['No physician adjudication','No training or classification gain tested','Extra blind subagent review completed 8/16 before usage-limit interruption','Independent engineering review covers its recorded earlier versions; later checks are executor regression tests'])
    c.put(c.OUT/'selfcheck.json',result)
    print(c.canonical(dict(status=result['status'],N=len(labels),cost=ledger['used_or_reserved_cny'])))


if __name__=='__main__':main()
