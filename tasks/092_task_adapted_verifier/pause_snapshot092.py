"""Read-only checkpoint inspection on CPU; no training/inference or GPU allocation."""
import torch
import common092 as c

def main():
    folder=c.PRIVATE/'finetuned_fold0'
    path=folder/'resume.pt'
    checkpoint=torch.load(path,map_location='cpu',weights_only=False)
    assert checkpoint['config_sha256']==c.sha(c.TASK/'config.json')
    snapshot=dict(status='PAUSED_BY_USER',utc=c.now(),API_calls=0,API_cost_cny=0,
        last_progress=c.read(c.OUT/'training_progress.json'),
        checkpoint=dict(path='.local_models/092/finetuned_fold0/resume.pt',sha256=c.sha(path),bytes=path.stat().st_size,
            completed_epochs=checkpoint['epoch'],active_epoch=checkpoint['epoch']+1,cursor=checkpoint['cursor'],
            order_length=len(checkpoint['order']) if checkpoint['order'] is not None else None,
            best=checkpoint['best'],optimizer_steps=checkpoint['steps'],non_skipped_updates=checkpoint['updates'],
            elapsed_seconds=checkpoint['elapsed'],optimizer_saved='optimizer' in checkpoint,RNG_saved='rng' in checkpoint),
        completed_models=[p.parent.name for p in c.OUT.glob('*_fold*/complete.json')],
        incomplete_training_history_epochs=len(checkpoint['history']),
        final_evaluation_complete=False,independent_audit=False)
    snapshot['private_artifacts']={str(p.relative_to(c.ROOT)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=c.sha(p)) for p in [folder/'best.pt',c.PRIVATE/'inputs.jsonl']}
    c.put(c.OUT/'pause_snapshot.json',snapshot)
    print(snapshot,flush=True)
if __name__=='__main__':main()
