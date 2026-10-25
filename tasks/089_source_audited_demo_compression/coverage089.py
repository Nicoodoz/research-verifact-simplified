"""Apply the already frozen constructor to remaining 086 D candidates, never select examples."""
from construct089 import *
def main():
    for rel,d in read(OUT/'constructor_freeze.json')['sources'].items():assert sha(ROOT/rel)==d
    pool=lines(ROOT/'outputs/086_global_demonstration_selection/candidate_pool.jsonl')
    fixed={x['proposition_id'] for x in lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl')}
    rows=[];stopped=False
    for ex in pool:
        if ex['proposition_id'] in fixed:continue
        src=unitize(ex['reference']);p=OUT/'coverage'/f"{ex['candidate_id']}.json"
        if p.exists():rows.append(read(p));continue
        used=sum(x['cost_or_unknown_cny'] for x in api.state()[0])
        # Conservative full-source payload bounds all candidate lengths and JSON metadata.
        payload=dict(claim=ex['claim'],physician_label=ex['physician_label'],source_prefix=src['prefix'],source_units=src['units'],original_reference=ex['reference'],candidate_reference=ex['reference'],selected_ids=all_ids(src),budget_proxy_tokens=token_proxy(ex['reference']),proxy_definition='English words, numbers, punctuation; not model tokens')
        reserve=2*3*(api.bound(dict(body=body(COMMON+P_GOAL+Q_GOAL,payload)))+api.bound(dict(body=body(CHECK,payload,MODEL))))
        short=len(ex['reference'])<=1200 or len(src['units'])==1
        if stopped or (not short and used+reserve>2):
            stopped=True;row=dict(id=ex['proposition_id'],candidate_id=ex['candidate_id'],status='not_called_construction_reserve',used_cny=used,full_pair_three_attempt_bound=reserve)
        else:row=dict(id=ex['proposition_id'],candidate_id=ex['candidate_id'],status='constructed',original_chars=len(ex['reference']),source_units=src,**pair(ex,src,'coverage'))
        put(p,row);rows.append(row);print(canonical(dict(candidate=ex['candidate_id'],status=row['status'])),flush=True)
    put(OUT/'coverage_summary.json',dict(pool_source_sha256=sha(ROOT/'outputs/086_global_demonstration_selection/candidate_pool.jsonl'),fixed_four_reused=True,remaining=rows,
        cost_cny=sum(x['cost_or_unknown_cny'] for x in api.state()[0]),target_GT_or_Judge_used=False))
if __name__=='__main__':main()
