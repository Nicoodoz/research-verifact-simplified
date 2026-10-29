"""CPU same-ID comparison, with original103 panel roles and no outcome imputation."""
from pathlib import Path
from collections import Counter
import argparse,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics
sys.path.insert(0,str(ROOT/'tasks/110_update_interpolation'));from analyze110 import changes
sys.path.insert(0,str(ROOT/'tasks/107_support_aux'));from evaluate107 import risk_deltas
sys.path.insert(0,str(ROOT/'src'));from verifact_research.evaluation import paired_compare
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));from parse105 import parse
def verdict(record):return record.get('parsed',{}).get('verdict') if record.get('parsed',{}).get('valid') else None
def section(keys,data,baselines,bootstrap):
    arms=list(data);expected={r['id'] for r in keys};rows=[dict(r,pred={a:verdict(data[a][r['id']]) for a in arms}) for r in keys if all(r['id'] in data[a] and verdict(data[a][r['id']]) is not None for a in arms)]
    scores={a:metrics(rows,{r['id']:r['pred'][a] for r in rows}) for a in arms} if rows else {};pairs={}
    for base in baselines:
        pair=[dict(r,pred={base:verdict(data[base][r['id']]),'update_half':verdict(data['update_half'][r['id']])}) for r in keys if all(r['id'] in data[a] and verdict(data[a][r['id']]) is not None for a in [base,'update_half'])]
        if not pair:continue
        old=metrics(pair,{r['id']:r['pred'][base] for r in pair});new=metrics(pair,{r['id']:r['pred']['update_half'] for r in pair});delta=changes(pair,base,'update_half')
        avoided=[r for r in pair if r['GT']!='Supported' and r['pred'][base]=='Supported'!=r['pred']['update_half']]
        delta.update(avoided_false_S_repaired_to_GT=sum(r['pred']['update_half']==r['GT'] for r in avoided),avoided_false_S_still_wrong=sum(r['pred']['update_half']!=r['GT'] for r in avoided),
            NA_from_S_to_NS_still_wrong=sum(r['GT']=='Not Addressed' and r['pred']['update_half']=='Not Supported' for r in avoided),
            delta_MCC=new['mcc']-old['mcc'],delta_PA=new['percent_agreement']-old['percent_agreement'],delta_correct=new['correct']-old['correct'],delta_false_S=new['false_S']-old['false_S'])
        patient=[]
        for n,sid in enumerate(sorted({str(r['sid']) for r in pair}),1):
            part=[r for r in pair if str(r['sid'])==sid];patient.append(dict(patient_index=n,N=len(part),correct_delta=sum(int(r['pred']['update_half']==r['GT'])-int(r['pred'][base]==r['GT']) for r in part),false_S_delta=sum(int(r['GT']!='Supported' and r['pred']['update_half']=='Supported')-int(r['GT']!='Supported' and r['pred'][base]=='Supported') for r in part)))
        result=dict(N=len(pair),baseline=old,candidate=new,**delta,patients=patient,patient_direction=dict(correct_improved=sum(p['correct_delta']>0 for p in patient),correct_worsened=sum(p['correct_delta']<0 for p in patient),false_S_reduced=sum(p['false_S_delta']<0 for p in patient),false_S_increased=sum(p['false_S_delta']>0 for p in patient)))
        if bootstrap and len(patient)>1:
            cohort=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in pair];a=[dict(proposition_id=r['id'],verdict=r['pred'][base]) for r in pair];b=[dict(proposition_id=r['id'],verdict=r['pred']['update_half']) for r in pair]
            result.update(patient_paired=paired_compare(cohort,a,b,iterations=1000),risk_CI=risk_deltas(pair,base,'update_half'))
        pairs[base]=result
    coverage={a:dict(expected=len(keys),received=sum(i in data[a] for i in expected),valid=sum(i in data[a] and verdict(data[a][i]) is not None for i in expected),invalid=sum(i in data[a] and verdict(data[a][i]) is None for i in expected),missing=sum(i not in data[a] for i in expected)) for a in arms}
    return dict(expected_N=len(keys),GT=dict(Counter(r['GT'] for r in keys)),non_S=sum(r['GT']!='Supported' for r in keys),patient_N=len({r['sid'] for r in keys}),common_valid_N=len(rows),coverage=coverage,scores=scores,half_vs=pairs,
        author={author:{a:metrics([r for r in rows if r['author']==author],{r['id']:r['pred'][a] for r in rows if r['author']==author}) for a in arms} for author in sorted({r['author'] for r in rows})})
def analyze(private,work,full,bootstrap):
    keys=c.rows(private/'cohort_keys.jsonl');key={r['id']:r for r in keys};old={a:{r['id']:r for r in c.rows(private/(a+'_old500.jsonl'))} for a in ['label_only105','label_only107','update_half','update_quarter']}
    paper={r['id']:dict(parsed=dict(valid=True,verdict=r['paper_r1'])) for r in keys};old['paper_r1']=paper
    history=c.rows(private/'history103_180.jsonl');old['lora103_9b512']={r['id']:dict(parsed=dict(valid=True,verdict=r['predictions']['nine_lora'])) for r in history}
    oldkeys=[r for r in keys if r['subset']=='old500'];olddata={a:old[a] for a in ['label_only105','label_only107','update_quarter','update_half','paper_r1']};sections={}
    for panel in ['natural','pressure']:sections['old_'+panel]=section([r for r in oldkeys if r['old_panel']==panel],olddata,['label_only105','label_only107'],bootstrap)
    existing={r['id'] for r in oldkeys};histdata={a:old[a] for a in ['lora103_9b512','label_only105','label_only107','update_half','paper_r1']}
    for panel in ['natural','pressure']:
        matched=[key[r['id']] for r in history if r['panel']==panel and r['id'] in existing]
        sections['history103_existing_'+panel]=section(matched,histdata,['lora103_9b512','label_only105','label_only107'],bootstrap)
    result=dict(task=111,sections=sections,preparation_only=not full,full1817_not_reported_until_complete_receipts=True,history103_arm='nine_lora',history103_recipe_differences='512 one epoch/original103 prompt/uniform answer CE vs196 two epochs/104 prompt/105 segmented loss; whole-recipe comparison',new_training=False,new_paid_API_CNY=0)
    if full:
        cfg=c.read(private/'config111.json');newids={r['id'] for r in keys if r['subset']=='new'};merged={}
        for a in ['label_only105','label_only107','update_half']:
            raw=c.rows(work/a/'predictions.jsonl');new={r['id']:r for r in raw}
            if len(raw)!=len(new) or len(new)!=len(newids) or set(new)!=newids:raise ValueError('All1317 distinct first receipts required; no missing fallback')
            for i,r in new.items():
                if r['identity']['adapter_sha256']!=cfg['source_adapters'][a]['sha256'] or str(r['sid'])!=str(key[i]['sid']):raise ValueError('Wrong new adapter/patient')
                if r['parsed']!=parse(r['content'],r['finish_reason']):raise ValueError('Changed parser')
            if set(old[a])&set(new):raise ValueError('Old500/new overlap')
            merged[a]=old[a]|new
        for i in newids:
            if len({merged[a][i]['prompt_token_sha256'] for a in merged})!=1:raise ValueError('Different actual original prompts across new arms')
        merged['paper_r1']=paper
        sections['new1317']=section([r for r in keys if r['subset']=='new'],merged,['label_only105','label_only107'],bootstrap)
        sections['full1817']=section(keys,merged,['label_only105','label_only107'],bootstrap)
        for panel in ['natural','pressure']:
            hkeys=[key[r['id']] for r in history if r['panel']==panel];hdata=dict(merged,lora103_9b512=old['lora103_9b512']);sections['history103_full_'+panel]=section(hkeys,hdata,['lora103_9b512','label_only105','label_only107'],bootstrap)
        sanitized=[dict(id=r['id'],sid=r['sid'],GT=r['GT'],author=r['author'],subset=r['subset'],arm=a,valid=verdict(merged[a][r['id']]) is not None,verdict=verdict(merged[a][r['id']]),source='old500_reused' if r['subset']=='old500' else 'new111_first_receipt') for r in keys for a in ['label_only105','label_only107','update_half']]
        c.putl(ROOT/'outputs/111_half_extension/predictions_sanitized.jsonl',sanitized);result['complete1817_ID_receipts_verified']=True
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true');p.add_argument('--bootstrap',action='store_true');a=p.parse_args();r=analyze(a.private,a.work,a.full,a.bootstrap);c.put(a.output,r);print(c.canonical({s:{a:dict(MCC=m['mcc'],PA=m['percent_agreement'],false_S=m['false_S'],N=m['n']) for a,m in v['scores'].items()} for s,v in r['sections'].items()}))
