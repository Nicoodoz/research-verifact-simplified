"""Stream hashes of this task's results; never copy/delete model source files."""
from pathlib import Path
import common105 as c

def save(work):
    work=Path(work)
    files={}
    for path in sorted(work.rglob('*')):
        if path.is_file() and path.name not in {'saved_outputs_manifest.json'} and not path.name.endswith(('.lock','.tmp')):
            files[path.relative_to(work).as_posix()]=dict(bytes=path.stat().st_size,sha256=c.sha(path))
    result=dict(utc=c.utc(),scope='105 results/checkpoints only; original103 untouched',files=files,
                base_weights_copied=False,files_deleted=False,platform_shutdown_confirmation_separate=True)
    c.put(work/'saved_outputs_manifest.json',result)
    return result
