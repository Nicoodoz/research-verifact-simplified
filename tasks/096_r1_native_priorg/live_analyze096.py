"""Offline-only fit and same-ID evaluation, requires completed reconciliation."""
import sys,collections,csv,json
import common096 as c
import live_run096 as run
from calibration096 import decode
from bounded_fit096 import fit_g
sys.path.insert(0,str(c.ROOT/'src'))
sys.path.insert(0,str(c.ROOT/'tasks/095_anchored_minimal_contrast'))
from metrics095 import score,paired,transition,strata
O=run.O;P=run.P
MODELS=['Original','V4_raw','R1_raw','R1_V4_PriorG','R1_adapted_PriorG','V4_PriorG','R1_U0','R1_G_only','R1_prior_only']
PAIRS=[('Original','R1_raw'),('Original','V4_raw'),('V4_raw','R1_raw'),('R1_raw','R1_adapted_PriorG'),('R1_V4_PriorG','R1_adapted_PriorG'),('Original','R1_adapted_PriorG'),('V4_PriorG','R1_adapted_PriorG'),('R1_U0','R1_G_only'),('R1_U0','R1_prior_only'),('R1_prior_only','R1_adapted_PriorG')]
def fit_calibration(jj):
    truth={r['id']:r for r in c.lines(c.PRIVATE/'calibration_supervision.jsonl')};good=[];invalid=[]
    for j in jj:
        if j['stage']!='calibration':continue
        p=run.parsed(j)
        if p['valid'] and p['label_scores'] is not None:good.append(dict(id=j['id'],sid=j['sid'],GT=truth[j['id']]['GT'],scores=p['label_scores']))
        else:invalid.append(j['id'])
    assert len(good)+len(invalid)==143
    counts=dict(collections.Counter(r['GT'] for r in good));assert set(counts)==set(c.LABELS)
    model,check=fit_g(good);v4,vcheck=fit_g([truth[r['id']] for r in good]);old=c.read(c.OUT/'calibration_recipe.json')
    result=dict(status='FROZEN_BEFORE_EVALUATION_GT_JOIN_AFTER_GPU_DONE',calibration_ids=sorted(r['id'] for r in good),training_ids_sha256=c.digest(sorted(r['id'] for r in good)),invalid_ids=invalid,counts=counts,reference_counts=old['reference_counts'],R1_model=model,R1_independent_objective_check=check,V4_matched_model=v4,V4_matched_objective_check=vcheck,old_V4_theta=old['old_theta'],old_counts=old['calibration_counts'],boundary_hit=abs(model['theta'][0])>=6-1e-8,evaluation_GT_used=False,recipe_sha256=c.sha(c.OUT/'calibration_recipe.json'))
    c.put(O/'R1_calibration_model.json',result);return result
def main():
    done=c.read(O/'R1_INFERENCE_DONE.json');assert done['status']=='R1_INFERENCE_DONE' and c.sha(O/'response_reconciliation.jsonl')==done['reconciliation_sha256']
    sel=c.read(O/'tier_selection.json');ids=set(sel['ids']);jj=[j for j in run.jobs() if j['id'] in ids];model=fit_calibration(jj)
    # Only now join evaluation GT. No endpoint access anywhere in this program.
    base={r['id']:r for r in c.lines(P/'comparator_cache.jsonl')};rows=[];public=[]
    for j in jj:
        p=run.parsed(j);public.append(dict(id=j['id'],sid=j['sid'],stage=j['stage'],raw_valid=p['valid'],core_valid=p['valid'] and p['label_scores'] is not None,verdict=p['verdict'],label_scores=p['label_scores'],invalid_reason=p['invalid_reason'],finish=p['finish'],usage=p['usage'],request_id=j['request_id'],body_sha256=j['body_sha256']))
        if j['stage']=='calibration':continue
        b=base[j['id']];r={k:b[k] for k in ['id','sid','GT','author','C48_source','B_core_valid','B_raw_valid','B_call_UTC_hour','historical_role']};r.update(panel=j['stage'],R1_raw_valid=p['valid'],R1_core_valid=p['valid'] and p['label_scores'] is not None,predictions={'Original':b['predictions']['Original'],'V4_raw':b['predictions']['B_raw'],'V4_PriorG':b['predictions']['B_PriorG'] if b['B_core_valid'] else None,'R1_raw':p['verdict'] if p['valid'] else None},probabilities={},R1_scores=p['label_scores'],V4_scores=b['B']['parsed']['scores'])
        if r['R1_core_valid']:
            s=p['label_scores'];ref=model['reference_counts'];old=model['old_counts'];new=model['counts'];theta=model['R1_model']['theta'][0]
            r['predictions'].update(R1_U0=decode(s),R1_G_only=decode(s,theta),R1_prior_only=decode(s,0,ref,new),R1_V4_PriorG=decode(s,model['old_V4_theta'],ref,old),R1_adapted_PriorG=decode(s,theta,ref,new))
        rows.append(r)
    c.putl(O/'R1_parsed_predictions.jsonl',public);c.putl(O/'unified_predictions.jsonl',rows)
    tables={};pairs={};transitions={};sub={};coverage={};patients={};cases=[]
    for panel in ['natural','diagnostic']:
        rr=[r for r in rows if r['panel']==panel];raw=[r for r in rr if r['R1_raw_valid']];core=[r for r in rr if r['R1_core_valid'] and r['B_core_valid']]
        coverage[panel]=dict(full_N=len(rr),raw_common_N=len(raw),core_common_N=len(core),R1_raw_invalid=[r['id'] for r in rr if not r['R1_raw_valid']],R1_core_invalid=[r['id'] for r in rr if not r['R1_core_valid']],V4_core_invalid=[r['id'] for r in rr if not r['B_core_valid']],fallback_used=False)
        tables[panel]=dict(raw_common=score(raw,['Original','V4_raw','R1_raw']),all_methods_common=score(core,MODELS),per_method_available={m:score([r for r in rr if r['predictions'].get(m) in c.LABELS],[m]) for m in MODELS})
        pairs[panel]={};transitions[panel]={};sub[panel]={}
        for a,b in PAIRS:
            valid=[r for r in rr if r['predictions'].get(a) in c.LABELS and r['predictions'].get(b) in c.LABELS];key=b+'_vs_'+a
            pairs[panel][key]=paired(valid,a,b);transitions[panel][key]=transition(valid,a,b)
            for r in valid:
                x=r['predictions'][a];y=r['predictions'][b]
                if x!=y:cases.append(dict(panel=panel,comparison=key,id=r['id'],sid=r['sid'],GT=r['GT'],author=r['author'],base=x,candidate=y,type='rescue' if y==r['GT'] else 'harm' if x==r['GT'] else 'wrong_to_wrong'))
        for field in ['author','C48_source','B_call_UTC_hour','historical_role']:sub[panel][field]=strata(core,field,MODELS)
        patients[panel]=strata(core,'sid',MODELS)
    c.put(O/'main_metrics.json',tables);c.put(O/'coverage.json',coverage);c.put(O/'paired_bootstrap.json',pairs);c.put(O/'class_transitions.json',transitions);c.put(O/'subgroups.json',sub);c.put(O/'patients.json',patients);c.putl(O/'paired_case_transitions.jsonl',cases)
    flat=[];md=['# 096同ID结果表','自然与少数类诊断分别展示；不可合并为总体PA。未使用fallback补R1。']
    for panel,scopes in tables.items():
        for scope in ['raw_common','all_methods_common']:
            md+=['',f'## {panel} / {scope}','','|配置|MCC|PA|正确/N|false-S/non-S|AC1|Macro-F1|S recall|NS recall|NA recall|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
            for name,m in scopes[scope].items():
                flat.append(dict(panel=panel,scope=scope,method=name,**{k:v for k,v in m.items() if not isinstance(v,(dict,list))}))
                # Column extraction is finalized from canonical metric schema.
                md.append(f"|{name}|{m['MCC']:.4f}|{m['PA']:.2%}|{m['correct']}/{m['N']}|{m['false_S']}/{m['true_non_S']}|{m['AC1']:.4f}|{m['Macro_F1']:.4f}|{m['recall'][0]:.2%}|{m['recall'][1]:.2%}|{m['recall'][2]:.2%}|")
    c.write(O/'tables.md','\n'.join(md))
    fields=sorted(set().union(*(r.keys() for r in flat)))
    with (O/'main_metrics.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(flat)
    print('OFFLINE_ANALYSIS_COMPLETE',json.dumps(coverage,ensure_ascii=False));print('R1_theta',model['R1_model']['theta'])
if __name__=='__main__':
    import socket
    from unittest.mock import patch
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Analysis strictly offline')):main()
