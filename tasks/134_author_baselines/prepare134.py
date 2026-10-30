"""Freeze the exact upstream prompt, existing1817 IDs, cache audit and GPU bundle."""
from pathlib import Path
import ast,hashlib,inspect,json,shutil,sys,tarfile,urllib.request
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'.local_models/134_author_baselines';O=ROOT/'outputs/134_author_baselines'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0,str(ROOT/'tasks/103_lora_selection'))
from prompt103 import original_style_prompt
from prompt134 import SYSTEM,prompt_determine_verdict_reasoning,prompt_ids

def main():
    P.mkdir(exist_ok=True);O.mkdir(parents=True,exist_ok=True)
    url='https://raw.githubusercontent.com/philipchung/verifact/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/prompts.py'
    source=P/'upstream_prompts.py'
    if not source.exists():
        with urllib.request.urlopen(url,timeout=30) as r:source.write_bytes(r.read())
    tree=ast.parse(source.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('system_prompt_judge','prompt_determine_verdict_reasoning')]
    ns={'inspect':inspect};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
    probe=json.dumps({'text':'synthetic claim','reference':'synthetic reference'},ensure_ascii=False,indent=4)
    assert SYSTEM==ns['system_prompt_judge']()
    assert prompt_determine_verdict_reasoning(probe)==ns['prompt_determine_verdict_reasoning'](probe)
    assert original_style_prompt('synthetic claim','synthetic reference')==prompt_determine_verdict_reasoning(probe)
    keys=c.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    raw=c.rows(ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')
    ki={r['id']:r for r in keys};ri={r['id']:r for r in raw}
    assert len(ki)==len(keys)==len(ri)==len(raw)==1817 and set(ki)==set(ri)
    assert len({r['sid'] for r in keys})==20
    assert sum(r['old_panel']=='natural' for r in keys)==400 and sum(r['old_panel']=='pressure' for r in keys)==100
    assert sum(r['subset']=='new' for r in keys)==1317
    old=c.rows(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl')
    old_ids={r['id'] for r in old};assert len(old_ids)==180 and old_ids<=set(ki)
    assert all(r['paper_r1'] in c.LABELS for r in keys)
    tok=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    inputs=[];lengths=[]
    for i in sorted(ki):
        x={k:ri[i][k] for k in ('id','claim','reference')}
        ids=prompt_ids(tok,x);x['prompt_token_sha256']=c.digest(c.canonical(ids))
        assert len(ids)+768<=16384
        inputs.append(x);lengths.append(dict(id=i,input_tokens=len(ids)))
    b=P/'bundle';c.putl(b/'data/inputs.jsonl',inputs)
    c.putl(P/'keys.jsonl',keys);c.putl(P/'lengths.jsonl',lengths)
    start=datetime.fromisoformat('2026-10-30T23:40:00+08:00').timestamp()
    session=dict(start_epoch=start,start_local='2026-10-30T23:40:00+08:00',hourly_CNY=1.58,GPU_cap_CNY=16.,API_cap_CNY=80.,API_spent_CNY=0.,no_shutdown=True,save_reserve_seconds=300,price_basis='same instance documented hourly rate; platform invoice not verified')
    c.put(b/'data/session.json',session);c.put(P/'session.json',session)
    proof=c.read(ROOT/'.local_models/120_full_pool_sft/resume369/evidence/full_pool_sft/train/checkpoint_b/checkpoint_complete.json')
    adapter=ROOT/'.local_models/120_full_pool_sft/resume369/evidence/full_pool_sft/train/checkpoint_b'
    job=dict(task=134,arms=['author_base9b','author_lora9b'],model_dir='/root/verifact_image/models/qwen3.5-9b',adapter='/root/autodl-tmp/verifact134/adapter120',adapter_bytes=(adapter/'adapter_model.safetensors').stat().st_size,
        max_seq_length=16384,inputs='data/inputs.jsonl',session='data/session.json',expected_N=1817,
        generation=dict(dtype='bfloat16',thinking=False,max_new_tokens=768,do_sample=False,num_beams=1,repetition_penalty=1.,batch_size=2,single_if_prompt_above=12500),
        parser='parse103.parse_content; EOS required; reason presence tracked separately',template_source=url,template_sha256=c.sha(source),first_receipts_only=True)
    screen=c.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    old500={r['id'] for r in keys if r['old_panel'] in ('natural','pressure')}
    assert len(screen)==160 and set(screen)<=old500
    job['phases']=[dict(name='screen160',ids=screen),dict(name='old340',ids=sorted(old500-set(screen))),dict(name='new1317',ids=sorted(set(ki)-old500))]
    c.put(b/'data/job.json',job);c.put(P/'job.json',job)
    cache={};by_input={r['id']:r for r in inputs}
    old_job=c.read(ROOT/'.local_models/120_full_pool_sft/native_reason_check/job.json')
    assert old_job['final369_proof']['steps']==369
    for arm in job['arms']:
        prior=old_ids if arm=='author_base9b' else set()
        sub='base_original9b' if arm=='author_base9b' else 'final369_120'
        reasons=list((ROOT/'.local_models/120_full_pool_sft/native_reason_check/evidence'/sub).glob('*.json'))
        cached=prior|{c.read(f)['id'] for f in reasons};matched=[];invalid=[]
        for f in reasons:
            r=c.read(f);i=r['id']
            assert r['prompt_token_sha256']==by_input[i]['prompt_token_sha256']
            assert r['adapter_sha256']==(None if arm=='author_base9b' else old_job['final369_proof']['adapter_sha256'])
            valid=bool(r['parsed']['label_parse_valid'] and r['finish_reason']=='stop')
            record=dict(r,arm=arm,parsed=dict(verdict=r['parsed']['verdict'],valid=valid,reason_present=bool(r['parsed'].get('reason'))),batch_size=1,cached_from=f.relative_to(ROOT).as_posix())
            c.put(b/'results'/arm/(i+'.json'),record);matched.append(i)
            if not valid:invalid.append(i)
        cache[arm]=dict(existing_related_ids=sorted(cached),configuration_matched_ids=sorted(matched),invalid_matched_ids=sorted(invalid),missing_ids=sorted(set(ki)-set(matched)),
            related103_N=len(prior),related_native_reason_N=len(reasons),exclusion='103: thinking4096/final768; other107/120/132:104 prompt and/or different weights; native20 has identical prompt/weights/decoding and is reused with recorded batch1')
    cache['paper_r1']=dict(existing_ids=sorted(ki),missing_ids=[],invalid_ids=[],new_calls=0)
    c.put(O/'cache_inventory.json',cache)
    c.putl(O/'cohort_ids.jsonl',[{k:r[k] for k in ('id','sid','GT','author','old_panel','subset','history103_panel')} for r in keys])
    summary=dict(stage='prepared',N=1817,patients=20,prompt_source=url,prompt_exact_text_verified=True,system_exact_text_verified=True,
        old103_template_equal=True,cache_matched={a:len(cache[a]['configuration_matched_ids']) for a in job['arms']},paper_r1_reused=1817,new_calls=sum(len(cache[a]['missing_ids']) for a in job['arms']),
        max_input_tokens=max(x['input_tokens'] for x in lengths),total_input_tokens=sum(x['input_tokens'] for x in lengths),generation=job['generation'],GPU_started=False)
    c.put(O/'preparation.json',summary)
    for rel in ['tasks/134_author_baselines/prompt134.py','tasks/134_author_baselines/worker134.py','tasks/103_lora_selection/parse103.py','tasks/105_brief_supervision/common105.py']:
        dest=b/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest)
    with tarfile.open(P/'bundle134.tar.gz','w:gz',compresslevel=1) as t:
        for f in b.rglob('*'):
            if f.is_file():t.add(f,arcname=f.relative_to(b),recursive=False)
    print(c.canonical(summary))

if __name__=='__main__':main()
