"""017 reuses fixed009/016 evidence and002 evaluation; import never calls services."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/017_verification_supervised_evidence_utility'
sys.path.insert(0,str(ROOT/'tasks/016_disagreement_triggered_review_validation'))
import common016 as old
from common016 import read,write_json,write_csv,write_lines,jsonlines,csvrows,canonical,fingerprint,file_hash,require,save,now,evaluate,paired_compare,LABELS
core=old.baseline.core
MODEL=old.V4
BASES={'old6':ROOT/'outputs/009_retrieval_baselines/confirmation_001','recent6':ROOT/'outputs/016_disagreement_triggered_review_validation/stage1'}
ARMS=('baseline','c48_local','c48_crossnote','wide_swap','wide_relevance')
SWAPS=ARMS[1:4]
FEATURES=('bge_score','reciprocal_bge_rank','reciprocal_dense_rank','reciprocal_bm25_rank','log_length','claim_lexical_coverage','kept_redundancy','same_note_count')

def seal(folder,deps=(),code=()):
    write_json(folder/'manifest.json',dict(created_utc=now(),files={p.relative_to(ROOT).as_posix():file_hash(p) for p in folder.rglob('*') if p.is_file()},
        dependencies={p.relative_to(ROOT).as_posix():file_hash(p) for p in deps},code_sha256={p.relative_to(ROOT).as_posix():file_hash(p) for p in code}))
def check(folder):
    m=read(folder/'manifest.json')
    for k in ('files','dependencies','code_sha256'):old.check_hashes(m[k])
    return m
def rank_id(pid):return old.hash_rank(pid,'017/GT-blind/patient-author/v1:')

def sources():
    result=[];passages={};paths=[]
    for name,root in BASES.items():
        if name=='old6':
            ip=root/'judge_preparation/inputs.jsonl';cp=root/'preparation/corpus.jsonl';rows=jsonlines(ip)
        else:
            ip=root/'base_preparation_001/inputs.jsonl';cp=root/'preparation_002/corpus.jsonl';rp=root/'candidates_001/candidates.jsonl'
            ranking={r['proposition_id']:r for r in jsonlines(rp)};rows=jsonlines(ip);paths.append(rp)
        passages.update({p['passage_id']:p for p in jsonlines(cp)});paths.extend([ip,cp])
        for r in rows:
            if name=='old6':base=r['retrieval']['C48'];ranks=r['rankings'];pools={k:r['retrieval'][k]['candidate_ids'] for k in ('A48','B48','C48')}
            else:base=r;ranks=ranking[r['proposition_id']]['rankings'];pools=ranking[r['proposition_id']]['candidate_ids']
            wide=sorted({pid for p in pools.values() for pid in p})
            require(set(wide)==set(r['scores']),'Frozen scored union differs')
            result.append({**{k:r[k] for k in ('proposition_id','subject_id','author_type','text','admission','scores')},
                'case_id':name+'_'+r['case_id'],'source':name,'split':'train' if name=='old6' else 'selection',
                'rankings':ranks,'C48':pools['C48'],'wide':wide,'baseline':{k:base[k] for k in ('selected_ids','reference','body_characters')}})
    return result,passages,paths

def gt_for(ids):
    # Called only after interventions are frozen; GT never enters construction.
    rows=[]
    for name,root in BASES.items():
        p=root/('preparation/cohort.csv' if name=='old6' else 'preparation_002/cohort.csv')
        rows.extend(r for r in csvrows(p) if r['proposition_id'] in ids)
    require(len(rows)==len(ids) and len({r['proposition_id'] for r in rows})==len(ids),'Cohort mismatch')
    return rows
