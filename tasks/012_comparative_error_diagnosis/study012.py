"""012 offline comparison with frozen 010 contemporaneous responses."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/012_comparative_error_diagnosis'
sys.path.insert(0,str(ROOT/'tasks/010_verifact_baseline_alignment'))
import alignment_common as source
pilot=source.pilot
read_json=source.read_json
RAW=source.RAW
TEN=ROOT/'outputs/010_verifact_baseline_alignment'
NINE=ROOT/'outputs/009_retrieval_baselines/confirmation_001'
BASE_HEAD='b710543fd5caf8ca9b9017ec230cac9ac242f721'
SYSTEMS=('O','V','C')
LAYERS=('target_evaluation','raw_records_scope','segmentation_index','query_recall','candidate_retention','rerank_selection','reference_packaging','final_reference','judge','output_processing')
MECHANISMS=('scope_sufficiency','time','event_identity','state_plan_execution','terminology_modality','negation_conflict','complementary_evidence','local_context_loss','distractor_or_redundancy','record_availability','processing_difference','uncertain')

def seal(out,dependencies,code):
    from datetime import datetime,timezone
    pilot.write_json(out/'manifest.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=BASE_HEAD,
        dependencies={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in dependencies},
        code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in code},
        files={p.relative_to(out).as_posix():pilot.digest_file(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}))

def check(out):
    m=read_json(out/'manifest.json')
    for path,h in m['files'].items():assert pilot.digest_file(out/path)==h,('output changed',path)
    for path,h in {**m.get('dependencies',{}),**m.get('code_sha256',{})}.items():assert pilot.digest_file(ROOT/path)==h,('source changed',path)
    return m

def direction(old,new,gt):
    return ('both_correct' if new==gt else 'old_correct_new_wrong') if old==gt else ('old_wrong_new_correct' if new==gt else 'both_wrong')

def final_json(text):
    import re,json
    candidates=[]
    for m in re.finditer(r'\{',text or ''):
        try:v,length=json.JSONDecoder().raw_decode(text[m.start():])
        except json.JSONDecodeError:continue
        if isinstance(v,dict) and {'verdict','reason'}<=set(v):candidates.append(dict(start=m.start(),end=m.start()+length,value=v))
    return candidates
