"""Fixed min/median/max training-only lexical-pair source audit; no API/model."""
from collections import Counter
import json
from pathlib import Path
import re
import statistics
import sys
from data106 import ROOT, OUT, PRIVATE, digest, put, putl, read, rows, sha
from analysis106 import unit_spans


def prepare():
    frozen_source=OUT/'data_pair_audit_source_v1.jsonl'
    pair_source_path=frozen_source if frozen_source.exists() else OUT/'data_boundary_cover_pairs.jsonl'
    links=[r for r in rows(pair_source_path) if r['kind']=='S_nonS']
    median=statistics.median(r['similarity'] for r in links)
    selections=dict(minimum=min(links,key=lambda r:(r['similarity'],r['nonS_id'],r['peer_id'])),
        median=min(links,key=lambda r:(abs(r['similarity']-median),r['nonS_id'],r['peer_id'])),
        maximum=min(links,key=lambda r:(-r['similarity'],r['nonS_id'],r['peer_id'])))
    corpus={r['id']:r for r in rows(PRIVATE/'training_pool.jsonl')}
    dossiers=[]
    for rank,link in selections.items():
        for side,identifier in (('nonS',link['nonS_id']),('S',link['peer_id'])):
            r=corpus[identifier];source=r['reference'];spans=unit_spans(source)
            notes={};chunks=[];mapped=[]
            for number,span in enumerate(spans):
                raw=source[span['start']:span['end']]
                content=re.sub(r'^\d+\. ','',raw)
                unit=f'U{number+1:03d}'
                matched=re.fullmatch(r'Date: (.*?), Time: (.*?), Note Category: (.*?), Note Description: (.*?) \| Text: ([\s\S]*)',content)
                if matched:
                    meta=matched.groups()[:4]
                    if meta not in notes:notes[meta]=f'N{len(notes)+1:02d}'
                    chunks.append(f'{unit} {notes[meta]} {matched.group(5)}')
                else:chunks.append(f'{unit} {content}')
                mapped.append(dict(unit_id=unit,**span))
            header=[f'PAIR {rank} SIDE {side} ID {identifier} GT {r["GT"]} SIMILARITY {link["similarity"]}',f'CLAIM: {r["claim"]}']
            header += [f'{code} Date {meta[0]}; Time {meta[1]}; Category {meta[2]}; Description {meta[3]}' for meta,code in notes.items()]
            path=PRIVATE/'pair_reading'/f'{rank}_{side}.txt'
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('\n'.join(header+chunks)+'\n').encode('utf-8'))
            dossiers.append(dict(rank=rank,side=side,id=identifier,sid=r['sid'],GT=r['GT'],claim=r['claim'],
                full_reference=source,reference_sha256=digest(source),claim_sha256=digest(r['claim']),
                complete_unit_spans=mapped,similarity=link['similarity']))
    putl(PRIVATE/'pair_reading/dossiers.jsonl',dossiers)
    put(OUT/'data_pair_audit_selection.json',dict(rule='Minimum, closest to numeric median, maximum similarity; ties by nonS ID then S ID; fixed before source reading',
        pair_population=192,median_similarity=median,selections=selections,
        source_pairs_sha256=sha(pair_source_path),source_pairs_path=str(pair_source_path.relative_to(ROOT)),selection_uses_development_performance=False,
        not_192_semantically_validated_pairs=True))
    print(json.dumps([{k:r[k] for k in ('rank','side','id','GT','claim','similarity')} for r in dossiers]))


def assemble():
    dossiers=rows(PRIVATE/'pair_reading/dossiers.jsonl')
    notes=read(PRIVATE/'pair_reading/review_notes.json')
    public=[];private=[]
    for rank,note in notes.items():
        pair=[r for r in dossiers if r['rank']==rank]
        citations=[];quotes=[]
        for r in pair:
            mapping={u['unit_id']:u for u in r['complete_unit_spans']}
            for identifier in note['units'][r['side']]:
                where=mapping[identifier]
                quote=r['full_reference'][where['start']:where['end']]
                assert digest(quote)==where['sha256']
                citation=dict(side=r['side'],id=r['id'],reference_sha256=r['reference_sha256'],**where)
                citations.append(citation);quotes.append(dict(citation,quote=quote))
        value=dict(rank=rank,similarity=pair[0]['similarity'],ids={r['side']:r['id'] for r in pair},
            GT={r['side']:r['GT'] for r in pair},same_patient=len({r['sid'] for r in pair})==1,
            same_reference=len({r['reference_sha256'] for r in pair})==1,
            **{k:v for k,v in note.items() if k!='units'},cited_source_locations=citations,
            complete_own_references_read_each_side=True,new_physician_gold=False,GT_modified=False,
            review_not_used_to_change_dev_predictions=True,not_all192_pairs_audited=True)
        public.append(value);private.append(dict(value,quoted_units=quotes,claims={r['side']:r['claim'] for r in pair}))
    assert {r['rank'] for r in public}=={'minimum','median','maximum'}
    putl(OUT/'semantic_training_pairs.jsonl',public)
    putl(PRIVATE/'semantic_training_pairs_private_quotes.jsonl',private)
    print(json.dumps(dict(N=len(public),assessments=dict(Counter(r['assessment'] for r in public)))))


if __name__=='__main__':
    if '--assemble-review' in sys.argv:assemble()
    else:prepare()
