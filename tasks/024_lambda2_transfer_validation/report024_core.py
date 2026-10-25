"""Render completed024 complete-case results; no new API or parameter selection."""
from collections import Counter
import core024 as c
def run():
    a=c.OUT/'analysis_001';m=c.read(a/'metrics.json');p=c.read(a/'paired.json');coh=c.read(a/'comparison_cohorts.json');d=c.read(a/'decision.json');cost=c.read(a/'costs.json');meta=c.read(a/'response_metadata.json')
    transitions=c.csvread(a/'transitions.csv');rows=c.csvread(c.OUT/'preparation_001/cohort.csv');pred={k:{r['proposition_id']:r for r in c.csvread(a/f'predictions_{k}.csv')} for k in c.MODELS}
    names={'deepseek':'DeepSeek0731','qwen':'Qwen27B'}
    def table(h,rr):return '\n'.join(['| '+' | '.join(h)+' |','|'+'|'.join('---' for _ in h)+'|']+['| '+' | '.join(map(str,r))+' |' for r in rr])
    def pct(x):return 'NA' if x is None else f'{100*x:.2f}%'
    def ci(x,k):
        v=x['metrics'][k];scale=100 if k=='percent_agreement' else 1
        return f"{v['delta']*scale:+.3f} [{v['ci95'][0]*scale:+.3f}, {v['ci95'][1]*scale:+.3f}]"
    lines=['# 024 固定λ=2跨后端与跨模型迁移验证','','## 结论','']
    for model in names:
        state='达到预登记强迁移证据标准' if d[model]['strong_transfer_evidence'] else '点估计方向支持，但未达到强迁移证据标准' if d[model]['direction_supported'] else '未达到总体方向支持标准'
        x=p[f'{model}/all/U2-minus-U0'];y=p[f'{model}/all/U2-minus-B']
        lines.append(f"- **{names[model]}：{state}。** U2−U0净正确{x['net_correct']:+d}/{x['coverage']['evaluated_n']}；U2−普通B净正确{y['net_correct']:+d}/{y['coverage']['evaluated_n']}。")
    if all(v['direction_supported'] for v in d.values()):
        lines+=['','同一个固定λ=2在两种Judge上均呈预登记总体收益方向，可以作为开发材料上的跨模型迁移证据；强弱程度以各自患者区间及类别代价为准。']
    elif d['deepseek']['direction_supported'] and not d['qwen']['direction_supported']:
        lines+=['','收益方向在DeepSeek后端迁移中保留，但没有无调参迁移到Qwen：当前证据更支持模型特异性，不能把固定λ=2称作普遍有效校准。']
    else:lines+=['','两模型没有同时满足预登记方向标准，跨模型泛化证据不足。不能根据本轮结果重新调λ或更换prompt补救。']
    lines+=['','**科研判断：λ修正本身的迁移信号已在两模型上复现——U2相对同次U0的PA/MCC患者区间均为正；但相对普通B的MCC区间均跨0。** 因而可以主张固定修正有跨Judge的开发证据，尚不能主张整个方案已稳定提高普通Judge的MCC。DeepSeek增益更大，也付出更多false-S和NS召回损失；Qwen增益较小、类别代价较轻。', '',
    '**后端桥接并未继承020的绝对成绩：** 阿里云DeepSeek普通B与旧条件接近，但评分U0及最终U2更低，U2较历史两轮少26–36条正确。λ仍有效，服务条件下的评分链路却有明显差异；不能把旧硅基流动成绩直接写成阿里云最终实现成绩。', '',
    '本轮到此停止，准备独立审计；未自动进入reserved40。固定λ=2不改。是否接受类别风险并冻结最终Judge，需要在审计后再决定；本轮不是最终测试，也不是本地部署验证。','','## 1. 固定设计与统一解析','',
    '复用020全部10名已暴露development患者879条valid atomic claims（human610、LLM269；S630、NS92、NA157）及冻结API-BGE C48。DeepSeek使用阿里云deepseek-v4-flash-0731，Qwen使用阿里云qwen3.8-27b；每模型普通structured B、019原scoring S各一次。仅model字段替换，原prompt、JSON schema、证据顺序、temperature=0、max_tokens=2048、enable_thinking=false保持。一次S给出V_raw、U0与U2；沿用019的floor和平分规则，只计算λ=0、2。', '',
    '用户在任何性能评价前明确授权amendment_002：verdict及S的label_scores为核心；reason/checks重复或结构异常只记录，不任取或人工合并冲突解释；原response不改。核心缺失/冲突/非法才invalid，HTTP200均不重跑。全部旧输出和新输出应用同一解析器；原严格解析状态、两次历史暂停和初次无损修订均保留。B原本不请求label_scores，不凭空要求其有评分。', '',
    f"共{cost['attempts']}次尝试、{cost['http200']}个HTTP200、{cost['valid_terminal']}个核心有效输出；缺失/核心无效{cost['invalid_missing']}。ID与原因见invalid_missing.json。普通解释不随U2后处理改写，不能把原reason当作新标签的完整解释。", '',
    '主比较按每项所需输出有效交集调用002 evaluate/paired_compare，1000次配对患者cluster bootstrap；各比较完整/排除ID及指纹见comparison_cohorts.json。模型直接比较仅用两模型相应输出共同有效集。下方描述表为各模型B/S共同有效集；主配对表使用各自所需集合，不能跨不同分母直接相减。','', '## 2. 总体性能与主要比较','']
    rr=[]
    for model in names:
        for arm in ('B','V_raw','U0','U2'):
            x=m[f'{model}/all/{arm}'];rr.append([names[model],arm,f"{x['counts']['correct']}/{x['n']}",pct(x['percent_agreement']),f"{x['mcc']:.4f}",f"{x['gwet_ac1']:.4f}",x['counts']['false_s']])
    lines +=[table(['模型','输出','正确/N','PA','MCC','AC1','false-S'],rr),'']
    rr=[]
    for model in names:
        for base in ('U0','B'):
            x=p[f'{model}/all/U2-minus-{base}'];rr.append([names[model],'U2−'+base,x['coverage']['evaluated_n'],f"{x['net_correct']:+d}",ci(x,'percent_agreement'),ci(x,'mcc'),ci(x,'gwet_ac1')])
    lines +=[table(['模型','比较','配对N','净正确','ΔPA百分点 [95%CI]','ΔMCC [95%CI]','ΔAC1 [95%CI]'],rr),'',
    '分母说明：DeepSeek唯一B无效的那条S有效，并被U2从U0错误救回。因此主描述表878条上的U2−U0为+61，而正确的S-only主比较879条为+62；这1条不能用于U2−B，也没有被丢出U2−U0。', '',
    '预登记“方向支持”要求U2对U0及B的总体PA和MCC四项点估计均>0；“强迁移证据”进一步要求四项95%患者区间下限均>0。区间跨0是统计不确定，不以单一高PA宣布成功，也不把同一患者的多个claim或两模型输出当作独立患者。','','## 3. Supported收益与类别代价','']
    direct=[]
    for arm in ('B','U0','U2'):
        x=p[f'qwen-minus-deepseek/all/{arm}'];direct.append([arm,x['coverage']['evaluated_n'],f"{x['net_correct']:+d}",ci(x,'percent_agreement'),ci(x,'mcc')])
    lines[-2:-2]=['跨模型辅助对照（Qwen−DeepSeek，仅共同有效集合；不替代迁移性主比较）：','',table(['输出','共同N','净正确','ΔPA百分点 [95%CI]','ΔMCC [95%CI]'],direct),'']
    rr=[]
    for model in names:
        for arm in ('B','U0','U2'):
            x=m[f'{model}/all/{arm}'];rr.append([names[model],arm,*[pct(x['per_class'][k]['recall']) for k in c.LABELS],f"{x['counts']['false_s']}/{x['false_s_denominator']}",pct(x['false_s_rate'])])
    lines +=[table(['模型','输出','S recall','NS recall','NA recall','false-S/真实non-S','false-S率'],rr),'']
    rr=[]
    for model in names:
        for author in ('all','human','llm'):
            ct=Counter(r['RHW'] for r in transitions if r['model']==model and (author=='all' or r['author_type']==author))
            rr.append([names[model],author,ct['R'],ct['H'],ct['W'],ct['R']-ct['H'],ct['H']+ct['W']])
    lines +=[table(['模型','作者','S rescue R','原正确non-S harm H','原错non-S新false-S W','净正确R−H','新增false-S H+W'],rr),'',
    'R/H/W使用同模型S有效配对集合。λ只增加Supported相对分数，不能直接修正NS与NA互混；新增false-S和净正确是不同量。所有三类混淆矩阵、TP/FN/FP及recall见metrics.json；分数为模型自报相对评分，不是经校准的医学概率。','','## 4. 作者与患者方向','']
    rr=[]
    for model in names:
        for author in ('human','llm'):
            for arm in ('B','U0','U2'):
                x=m[f'{model}/{author}/{arm}'];rr.append([names[model],author,arm,f"{x['counts']['correct']}/{x['n']}",pct(x['percent_agreement']),f"{x['mcc']:.4f}",f"{x['gwet_ac1']:.4f}",*[pct(x['per_class'][k]['recall']) for k in c.LABELS]])
    lines +=[table(['模型','作者','输出','正确/N','PA','MCC','AC1','S recall','NS recall','NA recall'],rr),'',
    '完整LLM队列269条中263条GT=S，仅6条non-S；Always-S PA=97.77%、MCC=0。因此LLM高PA不能单独作为成功证据，类别recall与MCC可能因极少数non-S翻转而明显改变。实际有效集合的Always-S指标同样保存。','']
    lines +=['尤其是DeepSeek：LLM的U2虽然PA高于B，MCC却从0.3022降到0.2924；human的MCC仅从0.5018升到0.5043。Qwen两作者MCC点估计均上升，但不据此忽略总体U2−B的MCC区间跨0。','']
    patient_pairs=[]
    for model in names:
        for base in ('U0','B'):
            key=f'{model}/all/U2-minus-{base}';included=set(coh[key]['included_ids']);vv=[]
            for sid in sorted({r['subject_id'] for r in rows}):
                rs=[r for r in rows if r['subject_id']==sid and r['proposition_id'] in included]
                change=sum(int(pred[model][r['proposition_id']]['U2']==r['human_gt'])-int(pred[model][r['proposition_id']][base]==r['human_gt']) for r in rs)
                vv.append(change);patient_pairs.append(dict(model=model,comparison='U2-minus-'+base,subject_id=sid,n=len(rs),delta_correct=change))
            lines.append(f"- {names[model]} U2−{base}：10名患者改善/持平/下降={sum(v>0 for v in vv)}/{sum(v==0 for v in vv)}/{sum(v<0 for v in vv)}；单患者净变化范围[{min(vv):+d}, {max(vv):+d}]。")
    if (a/'paired_patient_changes.json').exists():c.require(c.read(a/'paired_patient_changes.json')==patient_pairs,'Patient pair table changed')
    else:c.put(a/'paired_patient_changes.json',patient_pairs)
    lines +=['','逐患者、逐比较的分母和Δcorrect见[paired_patient_changes.json](analysis_001/paired_patient_changes.json)；患者/作者完整PA、MCC、AC1见patients.csv。','', '## 5. 历史后端差异、缺失敏感性与局限','']
    rr=[]
    for r in c.csvread(a/'historical_comparison.csv'):
        if r['new_model']=='deepseek' and r['arm'] in ('B','U0','U2'):rr.append([r['arm'],'020 R'+r['historical_repeat'],r['n'],r['net_correct'],r['label_flips']])
    lines +=[table(['阿里云DeepSeek输出','历史硅基流动参照','配对N','本轮−历史净正确','标签变化'],rr),'',
    '历史020与024非同期且服务条件/模型版本不能完全对齐。上述变化不能单独归因于供应商；核心迁移比较是各后端同一次score的U2−U0，以及同期U2−B。020 R0/R1是同879条重复调用，不是1758独立样本。024每模型只有一轮，不验证跨日稳定性。','']
    rr=[]
    for r in c.csvread(a/'missing_as_error.csv'):
        if r['author']=='all' and r['arm'] in ('B','U0','U2'):rr.append([names[r['model']],r['arm'],r['valid_n'],r['missing_n'],pct(float(r['missing_as_error_pa']))])
    lines +=[table(['模型','输出','有效N','缺失/invalid','缺失按错PA（分母879）'],rr),'',
    'missing-as-error只给正确数/全冻结分母的PA，不伪造S/NS/NA来算MCC。完整排除ID公开在机器结果中。没有为补分母重跑HTTP200，没有根据中途效果换样本。', '',
    '本研究只在已暴露development材料上作迁移验证；Qwen API结果不代表已验证本地部署、显存、速度或量化。模型自报评分尺度可能随模型变化，不能用本轮现象证明内部机制。无论迁移结果如何，都不重调λ、不改prompt、不启动新方法或reserved40。','', '## 6. 费用、自检与交审','',
    f"费用占用**{cost['total_occupied_cny']:.8f}/80元**：公开峰时无缓存usage估算{cost['usage_estimate_cny']:.8f}元＋未知保守预留{cost['unknown_reservation_cny']:.8f}元。不是供应商账单，未减缓存/闲时折扣。全部请求、回执、失败和重试保留。",'',
    '104次通信未知均保留并计预留；曾记录RemoteDisconnected/SSLEOFError及本地代理。任务进程改为直连同一阿里云端点后完成剩余请求，未改系统代理设置、endpoint、model或body；这种先后对比不是严格的网络因果实验。传输调度及源码指纹见amendment_002的network/transport记录。', '',
    '官方价格和服务登记见[registry](preparation_001/registry.json)，原协议见[protocol](protocol_001.md)，统一执行期修订见[amendment_002](amendment_002/README.md)。格式分类和诊断汇总见response_metadata.json，逐条解析见normalized.jsonl。U0/U2来自同一次S，λ后处理本身不增加API调用；B是本实验额外保留的同期对照。', '',
    '机器结果：[指标及混淆矩阵](analysis_001/metrics.json)、[配对比较](analysis_001/paired.json)、[每项比较样本ID](analysis_001/comparison_cohorts.json)、[缺失/invalid](analysis_001/invalid_missing.json)、[费用](analysis_001/costs.json)。自检与独立审计交接见audit_handoff.md。执行者自检不等于独立审计PASS。','']
    (c.OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
if __name__=='__main__':run()
