"""Compact publication tables and stage/actual-request cost ledger."""
from pathlib import Path
from collections import Counter,defaultdict
import study013 as s
from io013 import stage

def run():
    base=s.OUT/'screen_analysis_001';metrics=s.read_json(base/'metrics.json')
    rows=s.pilot.jsonl(base/'transitions.jsonl')
    results=[];classes=[];patients=[]
    methods=list(metrics['llm']['metrics'])
    for author in ('llm','human'):
        for arm,value in metrics[author]['metrics'].items():
            if value.get('status')=='blocked_missing':
                results.append(dict(author=author,arm=arm,n=value['expected_n'],status=value['status'],PA=None,AC1=None,MCC=None))
                continue
            results.append(dict(author=author,arm=arm,n=value['n'],status='complete',PA=value['percent_agreement'],AC1=value['gwet_ac1'],MCC=value['mcc']))
            for label,record in value['per_class'].items():classes.append(dict(author=author,arm=arm,label=label,**record))
        for sid in sorted({r['subject_id'] for r in rows}):
            own=[r for r in rows if r['author_type']==author and r['subject_id']==sid]
            patients.append(dict(author=author,subject_id=sid,n=len(own),**{arm:sum(r.get(arm)==r['human_gt'] for r in own) for arm in methods}))
    charges=[];phases=[]
    for manifest in sorted((s.OUT/'live').glob('*/manifest.json')):
        phase=manifest.parent.name
        values,attempts=stage(phase);charges+=attempts
        bykind=defaultdict(float)
        for a in attempts:bykind[values[a['request_id']]['job']['kind']]+=a['charge_cny']
        phases.append(dict(phase=phase,logical_requests=len(values),http_attempts=len(attempts),cost_or_reserved_cny=sum(a['charge_cny'] for a in attempts),
            costs_by_kind=dict(bykind),accounts=dict(Counter(a['account'] for a in attempts)),statuses=dict(Counter(a['http_status'] for a in attempts))))
    out=s.OUT/'synthesis_001';out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_csv(out/'metrics.csv',results);s.pilot.write_csv(out/'classes.csv',classes);s.pilot.write_csv(out/'patient_correct_counts.csv',patients)
    s.pilot.write_csv(out/'attempts.csv',charges)
    s.pilot.write_json(out/'costs.json',dict(stages=phases,total_cny=sum(a['charge_cny'] for a in charges),invoice_verified=False))
    md=['# 013机器生成核心表','', '|作者|方法|n|PA|AC1|MCC|','|---|---|---:|---:|---:|---:|']
    for r in results:md.append('|'+ '|'.join([r['author'],r['arm'],str(r['n'])]+[f'{r[k]:.4f}' if r[k] is not None else '缺失受阻' for k in ('PA','AC1','MCC')])+'|')
    md+=['','单位为原医生标签一致性。压力集非自然分布/新患者测试；刷新重排仅为控制。']
    (out/'results.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    s.freeze(out,[base/'metrics.json',base/'transitions.jsonl'],[Path(__file__)])
    print(s.pilot.canonical(phases))

if __name__=='__main__':run()
