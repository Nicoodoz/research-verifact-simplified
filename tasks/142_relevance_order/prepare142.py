"""CPU-only missing-ID preparation for one fixed lossless reference reorder."""
from pathlib import Path
import argparse,compileall,shutil,statistics,sys,tarfile,time
R=Path(__file__).resolve().parents[2];P=R/'.local_models/142_relevance_order';O=R/'outputs/142_relevance_order'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0,str(R/'tasks/140_kl_anchor'));from prepare_eval140 import read_source136
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'));from prompt136 import prompt_ids
from reorder142 import reorder_reference

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['screen160','old500','full1817'],default='screen160')
    ap.add_argument('--compute-seconds',type=int,default=900);a=ap.parse_args()
    if a.scope=='screen160' and a.compute_seconds!=900:raise ValueError('Frozen160 compute cap is900 seconds')
    if a.scope=='full1817' and a.compute_seconds!=3000:raise ValueError('Frozen full expansion compute cap is3000 seconds')
    source,lengths=read_source136()
    screen=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    keys={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/keys.jsonl')}
    old500={i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')}
    target=screen if a.scope=='screen160' else (old500 if a.scope=='old500' else set(keys))
    prior={}
    if a.scope!='screen160':
        previous='screen160' if a.scope=='old500' else 'old500'
        report=c.read(O/('relevance_order_'+previous+'.json'))
        if report['screening']['continue_signal'] is not True:raise ValueError('No prior fixed screening signal')
        for stage in (('screen160',) if a.scope=='old500' else ('screen160','old500')):
            for file in (P/stage/'evidence/relevance_order').glob('*.json'):
                row=c.read(file)
                if row['id'] in prior:raise ValueError('Duplicate prior142 first response')
                if row.get('adapter_sha256')!=report['source_adapter_sha256']:raise ValueError('Prior source adapter differs')
                prior[row['id']]=row
        if set(prior)!=(screen if a.scope=='old500' else old500):raise ValueError('Prior first responses incomplete')
    needed=target-set(prior);expected={'screen160':160,'old500':340,'full1817':1317}[a.scope]
    assert len(needed)==expected
    work=P/a.scope;B=work/'bundle'
    if work.exists():raise FileExistsError('Prepared stage exists; inspect, never overwrite')
    tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b')
    records=[];outlengths=[];maps=[]
    for i in sorted(needed):
        before=source[i];reference,manifest=reorder_reference(before['reference'],before['claim'])
        after=dict(id=i,claim=before['claim'],reference=reference,
                   source_prompt_token_sha256=before['prompt_token_sha256'])
        ids=prompt_ids(tok,after);after['prompt_token_sha256']=c.digest(c.canonical(ids))
        if len(ids)+384>16384:raise ValueError('Full transformed input exceeds fixed context: '+i)
        records.append(after);outlengths.append(dict(id=i,input_tokens=len(ids),source_input_tokens=lengths[i]['input_tokens'],
            prompt_token_sha256=after['prompt_token_sha256'],source_prompt_token_sha256=before['prompt_token_sha256']))
        maps.append(dict(id=i,**manifest))
    newlen={x['id']:x['input_tokens'] for x in outlengths}
    order=sorted(needed,key=lambda i:(lengths[i]['input_tokens'],i));batches=[];cursor=0
    while cursor<len(order):
        group=order[cursor:cursor+(2 if lengths[order[cursor]]['input_tokens']<=12701 else 1)]
        if max(newlen[i] for i in group)>12701:group=group[:1]
        batches.append(group);cursor+=len(group)
    first=max(range(len(batches)),key=lambda k:max(newlen[i] for i in batches[k]))
    batches=[batches[first]]+batches[:first]+batches[first+1:]
    settings=c.read(R/'.local_models/141_two_demos/source/settings.json')
    settings['max_seq_length']=16384
    settings['generation'].update(batch_size=2,single_if_prompt_above=12701)
    job=dict(settings,task=142,arm='relevance_order',scope=a.scope,inputs='data/inputs.jsonl',
             expected_N=len(needed),target_N=len(target),prior_N=len(prior),ids=order,batches=batches,
             first_formal_IDs=batches[0],compute_limit_seconds=a.compute_seconds,save_reserve_seconds=600,
             new_training=False,no_shutdown=True,transform='fixed008_bm25_desc_stable_full_fragments')
    c.putl(B/'data/inputs.jsonl',records);c.putl(B/'data/lengths.jsonl',outlengths);c.putl(work/'source_maps.jsonl',maps)
    c.put(B/'data/job.json',job);c.put(work/'job.json',job)
    c.put(B/'data/session.json',c.read(R/'.local_models/141_two_demos/source/session.json'))
    rels=['tasks/142_relevance_order/worker142.py','tasks/136_claim_repeat_transfer/prompt136.py',
          'tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']
    for rel in rels:
        dest=B/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
        compile(dest.read_text(encoding='utf-8-sig'),rel,'exec')
    shutil.copy2(R/'tasks/142_relevance_order/start142.py',work/'start.py')
    with tarfile.open(work/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for file in B.rglob('*'):
            if file.is_file():archive.add(file,arcname=file.relative_to(B),recursive=False)
    delta=[r['input_tokens']-r['source_input_tokens'] for r in outlengths]
    summary=dict(task=142,status='CPU_PREPARED_NOT_RUN',scope=a.scope,expected_N=len(needed),target_N=len(target),
        original_GTs_untouched=True,no_reference_fragment_dropped=True,max_input_tokens=max(newlen.values()),
        input_token_delta=dict(min=min(delta),median=statistics.median(delta),max=max(delta),sum=sum(delta)),
        first_formal_IDs=batches[0],compute_limit_seconds=a.compute_seconds,save_reserve_seconds=600,
        source_adapter_sha256=job['adapter_sha256'],bundle_sha256=c.sha(work/'bundle.tar.gz'),
        bundle_bytes=(work/'bundle.tar.gz').stat().st_size,no_GPU=True,new_API=0,created_epoch=time.time())
    c.put(work/'preparation.json',summary);c.put(O/(a.scope+'_preparation.json'),summary)
    print(c.canonical(summary))

if __name__=='__main__':main()
