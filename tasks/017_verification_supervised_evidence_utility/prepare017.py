"""Freeze GT-blind sampling/actions before reading labels; no API calls."""
from pathlib import Path
from collections import Counter
import csv
import math
import subprocess
import common017 as c
from selection017 import interventions

def prepare():
    out=c.OUT/'preparation_001';c.require(not out.exists(),'Preparation already frozen')
    allrows,passages,deps=c.sources();order=c.old.baseline.patient_order()
    c.require(set(r['subject_id'] for r in allrows)==set(order[18:30]),'Only exposed12 patients')
    selected=[]
    for sid in order[18:30]:
        for author in ('llm','human'):
            choices=sorted([r for r in allrows if r['subject_id']==sid and r['author_type']==author],key=lambda r:c.rank_id(r['proposition_id']))
            c.require(len(choices)>=8,'Too few cases; no replacement sampling');selected+=choices[:8]
    prompts_path=c.BASES['old6']/'preparation/judge_prompts.json';prompts=c.read(prompts_path)
    jobs={};assign=[];records=[]
    for item in selected:
        arms=interventions(item,passages);records.append(dict(item,interventions=arms))
        for arm,r in arms.items():
            body=c.old.judge_body(item,r['reference'],prompts,'v4_first')
            for repeat in (0,1):
                rid=f'017:headroom:r{repeat}:'+c.fingerprint(body)
                jobs.setdefault(rid,dict(request_id=rid,kind='chat',body=body,proposition_id=item['proposition_id'],case_id=item['case_id']))
                assign.append(dict(proposition_id=item['proposition_id'],case_id=item['case_id'],arm=arm,repeat=repeat,request_id=rid,body_sha256=c.fingerprint(body)))
    out.mkdir(parents=True);c.write_lines(out/'inputs.jsonl',records)
    c.write_lines(out/'jobs.jsonl',sorted(jobs.values(),key=lambda j:c.old.hash_rank(j['request_id'],'017/send/v1:')))
    c.write_csv(out/'assignments.csv',assign);c.write_json(out/'judge_prompts.json',prompts)
    c.write_json(out/'sampling.json',dict(seed='017/GT-blind/patient-author/v1:',claims=192,per_patient_author=8,
        train_patients=order[18:24],selection_patients=order[24:30],GT_read_for_selection=False,
        existing013_GT_enriched231_not_used_as_sampling_frame=True,features=list(c.FEATURES)))
    # Metadata-only future count; no new-patient texts, labels or EHR are inspected.
    future=Counter()
    with (c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['subject_id'] in order[30:] and r['proposition_type']=='claim' and r['invalid']=='False':future[r['subject_id']]+=1
    cal=c.read(c.ROOT/'outputs/016_disagreement_triggered_review_validation/token_calibration_001.json')['models']['v4_first']
    estimates=[(math.ceil(sum(len(m['content']) for m in j['body']['messages'])*cal['input_factor']+200)*3+cal['output_allowance']*9)/1e6 for j in jobs.values()]
    size=[len(r['wide']) for r in selected]
    summary=dict(claims=192,patients=12,authors=dict(Counter(r['author_type'] for r in selected)),logical_calls=len(assign),unique_requests=len(jobs),
        eligible={arm:sum(r['interventions'][arm]['eligible'] for r in records) for arm in c.ARMS},
        any_swap_eligible=sum(any(r['interventions'][arm]['eligible'] for arm in c.SWAPS) for r in records),
        C48_candidates_range=[min(len(r['C48']) for r in records),max(len(r['C48']) for r in records)],wide_candidates_range=[min(size),max(size)],
        stage1_expected_peak_cny=sum(estimates),stage2_additional_API_cny=0,remaining10_metadata_claim_counts=dict(future),
        confirmation_planning_allowance_cny=sum(future.values())*2*max(estimates)+3,
        all_stage_planning_estimate_cny=sum(estimates)+sum(future.values())*2*max(estimates)+3+5,cap_cny=80,
        no_new_rerank_embedding_or_retrieval=True,wide_definition='Saved true-scored A48/B48/C48 union; not013 full top80 union; no score refreshing',
        no_GT_read_before_freeze=True)
    c.write_json(out/'summary.json',summary)
    c.seal(out,deps+[prompts_path,c.OUT/'protocol_001.md',c.ROOT/'outputs/003_error_analysis/patient_groups.json'],[Path(__file__),c.TASK/'common017.py',c.TASK/'selection017.py'])
    # Materialize evaluation labels after the GT-blind preparation has been sealed.
    c.write_csv(c.OUT/'evaluation_cohort.csv',c.gt_for({r['proposition_id'] for r in selected}))
    c.write_json(c.OUT/'history_before.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),
        files={n:c.file_hash(c.ROOT/n) for n in subprocess.check_output(['git','ls-files','-z'],cwd=c.ROOT).decode().split('\0') if n and (c.ROOT/n).is_file()}))
    print(c.canonical(summary))

if __name__=='__main__':prepare()
