"""Post-run 087 analysis. Fixed contrasts, shared evaluator, no new fitting/API."""
import csv, statistics
from collections import Counter,defaultdict
import numpy as np
from common087 import *
import run087 as r
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tasks/053_thinking_prior_validation'))
from common053 import parse_response,decision,VALID
from verifact_research.evaluation import evaluate,paired_compare

PAIRS=(('X4','F4'),('CL4','F4'),('B','F4'),('B','CL4'),('B','X4'))

def load_gt(ids):
    master=ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv'
    gt={};original={}
    with master.open(encoding='utf-8-sig',newline='') as f:
        for x in csv.DictReader(f):
            if x['proposition_id'] not in ids:continue
            assert x['proposition_type']=='claim' and x['invalid']=='False'
            gt[x['proposition_id']]=x
    for author in ('human','llm'):
        p=ROOT/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv'
        with p.open(encoding='utf-8-sig',newline='') as f:
            for x in csv.DictReader(f):
                if x['proposition_id'] in ids:original[x['proposition_id']]=x['verdict']
    assert set(gt)==set(original)==ids
    return gt,original,sha(master)

def parse_arm(tr,fallback):
    p=parse_response(tr,True,True)
    assert p.get('model_returned')==MODEL
    valid=p['status'] in VALID and p.get('scores') is not None
    native=json.loads(tr['body_text']);choice=native['choices'][0];msg=choice['message']
    methods=dict(raw=p.get('verdict'),U0=decision(p['scores'],0) if valid else None,
                 U2=decision(p['scores'],2) if valid else None,PriorG=priorg(p['scores']) if valid else None)
    if not valid:methods={m:fallback for m in METHODS}
    info=dict(valid=valid,status=p['status'],raw_verdict=p.get('verdict') if valid else None,
              scores=p.get('scores') if valid else None,finish_reason=choice.get('finish_reason'),
              usage=native['usage'],returned_model=native.get('model'),elapsed_seconds=tr.get('client_elapsed_seconds'),
              reasoning_present=bool(msg.get('reasoning_content')),parser_errors=p.get('errors'),
              parser_adherence=p.get('adherence'),fallback_used=not valid)
    return info,methods

def collect():
    jobs=r.check_jobs();attempts,success,_=r.state()
    assert len(success)==440 and all(j['request_id'] in success for j in jobs),'incomplete four-arm run'
    sample=lines(OUT/'sample_blind.jsonl');gt,original,gtsha=load_gt({x['id'] for x in sample})
    rows={}
    for x in sample:
        g=gt[x['id']];assert g['subject_id']==x['sid'] and g['author_type']==x['author']
        rows[x['id']]={**x,'GT':g['human_gt'],'arms':{},'labels':{'Original':{m:original[x['id']] for m in METHODS}}}
    for j in jobs:
        z=rows[j['id']];s=success[j['request_id']];rp=ROOT/s['receipt_source'];tr=read(rp)['transport']
        info,labels=parse_arm(tr,z['fallback_U2'])
        info.update(receipt_source=s['receipt_source'],receipt_sha256=sha(rp),request_source=s['request_source'],body_sha256=j['body_sha256'])
        z['arms'][j['arm']]=info;z['labels'][j['arm']]=labels
    return list(rows.values()),attempts,gtsha

def cohort(rows):return [dict(proposition_id=x['id'],subject_id=x['sid'],human_gt=x['GT']) for x in rows]
def preds(rows,arm,m):return [dict(proposition_id=x['id'],verdict=x['labels'][arm][m]) for x in rows]
def metric(rows,arm,m,ci=True):
    e=evaluate(cohort(rows),preds(rows,arm,m),profile='research_patient' if ci else 'none',iterations=1000)
    false=sum(x['GT']!='Supported' and x['labels'][arm][m]=='Supported' for x in rows);non=sum(x['GT']!='Supported' for x in rows)
    patient=defaultdict(list)
    for x in rows:patient[x['sid']].append(x['labels'][arm][m]==x['GT'])
    return dict(n=len(rows),patients=len(patient),correct=sum(x['labels'][arm][m]==x['GT'] for x in rows),
        MCC=e['mcc'],PA=e['percent_agreement'],AC1=e['gwet_ac1'],Macro_F1=statistics.mean(e['per_class'][k]['f1'] or 0 for k in LABELS),
        false_S=false,non_S=non,false_S_rate_nonS=false/non if non else None,false_S_rate_all=false/len(rows),
        per_class=e['per_class'],confusion_matrix=e['confusion_matrix'],patient_CI95=e.get('confidence_intervals'),
        patient_equal_PA=statistics.mean(statistics.mean(v) for v in patient.values()),
        raw_includes_fallback=(m=='raw' and arm in ARMS and any(not x['arms'][arm]['valid'] for x in rows)))

def compare(rows,base,cand,m):
    p=paired_compare(cohort(rows),preds(rows,base,m),preds(rows,cand,m),iterations=1000)
    rescue=[x['id'] for x in rows if x['labels'][base][m]!=x['GT'] and x['labels'][cand][m]==x['GT']]
    harm=[x['id'] for x in rows if x['labels'][base][m]==x['GT'] and x['labels'][cand][m]!=x['GT']]
    pats=[]
    for sid in sorted({x['sid'] for x in rows}):
        z=[x for x in rows if x['sid']==sid];b=sum(x['labels'][base][m]==x['GT'] for x in z);c=sum(x['labels'][cand][m]==x['GT'] for x in z)
        pats.append(dict(sid=sid,n=len(z),base_correct=b,candidate_correct=c,delta_PA=(c-b)/len(z)))
    return dict(n=len(rows),paired=p,rescue_ids=rescue,harm_ids=harm,rescue=len(rescue),harm=len(harm),net=len(rescue)-len(harm),
        patient_wins=sum(x['delta_PA']>0 for x in pats),patient_losses=sum(x['delta_PA']<0 for x in pats),patient_ties=sum(x['delta_PA']==0 for x in pats),
        patient_equal_delta_PA=statistics.mean(x['delta_PA'] for x in pats),patients=pats,
        delta_false_S=sum(int(x['GT']!='Supported' and x['labels'][cand][m]=='Supported')-int(x['GT']!='Supported' and x['labels'][base][m]=='Supported') for x in rows))

def dist(values):
    return dict(mean=statistics.mean(values),min=min(values),p25=float(np.percentile(values,25)),median=statistics.median(values),
                p75=float(np.percentile(values,75)),p95=float(np.percentile(values,95)),max=max(values))

def cost(rows,attempts):
    ledger=[]
    for a in attempts:
        x=dict(a)
        if a['receipt_source']:
            tr=read(ROOT/a['receipt_source'])['transport'];x['elapsed_seconds']=tr.get('client_elapsed_seconds')
            if tr['http_status']==200:x['usage']=json.loads(tr['body_text']).get('usage')
        ledger.append(x)
    arm={}
    for a in ARMS:
        z=[x['arms'][a] for x in rows];usage=[x['usage'] for x in z]
        arm[a]=dict(n=len(z),prompt_tokens=sum(x['prompt_tokens'] for x in usage),completion_tokens=sum(x['completion_tokens'] for x in usage),
            total_tokens=sum(x['total_tokens'] for x in usage),prompt_distribution=dist([x['prompt_tokens'] for x in usage]),
            completion_distribution=dist([x['completion_tokens'] for x in usage]),total_distribution=dist([x['total_tokens'] for x in usage]),
            elapsed_seconds_distribution=dist([x['elapsed_seconds'] for x in z]),core_invalid=sum(not x['valid'] for x in z),
            truncation_n=sum(x['finish_reason']=='length' for x in z),truncation_rate=sum(x['finish_reason']=='length' for x in z)/len(z),
            original_success_cny=sum((x['prompt_tokens']*3+x['completion_tokens']*9)/1e6 for x in usage),
            attempts_original_or_unknown_cny=sum(x['cost_or_unknown_cny'] for x in attempts if x['arm']==a))
        arm[a]['original_success_per_case_cny']=arm[a]['original_success_cny']/len(z)
    total=sum(x['cost_or_unknown_cny'] for x in attempts);assert total<=20+1e-9
    out=dict(cap_original_cny=20,total_original_or_unknown_cny=total,attempts=len(attempts),http_status=dict(Counter(str(x['http_status']) for x in attempts)),
        unknown_reserved_cny=sum(x['cost_or_unknown_cny'] for x in attempts if x['http_status'] in (None,0)),arms=arm,
        price_input=3,price_output=9,discounts_ignored=True,not_billing_reconciliation=True,
        CL4_vs_F4_prompt_reduction=1-arm['CL4']['prompt_tokens']/arm['F4']['prompt_tokens'],
        CL4_vs_F4_original_cost_reduction=1-arm['CL4']['original_success_cny']/arm['F4']['original_success_cny'])
    putl(OUT/'attempt_ledger.jsonl',ledger);put(OUT/'cost_ledger.json',out)
    return out

def historical(rows):
    hist=[]
    # List every exact historical request frozen at preparation, never pick the best answer.
    for x in rows:
        for a,paths in x['prior_exact_requests'].items():
            for rel in paths:
                rp=(ROOT/rel).parent/'receipt.json'
                if not rp.exists():
                    hist.append(dict(id=x['id'],arm=a,request_source=rel,status='receipt_missing'));continue
                q=read(rp);tr=q.get('transport',q)
                if tr.get('http_status')!=200:
                    hist.append(dict(id=x['id'],arm=a,request_source=rel,status='not_HTTP200'));continue
                info,lab=parse_arm(tr,x['fallback_U2'])
                hist.append(dict(id=x['id'],sid=x['sid'],arm=a,GT=x['GT'],request_source=rel,receipt_source=rp.relative_to(ROOT).as_posix(),
                                 valid=info['valid'],native_raw=info['raw_verdict'],scores=info['scores'],
                                 historical_valid_labels=lab if info['valid'] else None,
                                 new_labels=x['labels'][a],note='Noncontemporaneous reference only; no imputed historical fallback'))
    putl(OUT/'historical_exact_references.jsonl',hist)
    # Retain conflicting stored fallback provenance only for selected IDs, never alter 087 rule.
    ids={x['id']:x for x in rows};mismatches=[]
    for rel in ('outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl','outputs/084_f4_coverage_validation/new_predictions.jsonl'):
        for z in lines(ROOT/rel):
            if z['id'] in ids:
                old=z.get('fallback_label');new=ids[z['id']]['fallback_U2']
                if old!=new:mismatches.append(dict(id=z['id'],source=rel,old_fallback=old,frozen087_fallback=new))
    put(OUT/'historical_fallback_differences.json',dict(mismatches=mismatches,selected_rule='032 U2 unchanged'))
    return hist

def main():
    rows,attempts,gtsha=collect();putl(OUT/'predictions.jsonl',rows)
    common=[x for x in rows if all(x['arms'][a]['valid'] for a in ARMS)]
    full={m:{a:metric(rows,a,m) for a in ('Original',)+ARMS} for m in METHODS}
    core={m:{a:metric(common,a,m) for a in ('Original',)+ARMS} for m in METHODS}
    pairs={};corepairs={};pairwise={};attributions=[]
    for m in METHODS:
        pairs[m]={f'{cand}-{base}':compare(rows,base,cand,m) for base,cand in PAIRS}
        corepairs[m]={f'{cand}-{base}':compare(common,base,cand,m) for base,cand in PAIRS}
    for base,cand in PAIRS:
        key=f'{cand}-{base}';z=[x for x in rows if x['arms'][base]['valid'] and x['arms'][cand]['valid']]
        pairwise[key]=dict(n=len(z),comparisons={m:compare(z,base,cand,m) for m in ('raw','PriorG')})
        for x in rows:
            b={**x['arms'][base],'final':x['labels'][base]['PriorG']};c={**x['arms'][cand],'final':x['labels'][cand]['PriorG']}
            attributions.append(dict(id=x['id'],sid=x['sid'],author=x['author'],GT=x['GT'],comparison=key,
                                     **attribution(b,c,x['GT'])))
    ats={}
    for base,cand in PAIRS:
        key=f'{cand}-{base}';z=[x for x in attributions if x['comparison']==key]
        ats[key]={k:dict(n=sum(x['kind']==k for x in z),rescue=sum(x['kind']==k and x['rescue'] for x in z),
                        harm=sum(x['kind']==k and x['harm'] for x in z)) for k in sorted({x['kind'] for x in z})}
    strata={}
    for field in ('author','teaching_candidate_patient_overlap','selection_tier'):
        for v in sorted({x[field] for x in rows},key=str):
            z=[x for x in rows if x[field]==v]
            strata[f'{field}={v}']=dict(n=len(z),patients=len({x['sid'] for x in z}),GT=dict(Counter(x['GT'] for x in z)),
                metrics={m:{a:metric(z,a,m,False) for a in ARMS} for m in ('raw','PriorG')})
    costs=cost(rows,attempts);hist=historical(rows)
    putl(OUT/'attribution_cases.jsonl',attributions)
    result=dict(status='COMPLETE',n=len(rows),patients=len({x['sid'] for x in rows}),GT=dict(Counter(x['GT'] for x in rows)),
        common_core_n=len(common),common_core_excluded=[x['id'] for x in rows if x not in common],
        full_metrics=full,common_core_metrics=core,full_comparisons=pairs,common_core_comparisons=corepairs,
        pairwise_core=pairwise,attribution_summary=ats,strata=strata,cost=costs,historical_reference_count=len(hist),
        raw_U0_disagreements={a:[x['id'] for x in rows if x['arms'][a]['valid'] and x['labels'][a]['raw']!=x['labels'][a]['U0']] for a in ARMS},
        GT_source_sha256=gtsha,predictions_sha256=sha(OUT/'predictions.jsonl'),
        multiplicity='All fixed contrasts shown; exploratory 95% intervals, no multiplicity adjustment or equivalence claim',
        uncertainty='Patient bootstrap of fixed predictions; no full model-call or historical method-selection uncertainty')
    put(OUT/'analysis.json',result)
    print(canonical(dict(n=len(rows),GT=result['GT'],common_core=len(common),
        full_G={a:(full['PriorG'][a]['correct'],full['PriorG'][a]['MCC'],full['PriorG'][a]['false_S']) for a in ARMS},
        core_raw={a:(core['raw'][a]['correct'],core['raw'][a]['MCC']) for a in ARMS},cost=costs['total_original_or_unknown_cny'])))

if __name__=='__main__':main()
