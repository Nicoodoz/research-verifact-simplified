"""Complete the missing manifest only after byte-identical offline replay."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import study009 as s
from score009 import score

if __name__=="__main__":
    folder=s.OUT/"development_001"
    existing=folder/"analysis_001"
    replay=folder/"analysis_replay_001"
    with redirect_stdout(StringIO()):
        score(folder,"dev_judge",replay)
    checked=[]
    for p in existing.iterdir():
        if p.is_file():
            assert s.pilot.digest_file(p)==s.pilot.digest_file(replay/p.name),p.name
            checked.append(p.name)
    assert not (existing/"manifest.json").exists()
    s.seal(existing,[folder/"judge_preparation/manifest.json",folder/"preparation/manifest.json",s.OUT/"live/dev_judge/state.json"],
        [s.TASK/"score009.py",s.TASK/"io009.py"],dict(manifest_completion_after_relative_path_fix=True,byte_identical_replay_files=checked))
    s.pilot.write_json(folder/"analysis_completion.json",dict(reason="Only final manifest creation failed for a relative CLI path. CLI now resolves paths; all existing content files match independent offline rerun. Original files were not replaced.",
        verified_files=checked,api_calls=0,raw_answers_unchanged=True))
    print(s.pilot.canonical(dict(matching_files=len(checked),analysis="analysis_001",raw_answers_unchanged=True)))
