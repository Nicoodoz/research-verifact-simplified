"""Close the authorized preflight-stop branch honestly; no classifier/API/publishing actions."""
from collections import Counter
import common102 as c
def main():
 pf=c.read(c.OUT/'preflight.json');check=c.read(c.OUT/'selfcheck.json');assert check['status']=='PASS' and not pf['paid_execution_allowed']
 ss=c.lines(c.OUT/'selections.jsonl');teachers=c.lines(c.OUT/'teaching_provenance.jsonl');labels={r['id']:r['label'] for r in teachers}
 transition=[]
 for r in ss:
  slots=[dict(label=label,topic_id=a,relation_id=b,changed=a!=b) for label,a,b in zip(c.LABELS,r['demo_topic'],r['demo_relation'])]
  transition.append(dict(id=r['id'],panel=r['panel'],slots=slots,replaced_slots=r['replaced_slots'],target_prediction_transition=None,classification_status='not_executed'))
 c.putl(c.OUT/'selection_transitions.jsonl',transition)
 freq={arm:dict(Counter(pid for r in ss for pid in r[arm])) for arm in ['demo_topic','demo_relation']}
 summary=dict(by_panel={panel:dict(N=sum(r['panel']==panel for r in ss),different=sum(r['panel']==panel and not r['same_examples'] for r in ss),reference_ablation_changed=sum(r['panel']==panel and r['relation_changed_without_reference'] for r in ss)) for panel in ['natural','pressure']},selection_frequencies=freq,unique_teachers_selected={arm:len(x) for arm,x in freq.items()},changed_slots_by_class={label:sum(t['slots'][i]['changed'] for t in transition) for i,label in enumerate(c.LABELS)},classification_executed=False)
 c.put(c.OUT/'selection_analysis.json',summary)
 c.put(c.OUT/'cost_ledger.json',dict(task='102_demo_relation',hard_cap_cny=35,paid_attempts=0,HTTP200=0,retries=0,actual_catalog_or_reserved_cny=0,unknown_or_inflight_cny=0,channel_discount_not_used=True,previous_task_budget_not_carried=True,forecast=pf['budget']))
 c.put(c.OUT/'classification_results.json',dict(status='NOT_EXECUTED',reason='Frozen full-panel budget gate failed before paid calls; qualitative relation binding concerns also remain',configurations={arm:dict(MCC=None,PA=None,Macro_F1=None,false_S=None,NS_recall=None,NA_recall=None) for arm in c.ARMS},paired_rescue_harm=None,patient_bootstrap=None,not_a_negative_classification_result=True))
 c.put(c.OUT/'complete.json',dict(utc=c.utc(),task_status='PREFLIGHT_CLOSED_PAID_EXECUTION_STOPPED',scientific_status='分类效果未检验',automatic_construction_checks_passed=True,relation_semantic_quality_not_certified=True,paid_calls=0,cost_cny=0,budget_required_cny=pf['budget']['required_idle_budget_cny'],budget_cap_cny=35,default_unchanged=True,commit_or_push=False,next_experiment_started=False,independent_audit=False,report_sha256=c.sha(c.OUT/'report.md'),method_review_sha256=c.sha(c.OUT/'method_review.md'),selfcheck_sha256=c.sha(c.OUT/'selfcheck.json')))
 print(c.canonical(summary))
if __name__=='__main__':main()
