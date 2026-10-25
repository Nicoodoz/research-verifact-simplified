"""Freeze exact F4 plus study-authored, source-anchored teaching notes."""
import copy,re,csv
from collections import Counter
from common075 import *
SOURCES=['outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl','outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl','outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl']
def normalized(s):return re.sub(r'\s+',' ',s).strip()
def main():
 OUT.mkdir(exist_ok=False)
 old=read(ROOT/'outputs/074_anchor_dynamic_examples/freeze.json');ann=annotations();mats={}
 for rel in SOURCES:
  for x in lines(ROOT/rel):
   pid=x['proposition_id']
   if pid not in mats:mats[pid]=dict(id=pid,sid=str(x['subject_id']),author=x['author_type'],claim=x['text'],reference=x['reference'],source=rel)
 used=set()
 for rel in ['outputs/072_adaptive_judge_examples/target_blind.jsonl','outputs/073_clinical_example_matching/target_blind.jsonl','outputs/074_anchor_dynamic_examples/target_blind.jsonl']:
  used|={x['id'] for x in lines(ROOT/rel)}
 targets=[];gold=[];sampling=[]
 for sid in old['pilot_patients']+old['confirmation_patients']:
  for author in ['human','llm']:
   rows=sorted([x for x in mats.values() if x['sid']==sid and x['author']==author and x['id'] not in used and ann[x['id']]['invalid']=='False'],key=lambda x:text_hash('075/sample:'+x['id']))
   chosen=[]
   for label in ['Not Supported','Not Addressed','Supported']:
    match=[x for x in rows if ann[x['id']]['human_gt']==label]
    if match:chosen.append(match[0])
   for x in rows:
    if len(chosen)==3:break
    if x not in chosen:chosen.append(x)
   assert len(chosen)==3,(sid,author,len(chosen))
   targets+=chosen;gold.extend(dict(id=x['id'],sid=sid,GT=ann[x['id']]['human_gt']) for x in chosen)
   sampling.append(dict(sid=sid,author=author,available_by_gt=dict(Counter(ann[x['id']]['human_gt'] for x in rows)),selected_ids=[x['id'] for x in chosen]))
 examples=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl');notes=read(TASK/'annotations075.json');evidence_checks=[]
 for x,n in zip(examples,notes,strict=True):
  assert x['ordinal']==n['example_ordinal'] and x['proposition_id'].startswith(n['proposition_id_prefix'])
  meta=ann[x['proposition_id']];assert meta['initial_agreement']=='3' and all(meta[k]=='False' for k in ['invalid','time_metadata_conflict','second_round_anomaly'])
  assert [meta[k] for k in ['verdict1','verdict2','verdict3']]==[x['physician_label']]*3
  blocks={int(m.group(1)):m.group(2) for m in re.finditer(r'(?ms)^(\d+)\. Date:(.*?)(?=^\d+\. Date:|\Z)',x['reference'])}
  for e in n['evidence']:
   assert e['reference_number'] in blocks
   assert normalized(e['quote']) in normalized(blocks[e['reference_number']]),e
   evidence_checks.append(dict(example_ordinal=n['example_ordinal'],reference_number=e['reference_number'],quote=e['quote'],matched=True,reference_sha256=text_hash(x['reference'])))
 assert not {x['sid'] for x in examples}&{x['sid'] for x in targets}
 assert all(x['sid'] in old['teaching_patients'] for x in examples)
 prefix='\n\n## Clinician-labeled examples from four other patients\nEach example contains a proposition, EHR reference, and physician label. Examples are not evidence about the patient in the actual task. For the actual task use only its supplied reference.\n'
 fixed=prefix+'\n'.join(canonical(dict(proposition=x['claim'],reference=x['reference'],physician_label=x['physician_label'])) for x in examples)+'\n'
 intro='\n## Evidence-grounded explanatory notes for the four examples above\nThese study-authored teaching notes are based on the supplied example references. They are not physician-authored rationales and are not evidence about the actual patient. Each note explains its own example; retain the original task label definitions and required output format for the actual task.\n'
 # Source-only metadata is kept locally; the Judge sees only explanatory content.
 prompt_notes=[{k:v for k,v in n.items() if k!='proposition_id_prefix'} for n in notes]
 suffix=intro+'\n'.join(canonical(n) for n in prompt_notes)+'\n'
 template=next(j['body'] for j in lines(ROOT/'outputs/053_thinking_prior_validation/main_jobs.jsonl') if j['condition']=='T-S')
 jobs=[]
 for t in targets:
  stage='pilot' if t['sid'] in old['pilot_patients'] else 'confirmation'
  b=copy.deepcopy(template);b['messages'][-1]['content']=canonical(dict(proposition=t['claim'],reference=t['reference']))
  f=copy.deepcopy(b);f['messages'][0]['content']+=fixed
  r=copy.deepcopy(f);r['messages'][0]['content']+=suffix
  for arm,body in [('B',b),('F4',f),('R4',r)]:
   h=digest(body);jobs.append(dict(request_id='075_'+stage+'_'+h[:24],stage=stage,id=t['id'],sid=t['sid'],arm=arm,body=body,body_sha256=h))
 jl(OUT/'target_blind.jsonl',targets);jl(OUT/'target_gt.jsonl',gold);jl(OUT/'examples.jsonl',examples);put(OUT/'teaching_notes.json',notes);put(OUT/'annotation_evidence_checks.json',evidence_checks);jl(OUT/'sampling.jsonl',sampling);jl(OUT/'all_arm_jobs.jsonl',jobs)
 pilot=[j for j in jobs if j['stage']=='pilot'];jl(OUT/'pilot_aliases.jsonl',pilot);jl(OUT/'pilot_jobs.jsonl',sorted({j['request_id']:j for j in pilot}.values(),key=lambda j:text_hash('075/order:'+j['request_id'])))
 fallback={x['proposition_id']:x['U2'] for x in csv.DictReader((ROOT/'outputs/034_same_data_comparison/predictions_common.csv').open(encoding='utf-8-sig'))};assert all(t['id'] in fallback for t in targets);put(OUT/'fallback_u2.json',{t['id']:fallback[t['id']] for t in targets})
 summary=dict(target_n=len(targets),gt=dict(Counter(x['GT'] for x in gold)),gt_by_author=dict(Counter(mats[x['id']]['author']+'/'+x['GT'] for x in gold)),pilot_calls=len(pilot),annotation_added_characters=len(suffix),annotation_words=len(suffix.split()),source_quotes_checked=len(evidence_checks),embedding_calls=0,annotations_authored_before_target_selection=True)
 put(OUT/'offline_summary.json',summary)
 md=['# 075 固定四例批注（API前冻结）','','以下英文内容实际加入Judge提示；批注由研究者/Codex依据原reference撰写，不是医生原始解释。原例子、原标签和原reference均保持字节内容不变。','']
 for x,n in zip(examples,notes):
  md += [f"## 示例{x['ordinal']}：{x['physician_label']}",'',x['claim'],'',f"**核验要求：** {n['claim_requirements']}",'']
  for e in n['evidence']:md += [f"- reference #{e['reference_number']}：`{normalized(e['quote'])}`；{e['interpretation']}"]
  md += ['',n['decision_explanation'],'',n['boundary'],'']
 (OUT/'annotations_review.md').write_text('\n'.join(md)+'\n',encoding='utf-8',newline='\n')
 artifacts=[p for p in OUT.iterdir() if p.is_file()]
 src=[TASK/n for n in ['annotations075.json','prepare075.py','common075.py','run075.py','analyze075.py','decide075.py','README.md']]+[ROOT/r for r in SOURCES]+[ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl',ROOT/'outputs/074_anchor_dynamic_examples/manifest.json',ROOT/'outputs/073_clinical_example_matching/manifest.json',ROOT/'outputs/053_thinking_prior_validation/freeze.json',ROOT/'outputs/053_thinking_prior_validation/main_jobs.jsonl',ROOT/'outputs/034_same_data_comparison/predictions_common.csv',ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv']
 put(OUT/'freeze.json',dict(status='FROZEN_BEFORE_075_API',created_utc=now(),cap_cny=20.,model=template['model'],pilot_patients=old['pilot_patients'],confirmation_patients=old['confirmation_patients'],teaching_patients=old['teaching_patients'],pilot_n=36,confirmation_n=60,source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in src},artifact_sha256={p.name:sha(p) for p in artifacts}))
 print(canonical(summary))
if __name__=='__main__':main()
