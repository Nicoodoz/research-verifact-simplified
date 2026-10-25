"""Frozen same-ID three-arm evaluation; no new calls or label fitting."""
import sys,re,json
from collections import Counter
import common094 as c
import api094
sys.path.insert(0,str(c.ROOT/'tasks/090_demo_constructor_repair_validation'))
from analyze090 import parse_arm
sys.path.insert(0,str(c.ROOT/'tasks/092_task_adapted_verifier'))
from analyze092 import table,paired
ARMS=['B','V','Q'];METHODS=['raw','U0','U2','PriorG'];PAIRS=[('B','Q'),('V','Q'),('B','V')]
def view(rows,method):return [dict(id=r['id'],sid=r['sid'],GT=r['GT'],predictions={'Original':r['Original'],**{a:r['labels'][a][method] for a in ARMS}},probabilities={}) for r in rows]
def score(rows,method):return table(view(rows,method),['Original']+ARMS) if rows else None
def compare(rows,b,a,method):return paired(view(rows,method),b,a) if rows else None
def main():
    attempts,success=api094.state();jobs=c.lines(c.PRIVATE/'judge_jobs.jsonl');assert all(j['request_id'] in success for j in jobs)
    meta={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')};rows={r['id']:dict(r,Original=meta[r['id']]['original'],arms={},labels={}) for r in c.lines(c.OUT/'sample.jsonl')};info={}
    for j in jobs:
        parsed,labels=parse_arm(success[j['request_id']]['tr'],None);parsed['core_invalid_no_imputation']=parsed.pop('fallback_used');parsed['raw_invalid_no_imputation']=parsed.pop('raw_fallback_used');info[j['request_id']]=(parsed,labels)
    for a in c.lines(c.OUT/'judge_aliases.jsonl'):
        parsed,labels=info[a['request_id']];r=rows[a['id']];r['operated']=a['operated'];r['arms'][a['arm']]={**parsed,'request_id':a['request_id'],'body_sha256':a['body_sha256']};r['labels'][a['arm']]=labels;assert r['GT']==meta[r['id']]['GT']
    rows=list(rows.values());c.putl(c.OUT/'predictions_public.jsonl',rows);panels={};transitions=[]
    for panel in ['natural','mechanism']:
        full=[r for r in rows if r['panel']==panel];core=[r for r in full if all(r['arms'][a]['valid'] for a in ARMS)];raw=[r for r in full if all(r['arms'][a]['raw_valid'] for a in ARMS)]
        d=dict(N=len(full),patients=len({r['sid'] for r in full}),GT=dict(Counter(r['GT'] for r in full)),core_N=len(core),raw_N=len(raw),operated_N=sum(r['operated'] for r in full),full_status={a:dict(invalid=sum(not r['arms'][a]['valid'] for r in full),raw_invalid=sum(not r['arms'][a]['raw_valid'] for r in full),known_final_correct=sum(r['labels'][a]['PriorG']==r['GT'] for r in full),conservative_full_PA=sum(r['labels'][a]['PriorG']==r['GT'] for r in full)/len(full)) for a in ARMS},metrics={m:score(core,m) for m in METHODS},native_raw_metrics=score(raw,'raw'),comparisons={m:{a+'-'+b:compare(raw if m=='raw' else core,b,a,m) for b,a in PAIRS} for m in ['raw','PriorG']},operated_metrics={m:score([r for r in (raw if m=='raw' else core) if r['operated']],m) for m in ['raw','PriorG']},author_strata={author:{m:score([r for r in (raw if m=='raw' else core) if r['author']==author],m) for m in ['raw','PriorG']} for author in ['human','llm']},excluded_core_ids=[r['id'] for r in full if r not in core])
        panels[panel]=d
        for r in full:
            for b,a in PAIRS:
                bf,af=r['labels'][b]['PriorG'],r['labels'][a]['PriorG'];br,ar=r['labels'][b]['raw'],r['labels'][a]['raw'];g=r['GT'];valid=r in core;rv=r in raw
                transitions.append(dict(id=r['id'],sid=r['sid'],panel=panel,GT=g,comparison=a+'-'+b,operated=r['operated'],common_core=valid,common_raw=rv,base_raw=br,new_raw=ar,base_final=bf,new_final=af,raw_rescue=br!=g and ar==g if rv else None,raw_harm=br==g and ar!=g if rv else None,final_rescue=bf!=g and af==g if valid else None,final_harm=bf==g and af!=g if valid else None))
    ext={(r['id'],r['arm']):r for r in c.lines(c.PRIVATE/'extracted_aligned.jsonl')};mechanism=[]
    for r in rows:
        if not r['operated']:continue
        v,q=ext[r['id'],'V'],ext[r['id'],'Q'];cs=lambda z:{(x['reference_id'],x['quote_sha256']) for x in z['citations']};vs,qs=cs(v),cs(q)
        answers=lambda z:[re.sub(r'\s+',' ',x['answer']).lower() for x in z['record']['candidates']]
        mechanism.append(dict(id=r['id'],panel=r['panel'],sid=r['sid'],V_valid=v['valid'],Q_valid=q['valid'],V_status=v['record']['status'],Q_status=q['record']['status'],V_candidates=len(v['record']['candidates']),Q_candidates=len(q['record']['candidates']),record_identical=v['record']==q['record'],answer_text_identical=answers(v)==answers(q),citation_set_identical=vs==qs,citation_jaccard=len(vs&qs)/len(vs|qs) if vs|qs else None,V_record_sha256=c.h(c.canonical(v['record'])),Q_record_sha256=c.h(c.canonical(q['record']))))
    auxiliary_subset={}
    for panel in ['natural','mechanism']:
        eligible=[r for r in rows if r['panel']==panel and r['operated'] and ext[r['id'],'V']['valid'] and ext[r['id'],'Q']['valid'] and all(r['arms'][a]['valid'] for a in ARMS)]
        auxiliary_subset[panel]=dict(N=len(eligible),metrics={method:score(eligible,method) for method in ['raw','PriorG']},note='Post-output validity diagnostic only; not replacement primary or new selection rule')
    c.put(c.OUT/'both_aux_valid_diagnostic.json',auxiliary_subset)
    charges=Counter();usage={};logical={}
    for a in attempts:charges[a['stage']]+=a['charge_cny']
    for panel in ['natural','mechanism']:
        rr=[r for r in rows if r['panel']==panel];logical[panel]={}
        for arm in ARMS:
            u=Counter();elapsed=0.;cost=0.;calls=0
            for r in rr:
                ids=[r['arms'][arm]['request_id']]
                if arm!='B':
                    ids+=[c.h('094/'+r['id']+'/generate/shared')[:28]]
                    if r['operated']:ids+=[c.h('094/'+r['id']+'/extract/'+arm)[:28]]
                for rid in ids:
                    tr=success[rid]['tr'];nu=json.loads(tr['body_text'])['usage'];u['input']+=nu['prompt_tokens'];u['output']+=nu['completion_tokens'];elapsed+=tr['client_elapsed_seconds'];cost+=(nu['prompt_tokens']*3+nu['completion_tokens']*9)/1e6;calls+=1
            logical[panel][arm]=dict(N=len(rr),calls=calls,input_tokens=u['input'],output_tokens=u['output'],undiscounted_cny=cost,mean_sequential_call_seconds=elapsed/len(rr))
    budget=dict(cap_cny=20,attempts=len(attempts),HTTP200=len(success),retries=len(attempts)-len(success),original_price_or_reserved_cny=sum(charges.values()),stage_cost_cny=dict(charges),logical_panels=logical,manual_question_reviews=32,manual_review_cost_not_monetized=True,no_new_retrieval_or_GPU=True)
    c.put(c.OUT/'analysis.json',dict(panels=panels,bootstrap='1000 patient-cluster resamples conditional on fixed outputs; not external confirmation or equivalence',primary='Q-B and Q-V Frozen PriorG',default_unchanged=True));c.put(c.OUT/'cost_ledger.json',budget);c.putl(c.OUT/'attempt_ledger.jsonl',attempts);c.putl(c.OUT/'transitions.jsonl',transitions);c.putl(c.OUT/'extraction_differences.jsonl',mechanism)
    for panel,d in panels.items():print(panel,'core',d['core_N'],'final',{a:(z['correct'],z['MCC'],z['false_S']) for a,z in d['metrics']['PriorG'].items()},'raw',{a:z['correct'] for a,z in d['native_raw_metrics'].items()})
    print('total cost',budget['original_price_or_reserved_cny'])
if __name__=='__main__':main()
