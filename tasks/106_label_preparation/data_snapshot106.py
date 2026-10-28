"""Preserve first audited 106 draft before specific source-gap isolation."""
from pathlib import Path
import shutil
from data106 import ROOT, OUT, PRIVATE, put, sha

def main():
    target=PRIVATE/'drafts_v1'
    files=[PRIVATE/f'{arm}.jsonl' for arm in ('ordinary_sample','boundary_cover')]
    files += list(OUT.glob('data_*.json*'))
    files += [ROOT/'tasks/106_label_preparation/data106.py',ROOT/'tasks/106_label_preparation/probe106.py']
    manifest={}
    for source in files:
        relative=source.relative_to(ROOT)
        destination=target/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():assert sha(destination)==sha(source),'Immutable draft snapshot already differs'
        else:shutil.copy2(source,destination)
        manifest[relative.as_posix()]=sha(source)
    put(target/'snapshot.json',dict(reason='Frozen selection before fixed min/median/max source-pair audit correction',files=manifest))
    preserved=OUT/'data_pair_audit_source_v1.jsonl'
    source=OUT/'data_boundary_cover_pairs.jsonl'
    if preserved.exists():assert sha(preserved)==sha(source)
    else:shutil.copy2(source,preserved)
    print('First audited draft snapshot preserved; no historical 103-105 artifact changed.')

if __name__=='__main__':main()
