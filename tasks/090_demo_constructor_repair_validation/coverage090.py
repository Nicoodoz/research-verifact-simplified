"""Reuse old D responses once through final090 source machinery, zero new inference."""
from repair_construction_v2 import *
def main():
    pool={x['proposition_id']:x for x in lines(ROOT/'outputs/086_global_demonstration_selection/candidate_pool.jsonl')}
    old=read(ROOT/'outputs/089_source_audited_demo_compression/coverage_summary.json')['remaining'];rows=[];details=[]
    for r in old:
        ex=pool[r['id']];src=unitize(ex['reference'])
        for before,arm in (('P4','P90'),('Q4','Q90')):
            v=r[before];obj=copy.deepcopy(v.get('constructor_output'));target=round(token_proxy(ex['reference'])*.5)
            if arm=='P90':
                sel=select_p(ex,src,obj,target)
                if sel['usable']:
                    obj['groups']=obj.pop('information') if 'information' in obj else obj['groups'];obj,audit=split_alternatives(src,obj);sel=select_p(ex,src,obj,target)
            else:sel=select_q(ex,src,obj,target)
            # The old checker response belongs to its original candidate only. Do not certify a changed090 extract with it.
            review=repair(ex,src,v['initial_selected_ids'],v.get('review_output'))
            rows.append(dict(candidate_id=r['candidate_id'],id=r['id'],arm=arm,source='089 native constructor reused; no new prompt/model inference',
                old_status=v['status'],new_status=sel['status'],source_usable=sel['usable'],selected_ids=sel['selected_ids'],original_chars=len(ex['reference']),
                selected_chars=len(render_reference(src,sel['selected_ids'])),old_checker_raw_issue_count=len((v.get('review_output') or {}).get('issues',[])),
                old_checker_filtered_accepted=len(review['accepted']),old_checker_rejection_reasons=[x['reason'] for x in review['rejected']],
                new_candidate_checked=False,downstream_tested=False))
            details.append(dict(candidate_id=r['candidate_id'],arm=arm,selection=sel,old_checker_reanalysis=review))
    put(OUT/'D_coverage_detail.json',details);put(PUB/'D_coverage.json',dict(rows=rows,new_API_calls=0,used_for_example_selection=False,
        limitation='Final090 normalization/coverage functions applied to old088/089-style responses; not a test of new constructor prompting across examples or classification generalization.'))
    print(canonical(dict(arms=len(rows),source_usable=sum(x['source_usable'] for x in rows),new_API=0)))
if __name__=='__main__':main()
