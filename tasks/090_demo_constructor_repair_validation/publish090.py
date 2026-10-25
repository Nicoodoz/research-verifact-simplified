"""Publish only metrics, IDs/hashes and source-free prediction fields; keep native text private."""
from common090 import *
def main():
    for name in ('analysis.json','cost_ledger.json','attempt_ledger.jsonl','attribution_cases.jsonl'):
        if name.endswith('jsonl'):putl(PUB/name,lines(OUT/name))
        else:put(PUB/name,read(OUT/name))
    rows=[]
    for x in lines(OUT/'predictions.jsonl'):
        keep={k:x[k] for k in ('id','sid','author','panel','GT','labels','reference_sha256','selection_tier','in_frozen085','teaching_candidate_patient_overlap')}
        keep['arms']={a:{k:v[k] for k in ('valid','raw_valid','scores_valid','raw_verdict','scores','status','finish_reason','usage','fallback_used','raw_fallback_used','elapsed_seconds','request_id','body_sha256','receipt_sha256')} for a,v in x['arms'].items()}
        rows.append(keep)
    putl(PUB/'predictions_public.jsonl',rows)
    # Every private artifact remains available locally with a checksum; never add it to Git.
    put(PUB/'private_artifact_manifest.json',dict(private_root=OUT.relative_to(ROOT).as_posix(),licensed_material_required=True,
        sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='run.lock'}))
    print(canonical(dict(public_predictions=len(rows),clinical_text_published=False)))
if __name__=='__main__':main()
