"""Direct160-ID paired comparisons for matched runtime claim_control."""
from pathlib import Path
import argparse,json,sys
R=Path(__file__).resolve().parents[2];P=R/'.local_models/139_full_repeat'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/135_reason_first'));from analyze135 import collect
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS


def compare(rows,old,new,old_name,new_name,bootstrap=False):
    if not rows:return None
    value=paired(rows,{r['id']:dict(verdict=old[r['id']]) for r in rows},
                 {r['id']:dict(verdict=new[r['id']]) for r in rows},old_name,bootstrap=bootstrap)
    value['scores'][new_name]=value['scores'].pop('candidate')
    value['direction']=new_name+' minus '+old_name
    return value


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--control',type=Path,default=P/'claim_control160/evidence/claim_control')
    ap.add_argument('--full',type=Path,default=P/'evidence/screen160/full_repeat')
    ap.add_argument('--out',type=Path,default=P/'claim_control160/comparison');ap.add_argument('--bootstrap',action='store_true');a=ap.parse_args()
    keys={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/keys.jsonl')}
    target=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    data={'claim_control':collect([a.control]),'full_repeat':collect([a.full]),
          'old136':collect([R/'.local_models/136_claim_repeat_transfer/evidence/screen160/claim_repeat'])}
    for name,records in data.items():
        if not set(records)<=target:raise ValueError('Unexpected ID in '+name)
    sha=c.read(P/'source/settings.json')['adapter_sha256']
    for name in ('claim_control','full_repeat'):
        for i,row in data[name].items():
            assert row['arm']==name and row['adapter_sha256']==sha
            if name=='claim_control':assert row['prompt_token_sha256']==data['old136'][i]['prompt_token_sha256']
    valid={name:{i:r['parsed']['verdict'] for i,r in records.items() if r['parsed']['valid']} for name,records in data.items()}
    common=sorted(set.intersection(*(set(v) for v in valid.values())))
    rows=[keys[i] for i in common]
    full_ids=sorted(set(valid['claim_control'])&set(valid['full_repeat']))
    claim_ids=sorted(set(valid['claim_control'])&set(valid['old136']))
    full_vs_control=compare([keys[i] for i in full_ids],valid['claim_control'],valid['full_repeat'],'claim_control','full_repeat',a.bootstrap)
    control_vs_old=compare([keys[i] for i in claim_ids],valid['old136'],valid['claim_control'],'old136','claim_control',a.bootstrap)
    def grouped(ids,old,new,old_name,new_name):
        result={}
        for field,values in [('author',sorted({keys[i]['author'] for i in ids})),('old_panel',['natural','pressure'])]:
            result[field]={v:compare([keys[i] for i in ids if keys[i][field]==v],old,new,old_name,new_name) for v in values}
        return result
    score={name:metrics(rows,pred) for name,pred in valid.items()} if rows else {}
    coverage={name:dict(received=len(records),valid=len(valid[name]),missing_ids=sorted(target-set(records)),
        invalid_ids=sorted(set(records)-set(valid[name]))) for name,records in data.items()}
    result=dict(task=139,scope='screen160_runtime_control',N=160,common_valid_N=len(rows),scores=score,
        full_repeat_vs_claim_control=full_vs_control,claim_control_vs_old136=control_vs_old,coverage=coverage,
        full_vs_control_groups=grouped(full_ids,valid['claim_control'],valid['full_repeat'],'claim_control','full_repeat'),
        control_vs_old_groups=grouped(claim_ids,valid['old136'],valid['claim_control'],'old136','claim_control'),
        new_training=False,new_API=0,
        interpretation='full_repeat vs claim_control matches runtime batch1/capacity32768; control vs old136 measures runtime-associated difference, not isolated batch-size causality.')
    a.out.mkdir(parents=True,exist_ok=True);c.put(a.out/'comparison.json',result)
    c.putl(a.out/'receipt_status.jsonl',[dict(id=i,**{name:dict(received=i in records,valid=i in valid[name],verdict=valid[name].get(i)) for name,records in data.items()}) for i in sorted(target)])
    lines=['#139 matched runtime control:160','',f'三者共同有效{len(rows)}/160；缺失/invalid不补旧答案。','',
        '|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
    for name,m in score.items():
        rec='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
        lines.append(f"|{name}|{m['mcc']:.6f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{rec}|")
    for value in [full_vs_control,control_vs_old]:
        if value:lines+=['',f"{value['direction']}（N={value['N']}）：ΔMCC{value['delta_MCC']:+.6f}、Δ正确{value['delta_correct']:+d}、ΔFS{value['delta_false_S']:+d}。"]
    lines+=['','三类precision/recall/F1、混淆矩阵、false-S率、预测S假发现率、患者方向与作者/面板分组见JSON。','运行时对照不训练、不重跑full_repeat；不能把旧136与控制的差别全归因为单一batch因素。','']
    (a.out/'comparison.md').write_bytes('\n'.join(lines).encode('utf-8'))
    print(c.canonical(dict(common_valid_N=len(rows),coverage={k:dict(received=v['received'],valid=v['valid']) for k,v in coverage.items()},
        full_minus_control=None if not full_vs_control else {k:full_vs_control[k] for k in ('delta_MCC','delta_correct','delta_false_S')},
        control_minus_old136=None if not control_vs_old else {k:control_vs_old[k] for k in ('delta_MCC','delta_correct','delta_false_S')})))


if __name__=='__main__':main()
