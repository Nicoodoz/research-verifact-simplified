"""Freeze completed preparation, or read-only verify its hashes; never run GPU."""
import argparse
from pathlib import Path
import subprocess
import common106 as c


def verify(record):
    for relative,wanted in record['files'].items():
        path=(c.ROOT/relative).resolve()
        assert path.is_relative_to(c.ROOT.resolve()) and c.sha(path)==wanted,relative
    private=record['private_files']
    for relative,wanted in private.items():assert c.sha(c.ROOT/relative)==wanted,relative
    package=c.read(c.OUT/'implementation_package.json')
    bundle=Path(package['bundle'])
    for name,wanted in c.read(bundle/'manifest.json')['files'].items():
        assert c.sha(bundle/name)==wanted,name
        if name.startswith(('tasks/','src/')):assert c.sha(c.ROOT/name)==wanted,name
    assert c.sha(c.TASK/'config.json')==c.sha(bundle/'frozen/config.json')
    assert c.sha(c.OUT/'cost_estimate.json')==c.sha(bundle/'frozen/cost_estimate.json')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');a=p.parse_args()
    target=c.OUT/'preparation_freeze.json'
    if a.verify:
        verify(c.read(target));print(c.canonical(dict(freeze_verified=True,GPU_executed=False)));return
    if target.exists():raise FileExistsError('A preparation freeze already exists; verify it or create a separately recorded amendment')
    check=c.read(c.OUT/'final_selfcheck.json');assert check['status']=='READY_FOR_NEXT_GPU_DECISION'
    public=[p for root in (c.TASK,c.OUT) for p in root.rglob('*') if p.is_file() and p!=target]
    navigation=[c.ROOT/p for p in ('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/RUN_ENVIRONMENT.md','docs/TASK_INDEX.md')]
    private=[c.PRIVATE/(arm+'.jsonl') for arm in (*c.ARMS,*c.CANDIDATE_DATA_ARMS)]
    package=c.read(c.OUT/'implementation_package.json')
    record=dict(task=106,status='READY_FOR_NEXT_GPU_DECISION',
        main_HEAD=subprocess.check_output(['git','rev-parse','refs/heads/main'],cwd=c.ROOT,text=True).strip(),
        github_main_checked_at_start=dict(research_verifact='ec07089657d15d66aaf310199dad6b74b7b097a9',
            research_verifact_simplified='873e7088003cef33778cbf61ba59ae53f4347f8d'),
        preparation_authorization='user106 request; CPU/data/literature only, API cap10 actual0; clinical service permission explicitly confirmed',
        no_GPU_authorization_included=True,new_API_calls=0,new_GPU_calls=0,
        files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sorted(public+navigation)},
        private_files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in private},
        private_bundle_manifest_sha256=package['manifest_sha256'],private_archive_sha256=package['archive_sha256'],
        original196_and_105_outcomes_unchanged=True,default_unchanged=True,committed=False,pushed=False,
        not_a_method_effectiveness_or_independent_medical_audit=True)
    verify(record);c.put(target,record)
    print(c.canonical(dict(status=record['status'],files=len(record['files']),private_training_files=len(private),
                          preparation_freeze_sha256=c.sha(target),GPU_executed=False)))


if __name__=='__main__':main()
