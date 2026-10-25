"""Prepare fixed114 calibration requests; no credentials/network access."""
from pathlib import Path
import sys,copy
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).parent
sys.path.insert(0,str(ROOT/'tasks/078_component_ablation'))
import common078 as old

def main():
    out=ROOT/'outputs/079_f4_priorg_adaptation';out.mkdir(exist_ok=False)
    # Derive separate task helpers/executor, preserving all historical sources.
    source=(ROOT/'tasks/078_component_ablation/common078.py').read_text(encoding='utf-8-sig')
    source=source.replace('Task078','Task079').replace("outputs/078_component_ablation","outputs/079_f4_priorg_adaptation").replace('CAP=30.','CAP=20.')
    with (TASK/'common079.py').open('x',encoding='utf-8',newline='\n') as f:f.write(source)
    source=(ROOT/'tasks/078_component_ablation/run078.py').read_text(encoding='utf-8-sig')
    source=source.replace('078 executor','079 executor').replace('30-CNY','20-CNY').replace('common078','common079').replace('FROZEN_BEFORE_078_API','FROZEN_BEFORE_079_API')
    with (TASK/'run079.py').open('x',encoding='utf-8',newline='\n') as f:f.write(source)
    sources={}
    def bind(p):sources[p.relative_to(ROOT).as_posix()]=old.sha(p)
    sf=ROOT/'outputs/071_judge_icl_feasibility/freeze.json';examples=old.read(sf)['examples'];bind(sf)
    demo_patients={e['sid'] for e in examples}
    cases=[]
    for name in ['screen_cases.jsonl','confirmation_cases_frozen.jsonl']:
        p=ROOT/'outputs/051_thinking_mode_validation'/name;bind(p)
        cases.extend(x for x in old.lines(p) if x['sid'] not in demo_patients)
    assert len(cases)==114 and len({x['sid'] for x in cases})==14
    assert dict(Counter(x['GT'] for x in cases))=={'Supported':36,'Not Supported':42,'Not Addressed':36}
    ext=ROOT/'outputs/078_component_ablation/f4_extension_001'
    ep=ext/'predictions.jsonl';cp=ext/'cohort_lists.json';bind(ep);bind(cp)
    ids=set(old.read(cp)['exclude_actual_example_patients352'])
    # Evaluation labels remain in their historical source; not copied to training or used for selection.
    evaluation=[dict(id=x['id'],sid=x['sid'],author=x['author'],arms=x['arms']) for x in old.lines(ep) if x['id'] in ids]
    trainpat={x['sid'] for x in cases};evalpat={x['sid'] for x in evaluation}
    assert len(evaluation)==352 and len(evalpat)==22 and not trainpat&evalpat and not (trainpat|evalpat)&demo_patients
    f4row=next(x for x in evaluation if 'F4' in x['arms'])
    templatepath=ROOT/f4row['arms']['F4']['request_source'];bind(templatepath)
    system=old.read(templatepath)['job']['body']['messages'][0]['content']
    native={};caseids={x['id'] for x in cases}
    for p in sorted((ROOT/'outputs/051_thinking_mode_validation/attempts').glob('*/request.json')):
        rq=old.read(p);j=rq['job'];rp=p.parent/'receipt.json'
        if j.get('id') not in caseids or j.get('condition')!='T-S' or not rp.exists():continue
        rc=old.read(rp);assert rc['request_sha256']==old.sha(p)
        if rc['transport']['http_status']!=200:continue
        assert j['id'] not in native
        parsed=old.parse(dict(scored=True,thinking=True),rc['transport'])
        assert parsed.get('model_returned')==old.MODEL
        native[j['id']]=dict(id=j['id'],body=j['body'],parsed=parsed,request_source=p.relative_to(ROOT).as_posix(),receipt_source=rp.relative_to(ROOT).as_posix())
        bind(p);bind(rp)
    assert set(native)==caseids
    jobs=[];training=[]
    for x in cases:
        b=copy.deepcopy(native[x['id']]['body']);assert b['model']==old.MODEL
        b['messages'][0]['content']=system
        j=dict(request_id='079_F4_'+old.digest(x['id'])[:24],id=x['id'],sid=x['sid'],arm='F4',stage='main',scored=True,thinking=True,body=b,body_sha256=old.digest(b))
        jobs.append(j);training.append(dict(id=x['id'],sid=x['sid'],GT=x['GT'],B=native[x['id']]))
    # Exact-body cache lookup across prior example tasks; first successful native answer only.
    wanted={j['body_sha256']:j for j in jobs};cached={}
    for folder in sorted((ROOT/'outputs').iterdir()):
        if not folder.is_dir() or not any(folder.name.startswith(f'{i:03}_') for i in range(71,79)):continue
        for p in sorted(folder.rglob('request.json')):
            if 'attempts' not in p.parts:continue
            rq=old.read(p);j=rq.get('job',{});body=j.get('body');rp=p.parent/'receipt.json'
            if not body or old.digest(body) not in wanted or not rp.exists():continue
            h=old.digest(body);rc=old.read(rp)
            if rc['transport']['http_status']!=200 or h in cached:continue
            assert rc['request_sha256']==old.sha(p);bind(p);bind(rp)
            cached[h]=dict(job=wanted[h],parsed=old.parse(wanted[h],rc['transport']),request_source=p.relative_to(ROOT).as_posix(),receipt_source=rp.relative_to(ROOT).as_posix())
    todo=[j for j in jobs if j['body_sha256'] not in cached];todo.sort(key=lambda j:old.digest('079/order/'+j['id']))
    old.jl(out/'main_jobs.jsonl',todo);old.jl(out/'calibration_cases.jsonl',training);old.jl(out/'evaluation_blind.jsonl',evaluation);old.jl(out/'reused_F4.jsonl',list(cached.values()))
    prior=ROOT/'outputs/053_thinking_prior_validation/freeze.json';bind(prior);old.put(out/'old_postprocessing.json',old.read(prior))
    for p in [TASK/'README.md',TASK/'prepare079.py',TASK/'common079.py',TASK/'run079.py',ROOT/'tasks/052_first_tier_validation/fit_calibration052.py',ROOT/'tasks/053_thinking_prior_validation/common053.py']:bind(p)
    old.put(out/'pricing.json',dict(checked_date='2026-09-24',source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',model=old.MODEL,input_cny_per_million=3,output_cny_per_million=9,cap_cny=20,expected_cny=len(todo)*.042))
    freeze=dict(status='FROZEN_BEFORE_079_API',created_utc=old.now(),cap_cny=20,model=old.MODEL,new_jobs=len(todo),reused_F4=len(cached),train_patients=sorted(trainpat),eval_patients=sorted(evalpat),train_n=114,eval_n=352,
                B_core_valid=sum(x['B']['parsed']['status'] in old.c53.VALID for x in training),source_sha256=sources,artifact_sha256={p.name:old.sha(p) for p in out.iterdir() if p.is_file()},gitignore_sha256=old.sha(ROOT/'.gitignore'))
    old.put(out/'freeze.json',freeze)
    print(old.canon({k:v for k,v in freeze.items() if k not in ['source_sha256','artifact_sha256','train_patients','eval_patients']}))

if __name__=='__main__':main()
