"""Freeze stratified natural panel and exact A request bodies before new outcomes."""
import copy, json, statistics, sys
from collections import Counter, defaultdict
import duckdb
import pandas as pd
import common097 as c

SYSTEM='You are judging whether text written about a patient is supported by information from the patient\'s electronic health record.'
def original_style_prompt(text, reference):
    payload=json.dumps({'text':text,'reference':reference},ensure_ascii=False,indent=4)
    return f'''## Task:
Using the provided reference from the patient's electronic health record, determine whether the text is supported, not supported, or not addressed by the reference context.

## Detailed Instructions:
1. Compare the text and reference, which is provided in the "text" and "reference" keys of the input JSON object.
2. You may think about the task before answering.
3. Provide a verdict in the output JSON object under the key "verdict".
    a. Determine whether the text is addressed or not addressed by the reference context.
    b. If the text is not addressed by the reference context, output the verdict "Not Addressed".
    c. If the text is addressed and fully supported by the reference context, output the verdict "Supported".
    d. If the text is addressed and not fully supported by the reference context, output the verdict "Not Supported". This includes cases where the text is only partially supported by the reference context.
    e. The only valid outputs are "Supported", "Not Supported", or "Not Addressed".
    d. When determining a verdict, consider the information in the reference context to be correct and the source of truth.
4. Provide a reason for your verdict in the output JSON object under the key "reason". Try to make your reason concise and to the point. You must provide a reason. Do not leave it blank.
5. Format your response as a JSON object with the keys "verdict" and "reason". Return only JSON.

## Input JSON:
{payload}'''

def main():
    natural=c.lines(c.ROOT/'outputs/096_r1_native_priorg/main_panel.jsonl')
    allb={r['id']:r for r in c.lines(c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl')}
    inp={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')}
    eligible=[r for r in natural if r['eligible'] and r['id'] in allb and r['id'] in inp and allb[r['id']]['B_present']]
    by=defaultdict(list)
    for r in eligible:by[(r['author'],r['GT'])].append(r)
    target=240;den=len(eligible)
    exact={k:target*len(v)/den for k,v in by.items()}
    quota={k:int(v) for k,v in exact.items()}
    for k in sorted(by,key=lambda k:(-(exact[k]-quota[k]),str(k)))[:target-sum(quota.values())]:quota[k]+=1
    chosen=[]
    for k,v in by.items():chosen.extend(sorted(v,key=lambda r:c.digest('097/A/v1/'+r['id']))[:quota[k]])
    chosen=sorted(chosen,key=lambda r:c.digest('097/A/order/v1/'+r['id']))
    ids=[r['id'] for r in chosen]
    with duckdb.connect() as db:
        db.register('wanted',pd.DataFrame({'proposition_id':ids}))
        vals=db.execute('SELECT v.proposition_id,v.reference_id,v.verdict FROM read_parquet(?) v JOIN wanted USING(proposition_id) WHERE rater_alias=?',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet'),'v1.1.0-rater-121']).fetchall()
        assert len(vals)==len(ids)==len({r[0] for r in vals})
        db.register('refids',pd.DataFrame({'reference_id':list({r[1] for r in vals})}))
        refs=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN refids USING(reference_id)',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/reference_payloads.parquet')]).fetchall())
    vals={pid:(rid,v) for pid,rid,v in vals}
    template=c.read(c.ROOT/'.local_models/094/judge_template.json')
    assert template['model']==c.MODEL and template['enable_thinking'] and template['reasoning_effort']=='high' and template['max_tokens']==8192
    panel=[];jobs=[]
    for r in chosen:
        pid=r['id'];x=inp[pid];b=allb[pid];rid,orig=vals[pid]
        assert r['GT']==b['GT'] and r['author']==b['author'] and c.digest(x['text'])==b['claim_sha256'] and c.digest(x['reference'])==b['reference_sha256']
        assert c.digest(refs[rid])==rid
        panel.append(dict(id=pid,sid=r['sid'],author=r['author'],GT=r['GT'],stratum=[r['author'],r['GT']],C48_sha256=c.digest(x['reference']),published_reference_id=rid,published_verdict=orig,C48_chars=len(x['reference']),published_chars=len(refs[rid]),B_raw=b['predictions']['B_raw'],B_PriorG=b['predictions']['B_PriorG'],B_receipt_path=b['B']['receipt_path'],B_request_path=b['B']['request_path']))
        for arm,reference in [('C48_native',x['reference']),('published_native',refs[rid]),('published_B',refs[rid])]:
            body=copy.deepcopy(template)
            if arm.endswith('native'):
                body['messages']=[{'role':'system','content':SYSTEM},{'role':'user','content':original_style_prompt(x['text'],reference)}]
                body.pop('response_format',None)
            else:
                body['messages'][1]['content']=json.dumps({'proposition':x['text'],'reference':reference},ensure_ascii=False,separators=(',',':'))
            jobs.append(dict(id=pid,arm=arm,body=body,body_sha256=c.digest(c.canonical(body)),reference_sha256=c.digest(reference),input_chars=len(reference),request_id=c.digest('097/A/'+arm+'/'+pid)[:28],bound_cny=((len(c.canonical(body).encode('utf-8'))+2000)*3+8192*9)/1e6))
    c.write_lines(c.OUT/'a_panel.jsonl',panel)
    c.write_lines(c.PRIVATE/'a_jobs.jsonl',jobs)
    stats=dict(utc=c.utc(),head='71c183aab93cc947cbd99b2b8dd30ebfee251944',eligible=len(eligible),N=len(panel),strata={str(k):v for k,v in quota.items()},patients=len({r['sid'] for r in panel}),arms=['C48_B_cached','published_B','C48_native','published_native'],model=c.MODEL,thinking='high',max_tokens=8192,selection='GT×author proportional largest remainder; fixed SHA256 097/A/v1/ID within strata; no outcome or PriorG selection',evaluation='valid atomic natural claims, same ID raw primary, 1000 patient cluster bootstrap',baseline_choice='Any B method must exceed strongest A raw point estimate on paired development data; no posthoc switching within B',C48_char_mean=statistics.mean(r['C48_chars'] for r in panel),published_char_mean=statistics.mean(r['published_chars'] for r in panel),max_bound_cny=sum(j['bound_cny'] for j in jobs),source_sha256={str(p.relative_to(c.ROOT)):c.sha(p) for p in [c.ROOT/'outputs/096_r1_native_priorg/main_panel.jsonl',c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl',c.ROOT/'.local_models/092/inputs.jsonl',c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet',c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/reference_payloads.parquet']},jobs_sha256=c.sha(c.PRIVATE/'a_jobs.jsonl'))
    c.write_json(c.OUT/'a_freeze.json',stats)
    print({k:stats[k] for k in ['N','patients','strata','C48_char_mean','published_char_mean','max_bound_cny']})

if __name__=='__main__':main()
