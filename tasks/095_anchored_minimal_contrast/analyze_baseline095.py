"""9065-row unified table; missing and invalid kept distinct, no cross-model fill."""
import sys,json,statistics
from collections import Counter
import common095 as c
import state095 as s
from cache095 import parse_arm,signature
from metrics095 import score,paired,strata,transition

MODELS=['Original','B_raw','B_PriorG','092_Frozen','092_Finetuned']

def main():
    assert not (c.PRIVATE/'run.lock').exists(),'freeze analysis after active requests drain'
    base=c.lines(c.ROOT/'outputs/092_task_adapted_verifier/oof_predictions.jsonl');inventory={r['id']:r for r in c.lines(c.OUT/'reference_inventory.jsonl')};cached={r['id']:r for r in c.lines(c.OUT/'cache_selected.jsonl')};native=s.successful_jobs();selected=dict(cached)
    for rid,a in sorted(native.items(),key=lambda kv:(kv[1]['utc'],kv[0])):
        j=a['job']
        if j['arm']!='B' or j['id'] in selected:continue
        p=json.loads(j['body']['messages'][1]['content']);pid=j['id']
        if set(p)!={'proposition','reference'}:continue
        assert signature(j['body'])==c.read(c.OUT/'cache_inventory.json')['template_signature']
        assert c.h(p['proposition'])==inventory[pid]['claim_sha256'] and c.h(p['reference'])==inventory[pid]['reference_sha256']
        parsed,labels=parse_arm(s.receipt(a),None);parsed['core_invalid_no_imputation']=parsed.pop('fallback_used');parsed['raw_invalid_no_imputation']=parsed.pop('raw_fallback_used');folder=c.ROOT/a['folder']
        selected[pid]=dict(id=pid,time=a['utc'],phase=j['phase'],request_id=rid,request_path=(folder/'request.json').relative_to(c.ROOT).as_posix(),receipt_path=(folder/'receipt.json').relative_to(c.ROOT).as_posix(),request_sha256=c.sha(folder/'request.json'),receipt_sha256=c.sha(folder/'receipt.json'),body_sha256=j['body_sha256'],parsed=parsed,labels=labels)
    rows=[];missing=[]
    for r in base:
        pid=r['id'];v=selected.get(pid);p=dict(Original=r['predictions']['Original'],B_raw=v['labels']['raw'] if v else None,B_PriorG=v['labels']['PriorG'] if v else None,B_U0=v['labels']['U0'] if v else None,B_U2=v['labels']['U2'] if v else None,**{'092_Frozen':r['predictions']['frozen'],'092_Finetuned':r['predictions']['finetuned']})
        x={k:r[k] for k in ['id','sid','GT','author','historical_role','time_metadata_conflict','initial_agreement','fold']}
        x.update(predictions=p,probabilities={},C48_source=inventory[pid]['source'],claim_sha256=inventory[pid]['claim_sha256'],reference_sha256=inventory[pid]['reference_sha256'],B=v,B_present=v is not None,B_raw_valid=bool(v and v['parsed']['raw_valid']),B_core_valid=bool(v and v['parsed']['valid']),B_scores_valid=bool(v and v['parsed']['scores_valid']),batch='095_new' if v and pid not in cached else v['request_path'].split('/')[1] if v else 'missing')
        x['B_call_UTC_hour']=v['time'][:13] if v else 'missing';x['B_execution_phase']=v.get('phase',x['batch']) if v else 'missing'
        rows.append(x)
        if not v:missing.append(dict(id=pid,reference_sha256=inventory[pid]['reference_sha256'],source=inventory[pid]['source']))
    core=[r for r in rows if r['B_core_valid']];raw=[r for r in rows if r['B_raw_valid']];rawmodels=['Original','B_raw','092_Frozen','092_Finetuned']
    c.putl(c.OUT/'unified_9065_predictions.jsonl',rows);c.putl(c.OUT/'baseline_remaining.jsonl',sorted(missing,key=lambda r:c.h('095/baseline/'+r['id'])))
    summary=dict(universe=len(rows),patients=len({r['sid'] for r in rows}),successful_B=len(selected),core_valid_B=len(core),raw_valid_B=len(raw),scores_valid_B=sum(r['B_scores_valid'] for r in rows),missing=len(missing),HTTP200_core_invalid=len(selected)-len(core),raw_valid_score_invalid=sum(r['B_raw_valid'] and not r['B_scores_valid'] for r in rows),raw_invalid_score_valid=sum(not r['B_raw_valid'] and r['B_scores_valid'] for r in rows),cached_initial=len(cached),new_B=len(selected)-len(cached),full_B_complete=not missing,GT=dict(Counter(r['GT'] for r in rows)),reference_sources=dict(Counter(r['C48_source'] for r in rows)),core_correct_lower_bound_on_9065=sum(r['predictions']['B_PriorG']==r['GT'] for r in rows)/len(rows),note='Invalid and missing are not classified as NA and receive no old-answer/model imputation. Lower bound is coverage-aware, not comparable complete-case PA.')
    tables=dict(full_9065_existing=score(rows,['Original','092_Frozen','092_Finetuned']),common_core=score(core,MODELS+['B_U0','B_U2']),common_raw=score(raw,rawmodels))
    pairs={a+'-'+b:paired(core,b,a) for b,a in [('Original','B_PriorG'),('B_raw','B_PriorG'),('092_Frozen','B_PriorG'),('092_Finetuned','B_PriorG')]};pairs['raw_B-Original']=paired(raw,'Original','B_raw')
    grouped={field:strata(core,field,MODELS) for field in ['sid','author','historical_role','C48_source','batch','B_call_UTC_hour','B_execution_phase','time_metadata_conflict','initial_agreement']}
    if any(r['batch']=='095_new' for r in core):grouped['initial_cache_vs_new']=strata([dict(r,cache_group='095_new' if r['batch']=='095_new' else 'historical_cache') for r in core],'cache_group',MODELS)
    c.put(c.OUT/'baseline_coverage.json',summary);c.put(c.OUT/'baseline_metrics.json',tables);c.put(c.OUT/'baseline_paired.json',pairs);c.put(c.OUT/'baseline_strata.json',grouped);c.put(c.OUT/'baseline_class_transitions.json',dict(author_to_G=transition(core,'Original','B_PriorG'),raw_to_G=transition(core,'B_raw','B_PriorG')))
    changes=[]
    for r in core:
        g=r['GT'];a,b,rawp=(r['predictions'][k] for k in ['Original','B_PriorG','B_raw'])
        changes.append(dict(id=r['id'],sid=r['sid'],GT=g,Original=a,B_raw=rawp,B_PriorG=b,author_rescue=a!=g and b==g,author_harm=a==g and b!=g,boundary_rescue=rawp!=g and b==g,boundary_harm=rawp==g and b!=g,NS_to_S=g=='Not Supported' and b=='Supported',NA_to_S=g=='Not Addressed' and b=='Supported',batch=r['batch'],C48_source=r['C48_source']))
    c.putl(c.OUT/'baseline_case_transitions.jsonl',changes)
    # Observed output paths, not a claim about hidden medical reasoning.
    kinds=Counter();by_gt={g:Counter() for g in ['Supported','Not Supported','Not Addressed']};profiles={}
    for r in core:
        g=r['GT'];rawp=r['predictions']['B_raw'];fin=r['predictions']['B_PriorG']
        kind='unchanged_correct' if rawp==fin==g else 'unchanged_wrong' if rawp==fin else 'rescue' if fin==g else 'harm' if rawp==g else 'wrong_to_wrong'
        kinds[kind]+=1;by_gt[g][kind]+=1
        sc=r['B']['parsed']['scores'];key=tuple(sc[k] for k in ['Supported','Not Supported','Not Addressed'])
        z=profiles.setdefault(key,dict(N=0,GT=Counter(),raw=Counter(),final=Counter(),raw_correct=0,final_correct=0,false_S=0,patients=set()))
        z['N']+=1;z['GT'][g]+=1;z['raw'][rawp]+=1;z['final'][fin]+=1;z['raw_correct']+=rawp==g;z['final_correct']+=fin==g;z['false_S']+=g!='Supported' and fin=='Supported';z['patients'].add(r['sid'])
    pp=[]
    for key,z in sorted(profiles.items(),key=lambda kv:(-kv[1]['N'],kv[0])):
        pp.append(dict(scores_S_NS_NA=list(key),**{k:dict(v) if isinstance(v,Counter) else len(v) if k=='patients' else v for k,v in z.items()}))
    c.put(c.OUT/'decision_boundary_diagnosis.json',dict(N=len(core),raw_to_G_paths=dict(kinds),by_GT={k:dict(v) for k,v in by_gt.items()},raw_U0_disagreement=sum(r['predictions']['B_raw']!=r['predictions']['B_U0'] for r in core),distinct_score_profiles=len(pp),score_profiles_by_frequency=pp,note='Descriptive only, no threshold fitting or scheme selection. Fixed output paths do not prove internal reasoning or evidence sufficiency. label_scores are self-reported integers, not token probabilities.'))
    amounts=[((v['parsed']['usage']['prompt_tokens']*1.5+v['parsed']['usage']['completion_tokens']*4.5)/1e6) for v in selected.values()];mean=statistics.mean(amounts)
    c.put(c.OUT/'baseline_gap_forecast.json',dict(remaining=len(missing),mean_idle_no_cache_cny=mean,idle_expected_cny=mean*len(missing),busy_expected_cny=mean*len(missing)*2,successes_not_retried=True))
    print('coverage',summary);print('common core',{k:(v['correct'],v['MCC'],v['false_S']) for k,v in tables['common_core'].items()})
if __name__=='__main__':main()
