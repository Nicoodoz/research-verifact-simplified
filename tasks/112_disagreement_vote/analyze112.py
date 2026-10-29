"""Fixed-vote analysis with historical and newly returned103 receipts; no model calls."""
from pathlib import Path
from collections import Counter
import sys,argparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics
sys.path.insert(0,str(ROOT/'tasks/110_update_interpolation'));from analyze110 import changes
sys.path.insert(0,str(ROOT/'tasks/107_support_aux'));from evaluate107 import risk_deltas
sys.path.insert(0,str(ROOT/'src'));from verifact_research.evaluation import paired_compare
sys.path.insert(0,str(ROOT/'tasks/103_lora_selection'));from parse_label103 import parse_label
from rule112 import disagreement_vote,LABELS
def section(keys,data):
    rows=[dict(r,pred={a:v[r['id']] for a,v in data.items()}) for r in keys];a='label_only107';b='disagreement_vote'
    scores={arm:metrics(rows,{r['id']:r['pred'][arm] for r in rows}) for arm in data}
    cohort=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in rows]
    pred=lambda arm:[dict(proposition_id=r['id'],verdict=r['pred'][arm]) for r in rows]
    delta=changes(rows,a,b);avoided=[r for r in rows if r['GT']!='Supported' and r['pred'][a]=='Supported'!=r['pred'][b]]
    patient=[dict(sid=sid,N=len(rr),correct_delta=sum(int(r['pred'][b]==r['GT'])-int(r['pred'][a]==r['GT']) for r in rr),false_S_delta=sum(int(r['GT']!='Supported' and r['pred'][b]=='Supported')-int(r['GT']!='Supported' and r['pred'][a]=='Supported') for r in rr)) for sid in sorted({r['sid'] for r in rows}) for rr in [[r for r in rows if r['sid']==sid]]]
    return dict(N=len(rows),GT=dict(Counter(r['GT'] for r in rows)),non_S=sum(r['GT']!='Supported' for r in rows),scores=scores,vs107=dict(**delta,
        delta_MCC=scores[b]['mcc']-scores[a]['mcc'],delta_PA=scores[b]['percent_agreement']-scores[a]['percent_agreement'],delta_correct=scores[b]['correct']-scores[a]['correct'],delta_false_S=scores[b]['false_S']-scores[a]['false_S'],
        avoided_false_S_still_wrong=sum(r['pred'][b]!=r['GT'] for r in avoided),NA_S_to_NS_still_wrong=sum(r['GT']=='Not Addressed' and r['pred'][b]=='Not Supported' for r in avoided),
        patient_paired=paired_compare(cohort,pred(a),pred(b),iterations=1000),risk_CI=risk_deltas(rows,a,b),patients=patient),
        author={u:{arm:metrics([r for r in rows if r['author']==u],{r['id']:r['pred'][arm] for r in rows if r['author']==u}) for arm in data} for u in sorted({r['author'] for r in rows})})
def main(private):
    keys=c.rows(private/'keys.jsonl');lookup={r['id']:r for r in keys};frozen={r['id']:r for r in c.rows(private/'frozen_labels.jsonl')};third={r['id']:r for r in c.rows(private/'cached103.jsonl')}
    cfg=c.read(ROOT/'tasks/112_disagreement_vote/config.json');new=c.read(private/'evidence/results/predictions.json');wanted={r['id'] for r in c.rows(private/'inputs.jsonl')}
    assert len(new)==len({r['id'] for r in new})==138 and {r['id'] for r in new}==wanted
    for r in new:
        assert r['adapter_sha256']==cfg['adapter_sha256'] and r['parsed']==parse_label(r['content'],r['finish_reason'])
        third[r['id']]=dict(id=r['id'],valid=r['parsed']['valid'],verdict=r['parsed']['verdict'],source='new112_first_receipt',finish_reason=r['finish_reason'])
    records=[];predictions={a:{} for a in ['label_only107','update_half','disagreement_vote','paper_r1']}
    for r in keys:
        i=r['id'];a=frozen[i]['baseline'];h=frozen[i]['half'];t=third.get(i);label=t['verdict'] if t and t['valid'] else None;v,reason=disagreement_vote(a,h,label)
        for arm,val in [('label_only107',a),('update_half',h),('disagreement_vote',v),('paper_r1',r['paper_r1'])]:predictions[arm][i]=val
        records.append(dict(id=i,sid=r['sid'],GT=r['GT'],author=r['author'],subset=r['subset'],baseline=a,half=h,verdict=v,trigger=a!=h,third_verdict=label if a!=h else None,third_valid=bool(t and t['valid']) if a!=h else None,third_source=t['source'] if a!=h and t else None,third_finish_reason=t.get('finish_reason','historical_valid') if a!=h and t else None,reason=reason))
    history=[r for r in c.rows(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl') if r['local180']];histids={r['id'] for r in history}
    result=dict(task=112,complete=True,counts=dict(cohort=1817,agreement=sum(not r['trigger'] for r in records),triggers=sum(r['trigger'] for r in records),new103=len(new),new103_invalid=sum(not r['parsed']['valid'] for r in new),cached103_triggers=28,reasons=dict(Counter(r['reason'] for r in records))),
        fallback_finish_reasons=dict(Counter(r['third_finish_reason'] for r in records if r['reason']=='third_invalid_fallback')),
        deployment_average_model_predictions=2+166/1817,trigger_rate=166/1817,new_training=False,new_API_CNY=0,sections={})
    for name,group in [('full1817',keys),('new1317',[r for r in keys if r['subset']=='new']),('old_natural',[r for r in keys if r['old_panel']=='natural']),('old_pressure',[r for r in keys if r['old_panel']=='pressure'])]:result['sections'][name]=section(group,predictions)
    hist_data=dict(predictions,original103={r['id']:r['predictions']['nine_lora'] for r in history},untrained9b_label={r['id']:r['predictions']['nine_direct'] for r in history})
    for panel in ['natural','pressure']:result['sections']['history103_'+panel]=section([lookup[r['id']] for r in history if r['panel']==panel],hist_data)
    out=ROOT/'outputs/112_disagreement_vote';c.put(out/'comparison.json',result);c.putl(out/'predictions_sanitized.jsonl',records)
    print(c.canonical({n:{a:dict(MCC=m['mcc'],PA=m['percent_agreement'],correct=m['correct'],false_S=m['false_S'],non_S=m['non_S']) for a,m in x['scores'].items()} for n,x in result['sections'].items()}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',type=Path,default=ROOT/'.local_models/112_disagreement_vote');main(p.parse_args().private)
