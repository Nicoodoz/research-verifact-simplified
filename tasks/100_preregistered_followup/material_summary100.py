"""Frozen geometry and completed-phase token/alias summary; no new API."""
import statistics
import common100 as c
def stats(values):
 values=sorted(values)
 return dict(N=len(values),min=values[0],median=statistics.median(values),mean=statistics.mean(values),p95=values[min(len(values)-1,int(len(values)*.95))],max=values[-1])
def main():
 cohort={r['id']:r for r in c.lines(c.OUT/'cohort.jsonl')};ledger=c.lines(c.OUT/'construction_ledger.jsonl');out={}
 for stage in ['development','confirmation']:
  rr=[r for r in ledger if cohort[r['id']]['stage']==stage]
  out[stage]=dict(planned_N=len(rr),S_equals_L=sum(r['S_equals_L'] for r in rr),L_equals_E=sum(r['L_equals_E'] for r in rr),S_L_gap=stats([r['S_L_token_gap'] for r in rr]),
   reference_lengths={a:stats([r['references'][a]['rendered_reference_tokens'] for r in rr]) for a in ['O','C','S24','L24','EHR-all']},
   L_selected_notes=stats([r['L_notes'] for r in rr]),S_selected_complete_passages=stats([r['S_passages'] for r in rr]))
 observed={}
 for mode in ['development','confirmation','cross_model_confirmation']:
  p=c.OUT/(mode+'_usage.jsonl')
  if not p.exists():continue
  usage=c.lines(p);arms=sorted({r['arm'] for r in usage});observed[mode]=dict(by_arm={a:dict(input_tokens=stats([r['prompt_tokens'] for r in usage if r['arm']==a and not r['repeat']]),output_tokens=stats([r['completion_tokens'] for r in usage if r['arm']==a and not r['repeat']])) for a in arms},
   logical_calls=len(usage),unique_body_slots=len({r['request_id'] for r in usage}),all_HTTP200_preserved=True)
  pairs={}
  for r in usage:
   if not r['repeat']:pairs.setdefault(r['id'],{})[r['arm']]=r['prompt_tokens']
  gaps=[v['L24']-v['S24'] for v in pairs.values() if 'S24' in v and 'L24' in v]
  if gaps:observed[mode]['actual_API_L_minus_S_input_tokens']=stats(gaps)
 c.put(c.OUT/'input_operation_summary.json',dict(frozen=out,observed_completed_phases=observed,token_count_basis='JSON-escaped reference interior, plus separately recorded actual native prompt usage',no_new_API=True))
 print(c.canonical(dict(completed_phases=list(observed),actual_API_L_S_gaps={k:v.get('actual_API_L_minus_S_input_tokens') for k,v in observed.items()})))
if __name__=='__main__':main()
