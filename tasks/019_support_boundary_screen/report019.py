"""Render factual 019 tables and case packets from preserved responses."""
from collections import Counter, defaultdict
import csv, json
import common019 as c
import analysis019 as a

def make():
    stages=[s for s in ('selection','validation') if (c.OUT/s/'analysis_001/metrics.json').exists()]
    ledger=c.read(c.OUT/'live_ledger.json');attempts=[];tokens=Counter();providers=Counter()
    for stage,phase in ledger['phases'].items():
        for rid,p in phase['jobs'].items():
            for ptr in p['receipts']:
                rec=c.read(c.OUT/ptr['file']);tr=rec['transport']
                attempts.append(dict(stage=stage,request_id=rid,http_status=tr['http_status'],provider=rec['provider'],account=rec['account'],charge_cny=ptr['charge_cny'],charge_basis=ptr['charge_basis'],receipt_file=ptr['file']))
                if tr['http_status']==200:
                    providers[(stage,rec['provider'],rec['account'])]+=1
                    try:
                        u=json.loads(tr['body_text']).get('usage',{})
                        for k in ('prompt_tokens','completion_tokens'):tokens[k]+=u.get(k,0)
                    except (ValueError,TypeError):pass
    lost=[dict(stage=s,request_id=rid,**x) for s,ph in ledger['phases'].items() for rid,p in ph['jobs'].items() for x in p.get('unreceipted_attempts',[])]
    summary=dict(HTTP_attempts=len(attempts)+len(lost),HTTP_receipts=len(attempts),unreceipted_attempts=len(lost),unknown_reservation_cny=sum(x['reserved_cny'] for x in lost)+sum(x['charge_cny'] for x in attempts if x['charge_basis']=='unknown_usage_reservation'),HTTP_status_counts=dict(Counter(r['http_status'] for r in attempts)),used_or_reserved_cny=ledger['used_or_reserved_cny'],cap_cny=80,usage=dict(tokens),
        providers=[dict(stage=s,provider=p,account=ac,answers=n) for (s,p,ac),n in providers.items()],stages_with_complete_metrics=stages,remaining10_used=False,reserved_test_used=False,independent_audit=False)
    c.write_json(c.OUT/'run_summary.json',summary);c.write_csv(c.OUT/'attempts.csv',attempts)
    text=['# 019：固定证据下的 Supported 判定边界筛查','',
        '执行报告。统计来自本轮原始回执；不代表独立审计PASS。',
        '原claim、完整C48和标签定义保持。B为同期原提示词，V_raw为增加评分后的原verdict，U0为评分argmax，U_lambda为只向S移动的离线偏置。','']
    if (c.OUT/'selection_freeze.json').exists():
        d=c.read(c.OUT/'selection_freeze.json')
        text+=['## 第一阶段决定',f"门槛：{'通过' if d['passed'] else '未通过'}；选定lambda={d['selected_lambda']}。",'未通过时不启动第二阶段，不追加prompt或扩大网格挽救。','']
    else:text+=['## 执行状态','未形成完整第一阶段选择结果；不能由传输或测量受阻否定科研假设。','']
    for stage in stages:
        folder=c.OUT/stage/'analysis_001';m=c.read(folder/'metrics.json');d=c.read(folder/'score_diagnostics.json')
        text+=['## '+stage,'两批患者均已用于历史研究，不是未接触测试患者。','',
            '|轮次|作者|方法|正确/N|PA%|AC1|MCC|false-S|S召回%|NS召回%|NA召回%|','|---|---|---|---|---|---|---|---|---|---|---|']
        for key,v in m.items():
            rep,author,arm=key.split('/');n=v['counts'];cl=v['per_class']
            fmt=lambda x:'NA' if x is None else f'{100*x:.2f}'
            rr=[fmt(cl[k]['recall']) for k in c.LABELS]
            text.append(f"|{rep}|{author}|{arm}|{n['correct']}/{n['n']}|{100*v['percent_agreement']:.2f}|{v['gwet_ac1']:.4f}|{v['mcc']:.4f}|{n['false_s']}|{rr[0]}|{rr[1]}|{rr[2]}|")
        text+=['','### 预设阈值与保护条件','|轮次|lambda|LLM净增|human净增|总净增|新增false-S|通过保护|R/H/W|','|---|---|---|---|---|---|---|---|']
        with (folder/'thresholds.csv').open(encoding='utf-8-sig',newline='') as f:
            for g in csv.DictReader(f):text.append(f"|{g['repeat']}|{g['lambda_value']}|{g['llm_gain']}|{g['human_gain']}|{g['total_gain']}|{g['false_s_added']}|{g['feasible']}|{g['boundary_R']}/{g['boundary_H']}/{g['boundary_W']}|")
        text+=['','### 评分诊断','```json',json.dumps(d,ensure_ascii=False,indent=2),'```','',
            f'完整患者bootstrap和配对区间见 `{stage}/analysis_001/metrics.json` 与 `paired.json`；同量随机对照和原始1000次抽样均保存在该目录。',
            '随机分布不是患者置信区间。PA提高不等于临床可靠性提高。O和C_history仅为历史参照。','']
    text+=['## 调用与费用','```json',json.dumps(summary,ensure_ascii=False,indent=2),'```',
        '按实际usage及已核实忙时无缓存价格估算，忽略折扣；未知usage保留上界。原始回答、失败和切换均保留。',
        '回执位于各阶段live；完整请求、schema和prompt diff位于preparation。没有重做检索、embedding、rerank、切分或训练。',
        '','## 解释边界','只能评价此评分/单参数流程对原医生GT一致性的影响。正确标签不证明证据充分；负结果不能自动归因检索；不产生新医学gold。',
        '','## 复查入口','[执行前协议](../../tasks/019_support_boundary_screen/README.md)；authority.json、history_before.json、live_ledger.json及selection_freeze.json（若形成）。']
    with (c.OUT/'statistics.md').open('x',encoding='utf-8') as f:f.write('\n'.join(text)+'\n')
    print(c.canonical(summary))

if __name__=='__main__':make()
