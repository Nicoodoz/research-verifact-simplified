"""Synthetic integrity checks and optional train-only existing-citation proof."""
from collections import Counter
from pathlib import Path
import argparse,json,time
from reorder142 import reorder_reference,split_reference

R=Path(__file__).resolve().parents[2]


def verify(source,claim):
    rendered,manifest=reorder_reference(source,claim)
    prefix,units=split_reference(source)
    before={u['number']:u for u in units}
    retained=[]
    for span in manifest['fragments']:
        raw=rendered[span['rendered_start']:span['rendered_end']]
        assert raw==before[span['number']]['raw'];retained.append(raw)
    assert Counter(retained)==Counter(u['raw'] for u in units)
    assert rendered[:len(prefix)]==prefix
    assert sorted(manifest['new_fragment_order'])==sorted(manifest['original_fragment_order'])
    assert len(rendered)-len(source)==manifest['added_separator_chars']
    assert len(split_reference(rendered)[1])==len(units)
    return rendered,manifest,units


def synthetic():
    def unit(n,text,end='\n'):return f'{n}. Date: 2100-01-01 | Time: Unknown | Category: Note | Description: Example | Text: '+text+end
    tied='Patient header\n'+unit(7,'same token')+unit(2,'same token')+unit(9,'same token')
    rendered,m,_=verify(tied,'same token');assert rendered==tied and m['new_fragment_order']==['7','2','9']
    rendered,m,_=verify(tied,'qwertyunmatched');assert rendered==tied and m['zero_score_fragment_N']==3
    boundary=unit(1,'irrelevant')+unit(2,'irrelevant')+unit(3,'needle','')
    rendered,m,_=verify(boundary,'needle');assert m['new_fragment_order'][0]=='3' and m['added_separator_chars']==1
    assert m['fragment_N']==3 and m['zero_score_fragment_N']==2
    blank,m,_=verify(boundary,'');assert m['new_fragment_order']==['1','2','3']
    try:reorder_reference('unstructured text','needle')
    except ValueError:pass
    else:raise AssertionError('Unrecognized reference must fail explicitly')
    return dict(status='PASS',synthetic_checks=['raw fragment multiset','original numbers','stable score ties',
        'zero-score retention','necessary newline counted','identical Text retained twice','empty claim','unrecognized reference rejected'])


def bands(values):
    import statistics
    return dict(N=len(values),front=sum(x<1/3 for x in values),middle=sum(1/3<=x<2/3 for x in values),
        back=sum(x>=2/3 for x in values),median=statistics.median(values) if values else None)


def training_proof(out):
    source=R/'.local_models/127_native_reason_data/dataset_v12_support20261031/paired/train_label_only.jsonl'
    rows=[json.loads(s) for s in source.read_text(encoding='utf-8').splitlines()]
    assert len(rows)==63 and all(r['fit_role']=='train' and r['reason_metadata']['review']['status']=='approved' for r in rows)
    eval_rows=[json.loads(s) for s in (R/'.local_models/134_author_baselines/keys.jsonl').read_text().splitlines()]
    assert not {r['sid'] for r in rows}&{r['sid'] for r in eval_rows}
    details=[];all_positions=[];first=[];began=time.perf_counter()
    for row in rows:
        rendered,m,units=verify(row['reference'],row['claim'])
        spans={s['number']:s for s in m['fragments']};cited={};whole=0
        for evidence in row['reason_metadata']['evidence_sources']:
            if evidence['kind']!='reference_span':whole+=1;continue
            lo,hi=evidence['start'],evidence['end'];assert row['reference'][lo:hi]==evidence['quote']
            for unit in units:
                if max(lo,unit['start'])<min(hi,unit['end']):
                    point=max(lo,unit['start']);n=unit['number'];cited[n]=min(point,cited.get(n,point))
        positions=[]
        for number,point in cited.items():
            s=spans[number];new=s['rendered_start']+point-s['original_start'];length=next(u for u in units if u['number']==number)['end']-point
            # Existing citation bytes that lie within this intact unit are unchanged.
            assert row['reference'][point:point+length]==rendered[new:new+length]
            value=dict(number=number,old_fraction=point/len(row['reference']),new_fraction=new/len(rendered))
            positions.append(value);all_positions.append(value)
        if positions:first.append(dict(old_fraction=min(x['old_fraction'] for x in positions),new_fraction=min(x['new_fraction'] for x in positions)))
        details.append(dict(id=row['id'],sid=row['sid'],fragment_N=m['fragment_N'],added_separator_chars=m['added_separator_chars'],
            original_characters=len(row['reference']),rendered_characters=len(rendered),whole_reference_sources=whole,
            positions=positions,fragment_integrity='PASS',existing_citation_integrity='PASS'))
    def comparison(values):return dict(original=bands([x['old_fraction'] for x in values]),sorted=bands([x['new_fraction'] for x in values]),
        moved_forward=sum(x['new_fraction']<x['old_fraction'] for x in values),moved_back=sum(x['new_fraction']>x['old_fraction'] for x in values))
    summary=dict(status='PASS_CPU_ONLY',N=63,patients=len({r['sid'] for r in rows}),evaluation_patient_overlap=0,
        reference_fragments=sum(x['fragment_N'] for x in details),added_separator_chars_total=sum(x['added_separator_chars'] for x in details),
        all_fragment_multisets_numbers_and_headers_text_preserved=True,all_existing_citations_unchanged=True,
        citation_unit_positions=comparison(all_positions),first_citation_positions=comparison(first),CPU_seconds=time.perf_counter()-began,
        source=str(source.relative_to(R)).replace('\\','/'),method='Unchanged008 tokenize/BM25; k1=1.2,b=.75; all intact numbered units sorted descending, original-order ties.',
        limitations=['Existing AI-assisted reason citations are not physician gold evidence.',
            'Only approved training63 (27 patients); no validation4 or evaluation20 prediction used.',
            'Character-position bins, not token locations or classification outcomes.',
            'Citation movement may hurt recency or chronology; position improvement is not model improvement.',
            'No evidence removal, deduplication, new text, new labels, model run or API.'])
    out.mkdir(parents=True,exist_ok=True)
    (out/'train_proof.json').write_text(json.dumps(dict(summary=summary,details=details),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--training-proof',type=Path);p.add_argument('--summary-out',type=Path);a=p.parse_args()
    result=synthetic()
    if a.training_proof:result['training']=training_proof(a.training_proof)
    if a.summary_out:
        if 'training' not in result:raise ValueError('--summary-out requires --training-proof')
        a.summary_out.parent.mkdir(parents=True,exist_ok=True)
        a.summary_out.write_text(json.dumps(result['training'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
