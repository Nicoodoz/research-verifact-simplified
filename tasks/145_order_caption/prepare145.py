"""CPU-only caption correction for original160 or the missing340; no GPU."""
from pathlib import Path
import argparse
import shutil
import statistics
import sys
import tarfile
import time

R = Path(__file__).resolve().parents[2]
P = R / '.local_models/145_order_caption'
sys.path.insert(0, str(R / 'tasks/105_brief_supervision'))
import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0, str(R / 'tasks/136_claim_repeat_transfer'))
from prompt136 import prompt_ids
from caption145 import replace_caption, OLD, NEW


def prepare(out, scope='screen160'):
    out = Path(out)
    if out.exists():
        raise FileExistsError('Prepared stage exists; preserve it')
    if scope not in ('screen160','old500'):raise ValueError('Only original160 or old500 is authorized')
    source = R / '.local_models/142_relevance_order' / scope / 'bundle/data'
    oldjob = c.read(source/'job.json')
    before = {r['id']:r for r in c.rows(source/'inputs.jsonl')}
    oldlengths = {r['id']:r for r in c.rows(source/'lengths.jsonl')}
    phases=c.read(R/'.local_models/134_author_baselines/job.json')['phases']
    fixed=[i for phase in phases[:(1 if scope=='screen160' else 2)] for i in phase['ids']]
    prior=[]
    if scope=='old500':
        prior_folder=P/'screen160/evidence/order_caption'
        prior_inputs={r['id']:r for r in c.rows(P/'screen160/bundle/data/inputs.jsonl')}
        for path in sorted(prior_folder.glob('*.json')):
            row=c.read(path)
            if (row.get('arm')!='order_caption' or row.get('adapter_sha256')!=oldjob['adapter_sha256']
                or not row.get('parsed',{}).get('valid') or row.get('finish_reason')!='stop'
                or row['prompt_token_sha256']!=prior_inputs[row['id']]['prompt_token_sha256']):
                raise ValueError('Wrong or invalid prior145 first answer')
            prior.append(dict(id=row['id'],source_path=path.relative_to(R).as_posix(),
                              source_file_sha256=c.sha(path),prompt_token_sha256=row['prompt_token_sha256']))
        if len(prior)!=160 or {r['id'] for r in prior}!=set(phases[0]['ids']):
            raise ValueError('Original145 screen160 is incomplete')
    needed=set(fixed)-{r['id'] for r in prior}
    expected=160 if scope=='screen160' else 340
    if oldjob['task'] != 142 or oldjob['arm'] != 'relevance_order' or len(before)!=expected or set(before)!=needed:
        raise ValueError('Require the exact missing original142/134 IDs')
    tok = CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b')
    records, lengths, edits = [], [], []
    for i in oldjob['ids']:
        row = before[i]
        original_ids = prompt_ids(tok, row)
        if c.digest(c.canonical(original_ids)) != row['prompt_token_sha256'] or len(original_ids) != oldlengths[i]['input_tokens']:
            raise ValueError('Frozen142 input fingerprint differs: '+i)
        reference, edit = replace_caption(row['reference'])
        changed = dict(id=i, claim=row['claim'], reference=reference,
                       source_prompt_token_sha256=row['prompt_token_sha256'])
        ids = prompt_ids(tok, changed)
        if len(ids)-len(original_ids)!=3:raise ValueError('Caption token difference changed: '+i)
        if len(ids)+384 > 16384:
            raise ValueError('Full prompt exceeds unchanged context: '+i)
        changed['prompt_token_sha256'] = c.digest(c.canonical(ids))
        records.append(changed)
        lengths.append(dict(id=i, input_tokens=len(ids), source_input_tokens=len(original_ids),
            prompt_token_sha256=changed['prompt_token_sha256'], source_prompt_token_sha256=row['prompt_token_sha256'],
            claim_repeat_input_tokens=oldlengths[i]['source_input_tokens'],
            claim_repeat_prompt_token_sha256=row['source_prompt_token_sha256']))
        edits.append(dict(id=i, **edit, token_delta=len(ids)-len(original_ids),
                          old_reference_sha256=c.digest(row['reference']), new_reference_sha256=c.digest(reference)))
    # Keep the original142 grouping and order, including its first formal batch.
    batches = oldjob['batches']
    if sorted(i for batch in batches for i in batch) != sorted(before):
        raise ValueError('Original142 batches do not cover this phase once')
    compute_seconds=750 if scope=='screen160' else 1000
    job = dict(oldjob, task=145, arm='order_caption', scope=scope, expected_N=expected,
        target_N=len(fixed), prior_N=len(prior), prior_ids=sorted(r['id'] for r in prior),
        batches=batches, compute_limit_seconds=compute_seconds, save_reserve_seconds=180,
        transform='global_sort_caption_only', source_task=142,
        source_job_sha256=c.sha(source/'job.json'), source_inputs_sha256=c.sha(source/'inputs.jsonl'),
        new_training=False, no_shutdown=True, no_new_algorithm=True,
        caption_change=dict(old=OLD,new=NEW,start=123),caption_edits_file='data/caption_edits.jsonl')
    B = out/'bundle'
    c.putl(B/'data/inputs.jsonl',records)
    c.putl(B/'data/lengths.jsonl',lengths)
    c.putl(out/'caption_edits.jsonl',edits)
    c.putl(B/'data/caption_edits.jsonl',edits)
    job['caption_edits_sha256']=c.sha(B/'data/caption_edits.jsonl')
    if prior:
        c.putl(B/'data/prior_receipt_manifest.jsonl',prior)
        job.update(prior_receipt_manifest='data/prior_receipt_manifest.jsonl',
                   prior_receipt_manifest_sha256=c.sha(B/'data/prior_receipt_manifest.jsonl'))
    c.put(B/'data/job.json',job)
    c.put(out/'job.json',job)
    shutil.copy2(source/'session.json',B/'data/session.json')
    files = ['tasks/145_order_caption/worker145.py', 'tasks/136_claim_repeat_transfer/prompt136.py',
             'tasks/104_supervision_evidence/training104.py', 'tasks/105_brief_supervision/common105.py',
             'tasks/105_brief_supervision/parse105.py']
    for rel in files:
        dest=B/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
        compile(dest.read_text(encoding='utf-8-sig'),rel,'exec')
    shutil.copy2(R/'tasks/145_order_caption/start145.py',out/'start.py')
    with tarfile.open(out/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for file in B.rglob('*'):
            if file.is_file():archive.add(file,arcname=file.relative_to(B),recursive=False)
    deltas=[r['token_delta'] for r in edits]
    result=dict(task=145,status='CPU_PREPARED_NOT_RUN',scope=scope,N=expected,target_N=len(fixed),prior_N=len(prior),
        source142_IDs_and_batches_unchanged=True, only_caption_changed=True, original_GT_untouched=True,
        old_caption=OLD,new_caption=NEW,caption_offset=123,
        token_delta=dict(min=min(deltas),median=statistics.median(deltas),max=max(deltas),sum=sum(deltas)),
        max_input_tokens=max(r['input_tokens'] for r in lengths),context_tokens=16384,max_new_tokens=384,
        compute_limit_seconds=compute_seconds,save_reserve_seconds=180,source_adapter_sha256=job['adapter_sha256'],
        bundle_sha256=c.sha(out/'bundle.tar.gz'),bundle_bytes=(out/'bundle.tar.gz').stat().st_size,
        no_GPU=True,no_API=True,no_new_algorithm=True,created_epoch=time.time())
    c.put(out/'preparation.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',choices=('screen160','old500'),default='screen160')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    print(c.canonical(prepare(args.out or P/args.scope,args.scope)))


if __name__=='__main__':main()
