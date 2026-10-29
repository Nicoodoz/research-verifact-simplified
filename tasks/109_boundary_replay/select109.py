"""Fixed error-driven sampling. No model calls, no teacher-error substitution."""
from collections import Counter,defaultdict,deque
from pathlib import Path
import argparse
import common109 as c

class InsufficientData(ValueError):pass

def rank(config,kind,identifier):return c.digest(config['selection']['seed']+'/'+kind+'/'+identifier)

def round_robin(ids,meta,config,kind):
    grouped=defaultdict(list)
    for identifier in ids:grouped[str(meta[identifier]['sid'])].append(identifier)
    queues={sid:deque(sorted(values,key=lambda i:rank(config,kind,i))) for sid,values in grouped.items()}
    patients=sorted(queues,key=lambda sid:rank(config,kind+'/patient',sid));result=[]
    while any(queues.values()):
        for sid in patients:
            if queues[sid]:result.append(queues[sid].popleft())
    return result

def load_predictions(path,expected_ids,meta):
    records=c.rows(path);ids=[r['id'] for r in records]
    if len(set(ids))!=len(ids) or set(ids)!=set(expected_ids):raise ValueError('Predictions must cover exactly this fixed request; no filtering/fallback')
    result={}
    for row in records:
        identifier=row['id'];m=meta[identifier]
        if not m.get('eligible_109') or m.get('role')!='train':raise ValueError('Ineligible/non-training case in mining request')
        if row.get('prediction_origin')!='actual_GPU_checkpoint':raise ValueError('Actual current-checkpoint predictions required')
        if row.get('checkpoint_adapter_sha256')!=c.SOURCE_ADAPTER_SHA:raise ValueError('Wrong checkpoint: R1/105/aux/108 are not current107 errors')
        if str(row.get('sid'))!=str(m['sid']) or row.get('prompt_token_sha256')!=m['prompt_token_sha256']:raise ValueError('Patient or actual prompt mismatch')
        if row.get('GT') is not None and row['GT']!=m['GT']:raise ValueError('Cached prediction carries a different original GT')
        parsed=row.get('parsed',{})
        if parsed.get('valid') and parsed.get('verdict') not in c.LABELS:raise ValueError('Unknown verdict')
        # Invalid first outputs are retained, never promoted to hard examples.
        result[identifier]=parsed.get('verdict') if parsed.get('valid') else None
    return result

def choose_hard(meta,predictions,config):
    queues={}
    for label in c.LABELS[1:]:
        ordered=[]
        for tier in (0,1):
            for reviewed in (True,False):
                ids=[i for i,p in predictions.items() if meta[i]['GT']==label and p is not None and p!=label
                     and (p=='Supported')==(tier==0) and (meta[i]['semantic104_status']=='gt_explained')==reviewed]
                ordered.extend(round_robin(ids,meta,config,'hard/'+label+'/'+str(tier)+'/'+str(reviewed)))
        queues[label]=ordered
    minimum=config['selection']['hard_min_per_class'];target=config['selection']['hard_target_per_class'];total=config['selection']['hard_total']
    if any(len(queues[g])<minimum for g in queues):raise InsufficientData('Need at least16 genuine valid errors in EACH non-S class; do not expand or substitute teachers')
    selected={g:queues[g][:min(target,len(queues[g]))] for g in queues}
    while sum(map(len,selected.values()))<total:
        possible=[g for g in queues if len(selected[g])<len(queues[g]) and len(selected[g])<total-minimum]
        if not possible:raise InsufficientData('Fewer than64 usable genuine errors; no training')
        label=sorted(possible,key=lambda g:(len(selected[g]),g))[0]
        selected[label].append(queues[label][len(selected[label])])
    return [i for g in c.LABELS[1:] for i in selected[g]]

def supported_request(hard,neighbors,source_ids,meta,config):
    if any(str(meta[h]['sid'])!=str(meta[n['id']]['sid']) or meta[n['id']]['GT']!='Supported' for h in hard for n in neighbors[h]):raise ValueError('Protection neighbors must be real S of the same training patient')
    ids={i for h in hard for i in [x['id'] for x in neighbors[h]]}
    if len(ids)<config['selection']['protect_S']:raise InsufficientData('Fewer than64 distinct eligible lexical-neighbor S even before prediction; stop early')
    ids.update(i for i in source_ids if meta[i]['GT']=='Supported')
    if len(ids)>3*len(hard)+83:raise ValueError('S prediction cap changed')
    if any(meta[i]['GT']!='Supported' for i in ids):raise ValueError('S protection request contains non-S')
    return sorted(ids,key=lambda i:(meta[i]['input_tokens'],i))

def select(meta,predictions_a,predictions_s,neighbors,source_ids,config):
    hard=choose_hard(meta,predictions_a,config);required=supported_request(hard,neighbors,source_ids,meta,config)
    if set(predictions_s)!=set(required):raise ValueError('S predictions differ from the frozen post-hard request')
    near={}
    for h in hard:
        for neighbor in neighbors[h]:
            i=neighbor['id']
            if predictions_s[i]=='Supported' and (i not in near or neighbor['similarity']>near[i]['similarity']):near[i]=dict(neighbor,hard_id=h)
    # Similarity orders candidates only; no pair is certified clinically.
    by_patient=defaultdict(list)
    for i in near:by_patient[str(meta[i]['sid'])].append(i)
    queues={sid:deque(sorted(ids,key=lambda i:(-near[i]['similarity'],rank(config,'protect',i)))) for sid,ids in by_patient.items()}
    patients=sorted(queues,key=lambda sid:rank(config,'protect/patient',sid));protect=[]
    while len(protect)<config['selection']['protect_S'] and any(queues.values()):
        for sid in patients:
            if queues[sid] and len(protect)<config['selection']['protect_S']:protect.append(queues[sid].popleft())
    if len(protect)!=config['selection']['protect_S']:raise InsufficientData('Fewer than64 CURRENT-correct lexical-neighbor S; no ordinary-S recipe substitution')
    chosen=set(hard+protect);retention=[];all_predictions=predictions_a|predictions_s;source=set(source_ids)
    for label,needed in config['selection']['retention'].items():
        eligible=[i for i,p in all_predictions.items() if i not in chosen and p==label==meta[i]['GT']]
        ordered=round_robin([i for i in eligible if i in source],meta,config,'retention/source/'+label)
        ordered+=round_robin([i for i in eligible if i not in source],meta,config,'retention/pool/'+label)
        if len(ordered)<needed:raise InsufficientData('Insufficient CURRENT-correct retention for '+label)
        retention.extend(ordered[:needed]);chosen.update(ordered[:needed])
    roles={i:'hard_error' for i in hard}|{i:'protect_S' for i in protect}|{i:'retention' for i in retention}
    order=sorted(chosen,key=lambda i:rank(config,'training_order',i))
    if len(order)!=192 or len(order)!=len(roles):raise ValueError('Expected192 unique training examples')
    manifest=[dict(id=i,sid=meta[i]['sid'],GT=meta[i]['GT'],role=roles[i],source107=i in source,
        previous_prediction=all_predictions[i],input_tokens=meta[i]['input_tokens'],
        lexical_neighbor=near[i] if roles[i]=='protect_S' else None,
        clinical_relation_pair_certified=False,sample_weight=1) for i in order]
    summary=dict(N=192,optimizer_updates=24,role_counts=dict(Counter(roles.values())),GT=dict(Counter(meta[i]['GT'] for i in order)),
        patients=len({meta[i]['sid'] for i in order}),genuine_hard_by_GT=dict(Counter(meta[i]['GT'] for i in hard)),
        hard_false_S=sum(predictions_a[i]=='Supported' for i in hard),all_retention_current_correct=True,
        S_predictions_requested=len(required),S_neighbors_clinically_certified=False,all100_historically_exposed=True)
    return manifest,summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan_s','select'])
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    meta={r['id']:r for r in c.rows(a.bundle/'data/pool_metadata.jsonl')};config=c.read(a.bundle/'frozen/config109.json')
    source=c.read(a.bundle/'data/source_ids.json');neighbors=c.read(a.bundle/'data/neighbors.json')
    first=load_predictions(a.work/'mining_a/predictions.jsonl',c.read(a.bundle/'data/stage_a_ids.json'),meta)
    hard=choose_hard(meta,first,config);ids=supported_request(hard,neighbors,source,meta,config)
    c.put(a.work/'supported_request.json',dict(hard_ids=hard,ids=ids,chosen_by_current107_prediction=True,not_a_training_manifest=True))
    if a.action=='select':
        second=load_predictions(a.work/'mining_s/predictions.jsonl',ids,meta)
        manifest,summary=select(meta,first,second,neighbors,source,config)
        raw={r['id']:r for r in c.rows(a.bundle/'data/pool.jsonl')}
        c.putl(a.work/'selected_manifest.jsonl',manifest);c.putl(a.work/'train.jsonl',[raw[r['id']] for r in manifest])
        c.put(a.work/'selection_summary.json',summary);print(c.canonical(summary))
    else:print(c.canonical(dict(S_request_N=len(ids),hard_N=len(hard))))

if __name__=='__main__':main()
