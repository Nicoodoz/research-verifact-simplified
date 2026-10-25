"""Matched B/E/C results, boundary paths and preregistered stage-E decision."""
import argparse,json
from collections import Counter
import common095 as c
import state095 as s
from cache095 import parse_arm
from metrics095 import score,paired,strata,transition
ARMS=['B','E','C'];METHODS=['raw','U0','U2','PriorG'];PAIRS=[('B','C'),('E','C'),('B','E')]

def view(rows,method):return [dict(id=r['id'],sid=r['sid'],GT=r['GT'],author=r['author'],source=r.get('source'),predictions=dict(Original=r['Original'],**{a:r['labels'][a][method] for a in ARMS}),probabilities={}) for r in rows]

def table(rows,method):return score(view(rows,method),['Original']+ARMS)

def stage_decision(panels):
    n=panels['natural'];p=panels['mechanism'];t=n['metrics']['PriorG'];pt=p['metrics']['PriorG'];cb=n['comparisons']['PriorG']['C-B'];ce=n['comparisons']['PriorG']['C-E'];d=cb['delta'];risks={}
    for panel,z in [('natural',t),('mechanism',pt)]:
        risks[panel+'_S_recall']=z['C']['recall'][0]-z['B']['recall'][0]>=-.03-1e-12
        for i,label in [(1,'NS'),(2,'NA')]:risks[panel+'_'+label+'_recall']=z['C']['recall'][i]-z['B']['recall'][i]>=-.10-1e-12
        risks[panel+'_falseS_rate']=(z['C']['false_S_rate'] or 0)-(z['B']['false_S_rate'] or 0)<=.10+1e-12
    risks['natural_falseS_vs_net']=t['C']['false_S']-t['B']['false_S']<=cb['net']
    risks['mechanism_joint_damage']=not(pt['C']['MCC']-pt['B']['MCC']<-.03 and pt['C']['correct']<pt['B']['correct'])
    risk_ok=all(risks.values());positive=sum(d[k]>0 for k in ['PA','MCC','Macro_F1'])>=2;size=d['PA']>=.01-1e-12 or d['MCC']>=.015-1e-12 or d['Macro_F1']>=.015-1e-12
    no_harm=d['PA']>=-.005-1e-12 and d['MCC']>=-.01-1e-12 and d['Macro_F1']>=-.01-1e-12
    specific=ce['net']>=2 or (ce['delta']['MCC']>=.01-1e-12 and ce['net']>=0)
    across=cb['rescue_patients']>=3
    clear=positive and size and no_harm and specific and across and risk_ok
    edge=cb['net']>0 and (d['MCC']>0 or d['Macro_F1']>0) and ce['net']>0 and across and risk_ok
    return dict(provisional_numeric_action='one_frozen_extension' if clear or edge else 'stop_candidate',signal='clear' if clear else 'edge' if edge else 'not_supported',risks=risks,positive_metrics=positive,magnitude_pass=size,other_metric_guard=no_harm,C_minus_E_increment=specific,rescue_patient_guard=across,source_review_required_before_extension=True,default_upgrade=False,note='Applies only natural common-core increments; pressure independent safety checks. No interval-crossing rule. Source audit and budget can stop but cannot relax numeric criteria.')

def analyze(tag='screen'):
    assert not (c.PRIVATE/'run.lock').exists()
    success=s.success_index();aliases=c.lines(c.OUT/(tag+'_aliases.jsonl'));sample=c.lines(c.OUT/(tag+'_sample.jsonl'));meta={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')};audit={r['id']:r for r in c.lines(c.OUT/('construction_audit.jsonl' if tag=='screen' else tag+'_construction_audit.jsonl'))};byid={r['id']:dict(r,Original=meta[r['id']]['original'],arms={},labels={},construction=audit[r['id']]) for r in sample};parsed={}
    for a in aliases:
        rid=a['request_id'];assert rid in success,('uncompleted logical position',a)
        if rid not in parsed:
            info,labels=parse_arm(s.receipt(success[rid]),None);info['core_invalid_no_imputation']=info.pop('fallback_used');info['raw_invalid_no_imputation']=info.pop('raw_fallback_used');parsed[rid]=(info,labels)
        info,labels=parsed[rid];row=byid[a['id']];row['operated']=a['operated'];row['arms'][a['arm']]=dict(info,request_id=rid,body_sha256=a['body_sha256'],exact_B_alias=a['exact_B_alias']);row['labels'][a['arm']]=labels
    rows=list(byid.values());assert all(set(r['arms'])==set(ARMS) for r in rows);c.putl(c.OUT/(tag+'_predictions.jsonl'),rows);panels={};trans=[]
    for panel in ['natural','mechanism']:
        full=[r for r in rows if r['panel']==panel];core=[r for r in full if all(r['arms'][a]['valid'] for a in ARMS)];raw=[r for r in full if all(r['arms'][a]['raw_valid'] for a in ARMS)]
        assert core and raw
        operated=[r for r in full if r['operated']]
        d=dict(N=len(full),patients=len({r['sid'] for r in full}),GT=dict(Counter(r['GT'] for r in full)),core_N=len(core),raw_N=len(raw),constructor_program_valid=sum(r['construction']['program_valid'] for r in full),operated_N=len(operated),operated_patients=len({r['sid'] for r in operated}),attribute_counts=dict(Counter(r['construction'].get('attribute') for r in operated)),metrics={m:table(core,m) for m in METHODS},native_raw_metrics=table(raw,'raw'),comparisons={m:{a+'-'+b:paired(view(raw if m=='raw' else core,m),b,a) for b,a in PAIRS} for m in ['raw','PriorG']},operated_metrics={m:table([r for r in (raw if m=='raw' else core) if r['operated']],m) for m in ['raw','PriorG']},operated_comparisons={m:{a+'-'+b:paired(view([r for r in (raw if m=='raw' else core) if r['operated']],m),b,a) for b,a in PAIRS} for m in ['raw','PriorG']},full_status={a:dict(core_invalid=sum(not r['arms'][a]['valid'] for r in full),raw_invalid=sum(not r['arms'][a]['raw_valid'] for r in full),known_final_correct=sum(r['labels'][a]['PriorG']==r['GT'] for r in full),conservative_full_PA=sum(r['labels'][a]['PriorG']==r['GT'] for r in full)/len(full)) for a in ARMS},excluded_core_ids=[r['id'] for r in full if r not in core],author_strata=strata(view(core,'PriorG'),'author',['Original']+ARMS),source_strata=strata(view(core,'PriorG'),'source',['Original']+ARMS))
        panels[panel]=d
        for r in full:
            g=r['GT'];valid=r in core;rv=r in raw
            for b,a in PAIRS:
                br,ar=r['labels'][b]['raw'],r['labels'][a]['raw'];bf,af=r['labels'][b]['PriorG'],r['labels'][a]['PriorG'];rs=br!=g and ar==g if rv else None;rh=br==g and ar!=g if rv else None;fs=bf!=g and af==g if valid else None;fh=bf==g and af!=g if valid else None
                kind='invalid_related' if not valid else 'raw_rescue_retained' if rs and fs else 'raw_rescue_reversed' if rs and fh else 'raw_rescue_cancelled' if rs else 'raw_harm_retained' if rh and fh else 'raw_harm_reversed' if rh and fs else 'raw_harm_cancelled' if rh else 'final_only_rescue' if fs else 'final_only_harm' if fh else 'no_correctness_change'
                trans.append(dict(id=r['id'],sid=r['sid'],panel=panel,GT=g,comparison=a+'-'+b,operated=r['operated'],common_core=valid,common_raw=rv,base_raw=br,new_raw=ar,base_final=bf,new_final=af,raw_rescue=rs,raw_harm=rh,final_rescue=fs,final_harm=fh,kind=kind,base_scores=r['arms'][b]['scores'],new_scores=r['arms'][a]['scores']))
        d['boundary_path_counts']={a+'-'+b:dict(Counter(v['kind'] for v in trans if v['panel']==panel and v['comparison']==a+'-'+b)) for b,a in PAIRS}
    c.put(c.OUT/(tag+'_analysis.json'),dict(panels=panels,primary='Same Frozen PriorG, B/E/C, panels separate',default_unchanged=True));c.putl(c.OUT/(tag+'_transitions.jsonl'),trans);c.put(c.OUT/(tag+'_numeric_decision.json'),stage_decision(panels))
    for p,z in panels.items():print(p,'operated',z['operated_N'],'core',z['core_N'],'final',{a:(m['correct'],m['MCC'],m['false_S']) for a,m in z['metrics']['PriorG'].items()},'raw',{a:m['correct'] for a,m in z['native_raw_metrics'].items()})
    print(stage_decision(panels))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',default='screen');a=p.parse_args();analyze(a.tag)
