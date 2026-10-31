"""Fixed-scope paired comparisons for matched runtime claim_control."""
from pathlib import Path
from collections import Counter
import argparse,json,sys
R=Path(__file__).resolve().parents[2];P=R/'.local_models/139_full_repeat'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/135_reason_first'));from analyze135 import collect
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS
from prepare_claim_control139 import RUNS,source136


def compare(rows,old,new,old_name,new_name,bootstrap=False):
    if not rows:return None
    value=paired(rows,{r['id']:dict(verdict=old[r['id']]) for r in rows},
                 {r['id']:dict(verdict=new[r['id']]) for r in rows},old_name,bootstrap=bootstrap)
    value['scores'][new_name]=value['scores'].pop('candidate')
    value['direction']=new_name+' minus '+old_name
    return value


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=list(RUNS),default='screen160')
    ap.add_argument('--control',type=Path,nargs='+');ap.add_argument('--full',type=Path,nargs='+')
    ap.add_argument('--out',type=Path);ap.add_argument('--bootstrap',action='store_true');a=ap.parse_args()
    scopes=list(RUNS)[:list(RUNS).index(a.scope)+1]
    control_paths=a.control or [P/RUNS[s]/'evidence/claim_control' for s in scopes]
    full_paths=a.full or [P/'evidence'/s/'full_repeat' for s in scopes]
    a.out=a.out or P/RUNS[a.scope]/'comparison'
    keys={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/keys.jsonl')}
    screen=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    target=screen if a.scope=='screen160' else ({i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')} if a.scope=='old500' else set(keys))
    control_inputs,old136=source136()
    data={'claim_control':collect(control_paths),'full_repeat':collect(full_paths),'old136':old136}
    for name,records in data.items():
        if not set(records)<=set(keys):raise ValueError('Unknown ID in '+name)
        data[name]={i:row for i,row in records.items() if i in target}
    sha=c.read(P/'source/settings.json')['adapter_sha256']
    full_inputs={r['id']:r for r in c.rows(P/'source/all1817_inputs.jsonl')}
    for name in ('claim_control','full_repeat'):
        for i,row in data[name].items():
            assert row['arm']==name and row['adapter_sha256']==sha
            expected=control_inputs if name=='claim_control' else full_inputs
            assert row['prompt_token_sha256']==expected[i]['prompt_token_sha256']
    valid={name:{i:r['parsed']['verdict'] for i,r in records.items() if r['parsed']['valid']} for name,records in data.items()}
    common=sorted(set.intersection(*(set(v) for v in valid.values())))
    rows=[keys[i] for i in common]
    full_ids=sorted(set(valid['claim_control'])&set(valid['full_repeat']))
    claim_ids=sorted(set(valid['claim_control'])&set(valid['old136']))
    bootstrap=a.bootstrap or a.scope=='full1817'
    full_vs_control=compare([keys[i] for i in full_ids],valid['claim_control'],valid['full_repeat'],'claim_control','full_repeat',bootstrap)
    control_vs_old=compare([keys[i] for i in claim_ids],valid['old136'],valid['claim_control'],'old136','claim_control',bootstrap)
    def grouped(ids,old,new,old_name,new_name):
        result={}
        for field,values in [('author',sorted({keys[i]['author'] for i in ids})),('old_panel',['natural','pressure'])]:
            result[field]={v:compare([keys[i] for i in ids if keys[i][field]==v],old,new,old_name,new_name) for v in values}
        parts={'all':[keys[i] for i in ids],
               'new1317':[keys[i] for i in ids if keys[i].get('subset')=='new'],
               'history103_180':[keys[i] for i in ids if keys[i].get('history103_panel') in ('natural','pressure')]}
        result['panels']={name:compare(part,old,new,old_name,new_name) for name,part in parts.items() if part}
        return result
    score={name:metrics(rows,pred) for name,pred in valid.items()} if rows else {}
    coverage={name:dict(received=len(records),valid=len(valid[name]),missing_N=len(target-set(records)),
        invalid_N=len(set(records)-set(valid[name])),missing_ids=sorted(target-set(records)),
        invalid_ids=sorted(set(records)-set(valid[name])),
        invalid_by_GT=dict(Counter(keys[i]['GT'] for i in set(records)-set(valid[name])))) for name,records in data.items()}
    own_scores={}
    for name,pred in valid.items():
        if pred:
            metric=metrics([keys[i] for i in sorted(pred)],pred)
            metric['PA_full_target_bounds']=[metric['correct']/len(target),(metric['correct']+len(target)-len(pred))/len(target)]
            own_scores[name]=metric
    result=dict(task=139,scope=a.scope+'_runtime_control',evaluation_scope=a.scope,N=len(target),common_valid_N=len(rows),scores=score,
        full_repeat_vs_claim_control=full_vs_control,claim_control_vs_old136=control_vs_old,coverage=coverage,
        own_valid_scores=own_scores,patient_bootstrap_iterations=1000 if bootstrap else 0,
        full_vs_control_groups=grouped(full_ids,valid['claim_control'],valid['full_repeat'],'claim_control','full_repeat'),
        control_vs_old_groups=grouped(claim_ids,valid['old136'],valid['claim_control'],'old136','claim_control'),
        new_training=False,new_API=0,
        interpretation='full_repeat vs claim_control matches runtime batch1/capacity32768; control vs old136 measures runtime-associated difference, not isolated batch-size causality.')
    a.out.mkdir(parents=True,exist_ok=True);c.put(a.out/'comparison.json',result)
    c.putl(a.out/'receipt_status.jsonl',[dict(id=i,**{name:dict(received=i in records,valid=i in valid[name],verdict=valid[name].get(i)) for name,records in data.items()}) for i in sorted(target)])
    lines=['#139 matched runtime control:'+a.scope,'',f'三者共同有效{len(rows)}/{len(target)}；缺失/invalid不补旧答案。','',
        '|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
    for name,m in score.items():
        rec='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
        lines.append(f"|{name}|{m['mcc']:.6f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{rec}|")
    for value in [full_vs_control,control_vs_old]:
        if value:lines+=['',f"{value['direction']}（N={value['N']}）：ΔMCC{value['delta_MCC']:+.6f}、Δ正确{value['delta_correct']:+d}、ΔFS{value['delta_false_S']:+d}。"]
    lines+=['','三类precision/recall/F1、混淆矩阵、false-S率、预测S假发现率、患者方向与作者/面板分组见JSON。',
        'full1817默认1000次患者配对bootstrap；不覆盖历史选型、重训及新医院泛化。',
        '运行时对照不训练、不重跑full_repeat；不能把旧136与控制的差别全归因为单一batch因素。','']
    (a.out/'comparison.md').write_bytes('\n'.join(lines).encode('utf-8'))
    print(c.canonical(dict(common_valid_N=len(rows),coverage={k:dict(received=v['received'],valid=v['valid']) for k,v in coverage.items()},
        full_minus_control=None if not full_vs_control else {k:full_vs_control[k] for k in ('delta_MCC','delta_correct','delta_false_S')},
        control_minus_old136=None if not control_vs_old else {k:control_vs_old[k] for k in ('delta_MCC','delta_correct','delta_false_S')})))


if __name__=='__main__':main()
