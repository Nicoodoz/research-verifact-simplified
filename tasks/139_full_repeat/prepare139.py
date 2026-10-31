"""Reuse frozen CPU inputs/lengths; make only missing-ID139 bundles, no tokenization."""
from pathlib import Path
import argparse, json, shutil, sys, tarfile
R = Path(__file__).resolve().parents[2]; P = R/'.local_models/139_full_repeat'; O = R/'outputs/139_full_repeat'
sys.path.insert(0, str(R/'tasks/105_brief_supervision'))
import common105 as c


def main():
    p = argparse.ArgumentParser(); p.add_argument('--scope', required=True, choices=['screen160','old500','full1817'])
    p.add_argument('--prior', type=Path, nargs='*', default=[])
    p.add_argument('--compute-seconds', type=int, default=2700)
    a = p.parse_args()
    if a.compute_seconds < 300: raise ValueError('Computation allocation too short')
    if a.scope == 'screen160' and a.compute_seconds != 2700: raise ValueError('Frozen screen computation cap2700s')
    source = P/'source'
    rows = {r['id']: r for r in c.rows(source/'all1817_inputs.jsonl')}
    lengths = {r['id']: r for r in c.rows(source/'all1817_lengths.jsonl')}
    keys = {r['id']: r for r in c.rows(source/'keys.jsonl')}
    screen = set(c.read(source/'screen160_ids.json'))
    assert len(rows) == len(lengths) == len(keys) == 1817 and len(screen) == 160
    target = screen if a.scope == 'screen160' else ({i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')} if a.scope == 'old500' else set(rows))
    prior = {}
    for folder in a.prior:
        for f in folder.glob('*.json'):
            row = c.read(f)
            if 'id' not in row: continue
            i = row['id']
            if i not in target or row.get('arm') != 'full_repeat': raise ValueError('Unexpected prior receipt')
            if row.get('adapter_sha256') != c.read(source/'settings.json')['adapter_sha256']: raise ValueError('Changed weights')
            if row['prompt_token_sha256'] != rows[i]['prompt_token_sha256']: raise ValueError('Changed prompt')
            if i in prior and prior[i] != row: raise ValueError('Conflicting first receipts')
            prior[i] = row
    required = set() if a.scope == 'screen160' else (screen if a.scope == 'old500' else {i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')})
    if not required <= set(prior): raise ValueError('Prior phase has missing first receipts; no automatic expansion')
    needed = sorted(target-set(prior), key=lambda i:(-lengths[i]['input_tokens'],i))
    if not needed: raise ValueError('No new IDs; successful or invalid first receipts are not rerun')
    run = P/a.scope; B = run/'bundle'
    if run.exists(): raise FileExistsError('Prepared phase exists; preserve and inspect')
    c.putl(B/'data/inputs.jsonl', [rows[i] for i in needed])
    c.putl(B/'data/lengths.jsonl', [lengths[i] for i in needed])
    session = c.read(source/'session.json'); session['save_reserve_seconds'] = 900
    c.put(B/'data/session.json', session)
    settings = c.read(source/'settings.json')
    job = dict(settings, task=139, name='full_repeat_'+a.scope, variant='full_repeat', scope=a.scope,
        inputs='data/inputs.jsonl', expected_N=len(needed), target_N=len(target), prior_N=len(prior),
        ids=needed, first_formal_ID=needed[0], compute_limit_seconds=a.compute_seconds,
        save_reserve_seconds=900, total_stage_limit_seconds=a.compute_seconds+900,
        first_receipts_only=True, no_training=True, no_shutdown=True)
    c.put(B/'data/job.json', job); c.put(run/'job.json', job)
    files=['tasks/139_full_repeat/'+n for n in ['prompt139.py','budget139.py','worker139.py','controller139.py']]
    files += ['tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']
    for rel in files:
        dest=B/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(R/rel,dest)
    shutil.copy2(R/'tasks/139_full_repeat/start139.py',run/'start.py')
    with tarfile.open(run/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for file in B.rglob('*'):
            if file.is_file(): archive.add(file,arcname=file.relative_to(B),recursive=False)
    summary=dict(task=139,status='PREPARED_NOT_RUN',scope=a.scope,target_N=len(target),prior_N=len(prior),new_calls=len(needed),
        prior_invalid=sum(not r['parsed']['valid'] for r in prior.values()),max_input_tokens=max(lengths[i]['input_tokens'] for i in needed),
        first_formal_ID=needed[0],source='Reuse frozen input/token-SHA/lengths; no CPU retokenization',
        compute_limit_seconds=a.compute_seconds,save_reserve_seconds=900,total_stage_limit_seconds=a.compute_seconds+900,
        global_budget_CNY=session['GPU_cap_CNY'],global_start=session['start_local'],new_API_CNY=0,new_training=False)
    c.put(run/'preparation.json',summary); c.put(O/(a.scope+'_preparation.json'),summary)
    print(c.canonical(summary))


if __name__ == '__main__': main()
