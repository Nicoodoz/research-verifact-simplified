"""Update one compact cycle report from completed, published-safe analyses."""
from pathlib import Path
import json,time

R=Path(__file__).resolve().parents[2]
O=R/'outputs/116_research_cycle'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,value):p.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())

def main():
    state=read(O/'cycle_state.json');rows=[];analyses=[]
    for name in state['completed_jobs']:
        path=O/(name+'.json')
        if not path.exists():continue
        result=read(path);analyses.append(result)
        for panel,part in result['panels'].items():
            for arm,score in part['scores'].items():
                rows.append(dict(job=name,panel=panel,arm=arm,N=part['N'],expected_N=part.get('expected_N',part['N']),MCC=score['mcc'],PA=score['percent_agreement'],correct=score['correct'],false_S=score['false_S'],non_S=score['non_S'],recall={g:v['recall'] for g,v in score['per_class'].items()}))
    (O/'comparison.jsonl').write_bytes(('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n').encode())
    elapsed=time.time()-state['start_epoch'];cost=elapsed*state['hourly_CNY']/3600
    write(O/'cost_status.json',dict(start_beijing=state['start_beijing'],snapshot_epoch=time.time(),elapsed_seconds=elapsed,GPU_estimate_CNY=cost,GPU_cap_CNY=state['GPU_cap_CNY'],API_CNY=state['paid_API_CNY'],API_cap_CNY=state['API_cap_CNY'],estimate_not_platform_invoice=True,no_shutdown=True,cycle_status=state['status']))
    lines=['# 自主研究周期1：阶段结果','',
           '107 label_only仍是主基线。以下均为原20名患者的开发筛查，原医生GT保留；后40人尚未用于选型或确认。各候选首次回执保留，未按结果重发。','',
           '|候选/面板|配置|MCC|PA|正确数/有效数|false-S/有效非S|有效/计划|',
           '|---|---|---:|---:|---:|---:|---:|']
    for row in rows:
        arm={'candidate':next(a['candidate'] for a in analyses if a['job']==row['job']),'label_only107':'107 label_only','paper_r1':'作者历史R1'}[row['arm']]
        lines.append(f"|{row['job']}/{row['panel']}|{arm}|{row['MCC']:.4f}|{row['PA']:.2%}|{row['correct']}/{row['N']}|{row['false_S']}/{row['non_S']}|{row['N']}/{row['expected_N']}|")
    lines+=['','## 去留与解释','']
    for result in analyses:
        name=result['job'];screen=result.get('screen',{})
        decision=state.get('decisions',{}).get(name)
        if not decision:decision='达到预写粗筛信号，继续扩大' if screen.get('continue_') else ('未达到预写粗筛信号，不据局部改善宣称成功' if screen else '已完成扩展，按较大开发结果判断')
        lines.append(f"- `{name}`：{decision}。")
        for panel,part in result['panels'].items():
            cl=part['changes']['by_class'];changes='；'.join(f"{g}救回{z['rescued']}、误伤{z['harmed']}" for g,z in cl.items())
            lines.append(f"  - {panel}：{changes}；新增false-S {part['changes']['false_S_new']}、避免{part['changes']['false_S_avoided']}。")
    strata=O/'claim_repeat_1817_missing_strata.json'
    if strata.exists():
        v=read(strata)['sections']['selection1817'];ci=v['patient_paired']['metrics']['mcc']['ci95']
        better=sum(p['scores']['candidate']['correct']>p['scores']['base']['correct'] for p in v['patients'])
        worse=sum(p['scores']['candidate']['correct']<p['scores']['base']['correct'] for p in v['patients'])
        lines+=['',f"claim_repeat完整1817的MCC差值患者分组95%区间为[{ci[0]:+.4f}, {ci[1]:+.4f}]（1000次bootstrap）；正确数增加{better}名患者、减少{worse}名患者。区间跨0不表示等效，也不足以支持稳定增益。相对107只是较小点估计收益，不占用唯一的确认40人机会。"]
    lines+=['','## 方法与代价','',
            '`joint_path`复用115最终适配器，枚举三个完整JSON+EOS路径并按总条件logP决策；每例三次完整前向。它联合验证115目标与路径决策，不能用仅比115原greedy好来宣布超过107。',
            '',
            '与115原greedy有回执交集的70条中，自然35条正确24→22，压力35条21→22，正确S救回0、额外误伤1。该描述性交集没有支持“改用完整路径即可挽救115”的解释，也不能外推为全部样本的机制证明。',
            '',
            '`claim_repeat`复用107，在完整reference之外的消息末端重述同一待核验命题；未增添EHR事实、GT、其他模型答案或逐例规则。',
            '',
            '范围：原103的180条与旧500仅重合70条（自然35、压力35）。因此补齐旧500实际新增430次，再补完整1817需要1207次；已有110条“旧500之外”的原180预测继续复用。180与500不是严格包含关系，不能把两张表的差值直接解释成新增320条的表现。',
            '',
            '对其自然面板6条S救回及1条S误伤做了定向原文检查：5条救回有较明确可见依据，1条缺关键时间段，误伤例也有可见支持。3条有依据救回来自同一患者。这不是随机病例审查，不能证明模型使用了对应证据，或排除更偏S；缺证例仍保留医生原GT。临床正文与逐例笔记仅在私有目录。',
            '',
            '`single_token_768`是待验证的完整判别配方：原9B、准备768条真实训练命题、32名梯度患者，另8名患者128条只用于选checkpoint。原临床定义与完整输入保留，A/B/C三行固定词表投影作唯一三类CE。原上限96步；按用户时间优先补充，先在24步内部验证后暂停并评价固定180，实际用量另报。不把它当作纯组件消融或新的原创算法。',
            '',
            '短训练实际完成24步、192条不同命题（S96/NS48/NA48），涉及31名梯度患者；内部验证仍为独立8人128条。按原内部选点规则选择第24步，未再更新权重。内部MCC0.5323→0.5989、false-S23→13，同时正确S60→56；这是训练侧信号，不能代替20名选型患者上的真实分类收益。',
            '',
            '三类完整指标、混淆矩阵、逐例配对变化与患者方向保存在各候选JSON。当前粗筛不例行bootstrap；有值得保留的较大开发收益后再补必要稳定性分析。作者R1只作历史同ID参照。',
            '',
            f"周期起点{state['start_beijing']}（北京时间），截止{state['deadline_beijing']}；本报告生成时GPU墙钟估算¥{cost:.3f}/20、API ¥{state['paid_API_CNY']}/20。估算包含等待和回传，不是平台精确账单。",
            '',
            f"状态：{state['status']}；当前任务`{state.get('active_job')}`；最佳`{state['best_candidate']}`。不自动关机，实例继续开机会继续计费。",
            '',
            '依据：[周期备忘](../../tasks/116_research_cycle/memo.md)、[预写粗筛规则](../../tasks/116_research_cycle/screen_rules.json)、[单token配置](../../tasks/116_research_cycle/single_token_config.json)。']
    (O/'report.md').write_bytes(('\n'.join(lines)+'\n').encode())
    print(json.dumps(dict(rows=len(rows),completed=state['completed_jobs'],GPU_estimate_CNY=cost),ensure_ascii=False))

if __name__=='__main__':main()
