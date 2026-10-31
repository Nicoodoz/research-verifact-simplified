"""Five frozen baseline readers and the project's shared evaluation path."""
from pathlib import Path
import json,sys,statistics
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.evaluation import evaluate,paired_compare
LABELS=('Supported','Not Supported','Not Addressed')

def rows(path):
    p=Path(path)
    if not p.exists():return []
    return [json.loads(line) for line in p.read_text(encoding='utf-8-sig').splitlines() if line.strip()]

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def collect(folders):
    found={}
    for folder in folders:
        for p in Path(folder).glob('*.json'):
            r=read(p)
            if 'id' not in r:continue
            if r['id'] in found and found[r['id']]!=r:raise ValueError('Conflicting first receipt')
            found[r['id']]=r
    return found

def valid(row):return row.get('parsed',{}).get('valid') is True and row['parsed'].get('verdict') in LABELS

def assets():
    keys={r['id']:r for r in rows(ROOT/'.local_models/134_author_baselines/keys.jsonl')}
    assert len(keys)==1817
    raw136=collect([ROOT/'.local_models/136_claim_repeat_transfer/evidence'/s/'claim_repeat' for s in ['screen160','old500','full1817']])
    assert len(raw136)==1817 and all(valid(r) for r in raw136.values())
    raw120={r['id']:r for r in rows(ROOT/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')}
    author={name:collect([ROOT/'.local_models/134_author_baselines/evidence'/name,ROOT/'.local_models/134_author_baselines/bundle/results'/name]) for name in ('author_base9b','author_lora9b')}
    predictions={'paper_r1':{i:r['paper_r1'] for i,r in keys.items()},
                 'author_base9b':{i:r['parsed']['verdict'] for i,r in author['author_base9b'].items() if valid(r)},
                 'author_lora9b':{i:r['parsed']['verdict'] for i,r in author['author_lora9b'].items() if valid(r)},
                 'full_pool120':{i:r['verdict'] for i,r in raw120.items() if r.get('valid') is True},
                 'claim_repeat136':{i:r['parsed']['verdict'] for i,r in raw136.items()}}
    raw={'paper_r1':{},'author_base9b':author['author_base9b'],'author_lora9b':author['author_lora9b'],'full_pool120':raw120,'claim_repeat136':raw136}
    return keys,predictions,raw

def cohort(ids,keys):return [dict(proposition_id=i,subject_id=str(keys[i]['sid']),human_gt=keys[i]['GT']) for i in sorted(ids)]
def predrows(ids,pred):return [dict(proposition_id=i,verdict=pred[i]) for i in sorted(ids)]
def score(ids,pred,keys,bootstrap=False):
    ids=set(ids)
    m=evaluate(cohort(ids,keys),predrows(ids,pred),profile='research_patient' if bootstrap else 'none',iterations=1000)
    m['correct']=round(m['percent_agreement']*m['n'])
    m['false_S']=sum(keys[i]['GT']!='Supported' and pred[i]=='Supported' for i in ids)
    m['non_S']=sum(keys[i]['GT']!='Supported' for i in ids)
    s=sum(pred[i]=='Supported' for i in ids)
    m['false_S_non_S']=m['false_S']/m['non_S'] if m['non_S'] else None
    m['S_FDR']=m['false_S']/s if s else None
    m['macro_f1']=statistics.mean(m['per_class'][g]['f1'] for g in LABELS)
    return m

def pair(ids,base,candidate,keys):
    ids=set(ids)&base.keys()&candidate.keys()
    return paired_compare(cohort(ids,keys),predrows(ids,base),predrows(ids,candidate),iterations=1000)

def cost(ids,raw):
    rr=[raw[i] for i in ids if i in raw]
    result={'attempted_records':len(rr)}
    for field in ('seconds','input_tokens','output_tokens'):
        values=[r[field] for r in rr if isinstance(r.get(field),(int,float))]
        result[field]=dict(recorded_N=len(values),total=sum(values) if values else None,mean=statistics.mean(values) if values else None)
    result['batch_size_counts']={str(v):sum(r.get('batch_size')==v for r in rr) for v in set(r.get('batch_size') for r in rr)}
    result['historical_money_CNY']=None
    return result

def five_table(ids,keys,predictions,raw,extra=None):
    pred=dict(predictions)
    if extra:pred.update({k:v[0] for k,v in extra.items()})
    joint=set(ids).intersection(*(p.keys() for p in pred.values()))
    return dict(N=len(joint),requested_N=len(set(ids)),missing_or_invalid={k:len(set(ids)-p.keys()) for k,p in pred.items()},
                scores={k:score(joint,p,keys) for k,p in pred.items()},
                costs={k:cost(joint,extra[k][1] if extra and k in extra else raw[k]) for k in pred})

def markdown_table(table):
    lines=['|配置|N|MCC|PA|正确|S/NS/NA recall|false-S/non-S|生成秒（记录N）|输入/输出tokens（记录N）|历史费用|',
           '|---|---:|---:|---:|---:|---|---|---|---|---|']
    def field(value):return '未记录' if value['total'] is None else f"{value['total']:.2f}（{value['recorded_N']}）"
    for name,m in table['scores'].items():
        c=table['costs'][name];rec='/'.join(f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
        lines.append(f"|{name}|{m['n']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{rec}|{m['false_S']}/{m['non_S']}|{field(c['seconds'])}|{field(c['input_tokens'])}/{field(c['output_tokens'])}|未记录（历史分摊）|")
    return '\n'.join(lines)
