"""GT-blind inventory for a single numeric-unit witness abstention operation."""
from common091 import *
import re
from decimal import Decimal
sys.path.insert(0,str(ROOT/'tasks/090_demo_constructor_repair_validation'))
from common090 import unitize
PAT=re.compile(r'(?<![\w.])(?P<v>\d+(?:\.\d+)?)\s*(?P<u>mm\s*Hg|cm\s*H2O|mg\s*/\s*dL|mmol\s*/\s*L|mEq\s*/\s*L|L\s*/\s*min|mcg|mg|mL|ml|bpm|%)(?![A-Za-z])',re.I)
def quantities(s):return [(str(Decimal(m['v']).normalize()),re.sub(r'\s+','',m['u']).lower()) for m in PAT.finditer(s)]
def witness(claim,reference):
    needs=set(quantities(claim));units=unitize(reference)['units'];seen={q for u in units for q in quantities(u['text'].split(' | Text: ',1)[-1])}
    return dict(eligible=bool(needs),n_required=len(needs),n_present=len(needs&seen),n_missing=len(needs-seen),missing=bool(needs-seen))
def main():
    # Source has old score fields; only identity/text/reference fields are consumed.
    audit=read(ROOT/'outputs/090_demo_constructor_repair_validation/sampling_audit.json');allowed=set(audit['eval_patients'])
    exclude=set();sources=[]
    for rel in ('outputs/084_f4_coverage_validation/sample_blind.jsonl','outputs/086_global_demonstration_selection/E_cases_blind.jsonl','outputs/087_f4_evidence_intervention/sample_blind.jsonl','outputs/089_source_audited_demo_compression/sample_blind.jsonl','outputs/090_demo_constructor_repair_validation/cohort_manifest.jsonl'):
        p=ROOT/rel;sources.append(p);exclude.update(x['id'] for x in lines(p))
    source=ROOT/'outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl';sources.append(source);pool=[];schema=None
    for x in lines(source):
        pid=x.get('id',x.get('proposition_id'));sid=str(x.get('sid',x.get('subject_id')))
        if sid not in allowed or pid in exclude:continue
        claim=x.get('claim',x.get('proposition',x.get('text')));ref=x.get('reference')
        if not isinstance(claim,str) or not isinstance(ref,str):raise RuntimeError(str(list(x)))
        w=witness(claim,ref)
        if w['eligible']:pool.append(dict(id=pid,sid=sid,claim=claim,reference=ref,author=x.get('author',x.get('author_type')),**w))
    assert len(pool)==len({x['id'] for x in pool})
    # This inventory threshold is about material coverage, not outcome significance.
    eligible=len(pool)>=32 and len({x['sid'] for x in pool})>=8 and min(sum(x['missing'] for x in pool),sum(not x['missing'] for x in pool))>=8
    putl(PRIVATE/'C_blind_pool.jsonl',pool)
    out=dict(created_utc=now(),n=len(pool),patients=len({x['sid'] for x in pool}),missing_literal=sum(x['missing'] for x in pool),all_literals_present=sum(not x['missing'] for x in pool),material_gate=eligible,reads_GT=False,source_sha256=bind(sources),by_patient={s:dict(n=len(z:=[x for x in pool if x['sid']==s]),missing=sum(x['missing'] for x in z)) for s in sorted({x['sid'] for x in pool})},excluded_recent_ids=len(exclude),limitations='Literal quantity/unit presence is neither predicate linkage nor clinical sufficiency; abstention is separate from NA. Earlier development exposure is not eliminated.')
    put(OUT/'C_material_inventory.json',out);print(canonical(out))
if __name__=='__main__':main()
