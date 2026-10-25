"""One pre-outcome budget revision: 240 target exceeds conservative busy forecast."""
import importlib.util, json
from collections import defaultdict
import common097 as c
from prepare_a import original_style_prompt

def main():
    panel=c.lines(c.OUT/'a_panel.jsonl'); jobs=c.lines(c.PRIVATE/'a_jobs.jsonl')
    # Verify exact upstream prompt text; this must hold before any paid request.
    source=c.ROOT/'.local_models/097_upstream/packages/llm_judge/src/llm_judge/prompts.py'
    spec=importlib.util.spec_from_file_location('upstream097',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    x=c.read(c.ROOT/'.local_models/094/judge_template.json')
    assert module.system_prompt_judge()=="You are judging whether text written about a patient is supported by information from the patient's electronic health record."
    for claim,reference in [('Claim X','Reference Y'),('a\nb','a\t文')]:
        payload=json.dumps({'text':claim,'reference':reference},ensure_ascii=False,indent=4)
        assert original_style_prompt(claim,reference)==module.prompt_determine_verdict_reasoning(payload)
    groups=defaultdict(list)
    for r in panel:groups[tuple(r['stratum'])].append(r)
    target=160;quota={k:int(target*len(v)/len(panel)) for k,v in groups.items()}
    frac={k:target*len(v)/len(panel)-quota[k] for k,v in groups.items()}
    for k in sorted(groups,key=lambda k:(-frac[k],k))[:target-sum(quota.values())]:quota[k]+=1
    ids=set()
    for k,rr in groups.items():
        ids.update(r['id'] for r in sorted(rr,key=lambda r:c.digest('097/A/budget160/v1/'+r['id']))[:quota[k]])
    selected=[r for r in panel if r['id'] in ids];selected_jobs=[j for j in jobs if j['id'] in ids]
    assert len(selected)==160 and len(selected_jobs)==480
    c.write_lines(c.OUT/'a_execution_panel.jsonl',selected)
    c.write_lines(c.PRIVATE/'a_execution_jobs.jsonl',selected_jobs)
    c.write_json(c.OUT/'a_execution_freeze.json',dict(utc=c.utc(),N=160,job_count=480,patients=len({r['sid'] for r in selected}),strata={str(k):v for k,v in quota.items()},selection='Budget revision before new outcomes: within originally frozen 240, GT×author proportional fixed SHA256 097/A/budget160/v1/ID; 80 omitted IDs locked out of A development',reason='240×3 new requests: conservative p95 no-cache busy-price forecast ¥54.38 exceeds ¥18 operating allowance. 160 still cost-controlled by per-request hard reservation; actual cost could stop early.',forecast_reference=c.sha(c.OUT/'a_forecast.json'),upstream_prompt_sha256=c.sha(source),jobs_sha256=c.sha(c.PRIVATE/'a_execution_jobs.jsonl'),panel_sha256=c.sha(c.OUT/'a_execution_panel.jsonl'),hard_cap_cny=20,operating_cap_cny=18,unknown_reserve_cny=2))
    print('frozen A N=160, patients',len({r['sid'] for r in selected}),'jobs',len(selected_jobs))
if __name__=='__main__':main()
