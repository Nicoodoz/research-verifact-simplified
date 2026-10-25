"""Render a concise Chinese report only from completed024 machine evaluation."""
from collections import Counter
import format024 as c
def run():
    a=c.OUT/'analysis_001';m=c.read(a/'metrics.json');p=c.read(a/'paired.json');cost=c.read(a/'costs.json');dec=c.read(a/'decision.json')
    patients=c.csvread(a/'patients.csv');ts=c.csvread(a/'transitions.csv');normalized=c.lines(a/'normalized.jsonl')
    names={'deepseek':'DeepSeek0731','qwen':'Qwen27B'}
    def mm(model,author,arm):return m[f'{model}/{author}/{arm}']
    def table(headers,rs):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+['| '+' | '.join(map(str,r))+' |' for r in rs])
    def pct(v):return 'NA' if v is None else f'{v*100:.2f}%'
    def interval(v,scale=1):return f"{v['delta']*scale:+.3f} [{v['ci95'][0]*scale:+.3f}, {v['ci95'][1]*scale:+.3f}]"
    def net(model,author,base):return mm(model,author,'U2')['counts']['correct']-mm(model,author,base)['counts']['correct']
    lines=['# 024 固定λ=2跨后端与跨模型迁移验证','', '## 结论','']
    for model in names:
        d=dec[model];state='达到预登记强迁移证据标准' if d['strong_transfer_evidence'] else '点估计方向支持，但未达到强迁移证据标准' if d['direction_supported'] else '未满足总体方向支持标准'
        lines.append(f"- **{names[model]}：{state}。** U2相对自身U0净{net(model,'all','U0'):+d}条、相对普通structured B净{net(model,'all','B'):+d}条。")
    lines+=['','本任务仅验证固定λ=2的迁移；未搜索其他λ、未改prompt或证据。两模型分别判断，不以模型绝对排名替代迁移结论。完成后停止并交独立审计，尚不进入reserved40。','', '## 1. 设计与实现','',
    '完整复用020的10名已暴露development患者879条valid atomic claims（human610、LLM269；S630、NS92、NA157）及API-BGE C48原文和顺序。两模型各B/S一次，共3516个合法终态。B是普通structured，S是019原版评分prompt；同一次S输出派生V_raw、U0及固定λ=2的U2。019的score floor和NS、NA、S平分优先级不变；002统一评价，all micro为主，1000次配对患者cluster bootstrap。', '',
    'DeepSeek请求与回传ID为deepseek-v4-flash-0731；Qwen为qwen3.8-27b。temperature=0、max_tokens=2048、enable_thinking=false，原JSON schema。Qwen仍是供应商服务别名，不证明不可变权重；本轮不证明本地推理、显存、速度或量化性能。原reason随V_raw保留，不为U2改写，也不当作后处理判定的完整解释。','',
    '初期一条输出出现相同reason重复。经用户明确授权，在任何性能评价前登记amendment_001：全024统一折叠值完全相同的重复JSON键，不同值仍异常；原response不修改、原严格解析状态保存。没有基于GT或效果决定修复，不重跑HTTP200。旧暂停状态及checkpoint_001保留。','', '## 2. 总体性能','']
    rows=[]
    for model in names:
        for arm in ('B','V_raw','U0','U2'):
            x=mm(model,'all',arm);rows.append([names[model],arm,f"{x['counts']['correct']}/879",pct(x['percent_agreement']),f"{x['mcc']:.4f}",f"{x['gwet_ac1']:.4f}",x['counts']['false_s']])
    lines +=[table(['模型','输出','正确数','PA','MCC','AC1','false-S'],rows),'','### 主配对比较（差值及95%患者区间）','']
    rows=[]
    for model in names:
        for base in ('U0','B'):
            q=p[f'{model}/all/U2-minus-{base}']['metrics'];rows.append([names[model],f'U2−{base}',f"{net(model,'all',base):+d}",interval(q['percent_agreement'],100),interval(q['mcc']),interval(q['gwet_ac1'])])
    lines +=[table(['模型','比较','净正确','ΔPA百分点 [CI]','ΔMCC [CI]','ΔAC1 [CI]'],rows),'',
    '预登记方向标准要求每模型U2相对U0和B的总体PA、MCC点估计全部为正；强证据标准进一步要求这四项95%区间下限均>0。类别代价与作者/患者异质性仍须单独披露。区间基于10名患者，不是879个独立患者；没有把两模型或历史两轮当作新增独立样本。','', '## 3. Supported收益与non-S代价','']
    rows=[]
    for model in names:
        for arm in ('B','U0','U2'):
            x=mm(model,'all',arm);rows.append([names[model],arm,*[pct(x['per_class'][label]['recall']) for label in c.LABELS],x['counts']['false_s'],pct(x['false_s_rate'])])
    lines +=[table(['模型','输出','S recall','NS recall','NA recall','false-S','false-S/真实non-S(249)'],rows),'']
    rows=[]
    for model in names:
        for author in ('all','human','llm'):
            r=Counter(x['RHW'] for x in ts if x['model']==model and (author=='all' or x['author_type']==author));rows.append([names[model],author,r['R'],r['H'],r['W'],r['R']-r['H'],r['H']+r['W']])
    lines +=[table(['模型','作者','S rescue R','原正确non-S harm H','原错non-S转false-S W','净正确 R−H','新增false-S H+W'],rows),'',
    'λ=2只提高Supported相对分数，不能直接修复NS与NA互相混淆。R−H是准确数收益；H+W是新增false-S，二者不是同一概念。label_scores仍是模型自报相对分数，不能解释为经校准的医学概率。','', '## 4. human/LLM与患者一致性','']
    rows=[]
    for model in names:
        for author in ('human','llm'):
            for arm in ('B','U0','U2'):
                x=mm(model,author,arm);rows.append([names[model],author,arm,f"{x['counts']['correct']}/{x['n']}",pct(x['percent_agreement']),f"{x['mcc']:.4f}",f"{x['gwet_ac1']:.4f}",x['counts']['false_s']])
    lines +=[table(['模型','作者','输出','正确数','PA','MCC','AC1','false-S'],rows),'',
    'LLM的269条中263条为Supported，只有6条non-S，Always-S PA=97.77%、MCC=0。必须结合MCC、NS/NA与false-S看LLM，不把高PA独立当作模型泛化。human及LLM各类recall、完整混淆矩阵与配对区间见metrics.json/paired.json。','']
    lookup={(x['model'],x['subject_id'],x['author'],x['arm']):x for x in patients}
    rows=[];direction={}
    for sid in sorted({x['subject_id'] for x in patients}):
        values=[]
        for model in names:
            for base in ('U0','B'):values.append(int(lookup[(model,sid,'all','U2')]['correct'])-int(lookup[(model,sid,'all',base)]['correct']))
        rows.append([sid,*[f'{v:+d}' for v in values]])
    lines +=[table(['患者','DeepSeek U2−U0','DeepSeek U2−B','Qwen U2−U0','Qwen U2−B'],rows),'']
    for model in names:
        for base in ('U0','B'):
            v=[int(lookup[(model,sid,'all','U2')]['correct'])-int(lookup[(model,sid,'all',base)]['correct']) for sid in sorted({x['subject_id'] for x in patients})]
            lines.append(f"- {names[model]} U2−{base}：患者改善/持平/下降={sum(x>0 for x in v)}/{sum(x==0 for x in v)}/{sum(x<0 for x in v)}；最大单患者净增={max(v):+d}、净减={min(v):+d}。")
    lines +=['','## 5. 与历史条件的关系及边界','',
    '本轮患者和证据与020相同，但属于新的阿里云服务条件，历史020是非同期硅基流动输出。不能把差异单独归因于服务供应商，更不能声称两边相同权重/内核。历史R0/R1同879条是重复输出，不能当成1758独立样本。本轮每模型只有一轮，不能评估跨日稳定性。','']
    hh=c.csvread(a/'historical_comparison.csv');rows=[]
    for r in hh:
        if r['new_model']=='deepseek' and r['arm'] in ('B','U0','U2'):
            rows.append(['DeepSeek0731',r['arm'],'020 R'+r['historical_repeat'],r['net_correct'],r['label_flips']])
    lines +=[table(['本轮模型','输出','历史参照','本轮−历史净正确','标签变化条数'],rows),'',
    '本任务没有新患者独立确认；复用020已暴露队列只能给出跨服务/模型迁移证据。若模型方向不同，应保留模型特异性结论，不调整λ补救。固定λ=2和API-BGE证据条件维持，reserved40须在024独立审计及另行授权后才可能启动。','', '## 6. 费用、格式与可复查材料','']
    repairs=[r for r in normalized if r.get('format_repair',{}).get('folded')]
    lines +=[f"- {cost['attempts']}次HTTP尝试，3516个合法终态；usage公开原价估算{cost['usage_estimate_cny']:.8f}元，未知预留{cost['unknown_reservation_cny']:.8f}元，总占用**{cost['total_occupied_cny']:.8f}/80元**。非供应商账单，未扣缓存/闲时优惠。",f"- {len(repairs)}条回答发生相同重复键折叠；原始回执不改。逐条原解析状态与修复记录在normalized.jsonl。",'- [冻结协议](protocol_001.md)、[服务/费用登记](preparation_001/registry.json)、[无损格式修订](amendment_001/README.md)。','- [主机器指标及混淆矩阵](analysis_001/metrics.json)、[配对区间](analysis_001/paired.json)、[患者结果](analysis_001/patients.csv)、[逐条R/H/W](analysis_001/transitions.csv)、[费用](analysis_001/costs.json)。','- 完整请求在preparation_001/jobs.jsonl及attempts，每次请求/原始回执通过hash绑定；评分及预测在analysis_001。独立审计交接见audit_handoff.md。','', '**执行完成不等于独立审计通过。本任务到此停止，不启动reserved test。**','']
    (c.OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
if __name__=='__main__':run()
