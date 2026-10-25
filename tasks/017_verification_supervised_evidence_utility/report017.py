"""Render the headroom-stop report from saved002 results; no decisions or API calls."""
from collections import Counter
from pathlib import Path
import argparse
import common017 as c

NAMES={'baseline':'原C48','c48_local':'C48内同note替换','c48_crossnote':'C48内跨note替换','wide_swap':'宽池单段替换','wide_relevance':'宽池＋原selection'}
SHORT={'Supported':'S','Not Supported':'NS','Not Addressed':'NA'}

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def render(output=None):
    output=output or c.OUT/'report.md'
    root=c.OUT/'analysis_001';s=c.read(root/'summary.json');g=c.read(root/'gate.json');m=c.read(root/'metrics.json');paired=c.read(root/'paired.json')
    c.require(not g['passed'],'This renderer is for the preregistered headroom stop only')
    c.require(not output.exists(),'Do not overwrite an existing report')
    results=c.csvrows(root/'core_results.csv');changes=c.csvrows(root/'changes.csv');strata=c.csvrows(root/'strata.csv')
    events=c.csvrows(root/'utility_events.csv');cases=c.csvrows(root/'cases.csv')
    prep=c.read(c.OUT/'preparation_001/summary.json')
    names={'complete':'完整覆盖','eligible':'可干预样本数','stable_error_coverage':'稳定错误覆盖','stable_correct_coverage':'稳定正确覆盖',
        'substantial_rescue':'稳定rescue≥max(12,25%稳定错误)','rescue_patients':'rescue覆盖≥4患者','both_authors_rescue':'两作者rescue各≥3',
        'same_pool_rescue':'同池rescue≥6且≥3患者','harm_rate':'稳定正确harm比例≤20%','baseline_flip_rate':'baseline翻转率≤15%',
        'train_pairs':'训练组非零稳定配对≥16且≥3患者'}
    failures='；'.join(names[k] for k,v in g['conditions'].items() if not v)
    rc=g['stable_rescued'];we=g['stable_errors'];ha=g['stable_harmed'];co=g['stable_correct']
    strong=[e for e in events if int(e['utility'])]
    train=[e for e in strong if e['split']=='train']
    coverage=lambda flag:len({r['subject_id'] for r in cases if r[flag]=='True'})
    first=[]
    for r in results:
        if r['repeat']=='0':first.append([r['author'],NAMES[r['arm']],r['correct']+'/96',f"{float(r['PA'])*100:.2f}%",f"{float(r['AC1']):.4f}",f"{float(r['MCC']):.4f}"])
    repeated=[]
    for author in ('llm','human'):
        for arm in c.ARMS[1:]:
            a=next(r for r in changes if r['author']==author and r['arm']==arm and r['repeat']=='0')
            b=next(r for r in changes if r['author']==author and r['arm']==arm and r['repeat']=='1')
            delta=paired['0'][author][arm]['differences'] if 'differences' in paired['0'][author][arm] else paired['0'][author][arm]['metrics']
            ci=delta['mcc']['ci95']
            repeated.append([author,NAMES[arm],a['rescue']+'/'+a['harm'],f"{int(a['net']):+d}",f"{int(b['net']):+d}",f"[{ci[0]:+.3f},{ci[1]:+.3f}]"])
    classes=[]
    for author in ('llm','human'):
        for label in c.LABELS:
            classes.append([author,SHORT[label],m['0'][author]['baseline']['per_class'][label]['support']]+[m['0'][author][arm]['per_class'][label]['tp'] for arm in c.ARMS])
    patientrows=[[r['value'],r['stable_wrong'],r['stable_rescued'],r['same_pool_rescued'],r['stable_correct'],r['stable_harmed']] for r in strata if r['dimension']=='subject_id']
    authorrows=[[r['value'],r['stable_wrong'],r['stable_rescued'],r['stable_correct'],r['stable_harmed']] for r in strata if r['dimension']=='author_type']
    classrows=[[SHORT[r['value']],r['stable_wrong'],r['stable_rescued'],r['stable_correct'],r['stable_harmed']] for r in strata if r['dimension']=='human_gt']
    text=f'''# 017：verification utility弱监督——正式主报告

## 结论

**第一阶段未达到事前headroom门槛，停止017；不训练selector，不使用剩余10名development患者确认。** 192条GT盲抽样中，稳定baseline错误{we}条，有限证据替换稳定救回{rc}条（{rc/we:.1%}）；稳定正确{co}条中，有{ha}条被至少一种替换稳定破坏（{ha/co:.1%}）。失败条件：{failures}。

本轮没有形成可作为论文方法候选的learned selector。结论仅约束这次有限候选池和单段替换方案，不证明所有evidence utility学习都无效。

还需保留一个重要限制：稳定错误只有19条，低于预设至少24条的覆盖要求，尤其LLM侧仅3条。因此这次属于“未获得足够继续依据”，不能把0/19解释成总体没有可修复错误，也不事后改成按错误补抽样本。

## 为什么做、实际做了什么

009/012已有“候选存在但未选入”等真实损失；013宽候选和普通LLM selector均无净收益；016独立复核亦未复现明显提升。因此017检验更小的选择干预能否产生足够、可重复的claim级弱监督，再决定是否值得学习，科研问题是**只有医生verdict时，是否能得到跨患者可用的证据utility信号**。

- 使用已暴露开发序19–30的12名患者，每患者／作者固定ID哈希前8条，共192条（LLM/human各96）；未按GT、错误或013压力集抽样。baseline正确／错误和类别覆盖事后报告，不补抽。这是患者／作者等额样本，比例不直接外推到自然全队列。
- 保留原claim、C48 formatter、V4-Flash structured prompt、标签定义及生成参数。三个GT盲规则各最多替换一整段：C48内同note、C48内跨note、宽池外来段。段数、其余证据不变，长度为原包90%–110%，相同每note／总段数／8000字符限制。没有合法动作则保留baseline。
- 宽池W复用已有真实BGE评分的A48∪B48∪C48，共{prep['wide_candidates_range'][0]}–{prep['wide_candidates_range'][1]}个候选；另用W＋原selection作容量对照。没有刷新分数、新检索或改packing。**W不是013两路top80宽池**，013 wide净−5仅是不同队列／范围的历史参照。
- 全部干预和完整请求先冻结，再读取评价GT；Judge仅看claim和reference。每条件两次独立调用，相同body在同一轮事前共享；1920逻辑条件对应1572个请求。两次baseline相同、两次干预相同且供应商一致才算稳定rescue/harm，其他结果保留但不作强utility监督。
- 002 valid-only统一评价，LLM/human分开，1000次患者cluster bootstrap；第0轮为主，第1轮为重复。每轮仍是192条，不能把重复当独立样本。

完整选择规则、8维特征、六训／六选划分、单一低容量模型和后续停止标准见[事前协议](protocol_001.md)。本轮未执行训练；不能把预案当作完成成果。

## 1. selection-fixable空间与监督

| 项目 | 结果 |
|---|---|
| 有合法单段替换 | {prep['any_swap_eligible']}/192 |
| 稳定baseline错误 | {we}/192 |
| 稳定救回错误并集 | {rc}/{we}，{rc/we:.1%}；{coverage('rescued')}名患者 |
| 仅C48内即可稳定救回 | {g['same_pool_rescued']}条 |
| 仅宽池动作额外救回 | {g['wide_only_rescued']}条 |
| 稳定baseline正确被破坏并集 | {ha}/{co}，{ha/co:.1%}；{coverage('harmed')}名患者 |
| baseline两次标签翻转 | {g['baseline_label_flips']}/192，{g['baseline_label_flips']/192:.1%} |
| 训练六人稳定非零utility配对 | {len(train)}个，覆盖{len({e['subject_id'] for e in train})}名患者 |
| 全12人稳定非零utility配对 | {len(strong)}个（事件，不是独立病例） |

“救回”是固定Judge与原医生标签一致性改善，不等于医学evidence gold；两次重复也不能消除全部随机性。{rc}/{we}是**本次有限动作下稳定错误的已观察救回比例**，不是全体错误可修复率或精确oracle上限。没有passage gold，无法把未救回病例断言为candidate不含有用证据；也不能仅凭一个正确标签证明新增段独立充分。

{table(['作者','稳定错误','稳定rescue','稳定正确','稳定harm'],authorrows)}

{table(['GT类别','稳定错误','稳定rescue','稳定正确','稳定harm'],classrows)}

## 2. 完整队列效果与类别代价

第0轮结果；以下均为固定规则对照，**不是已学习selector的成绩**。

两作者合计，C48／同note替换／跨note替换／wide swap／wide原selection的第0轮正确数为167／161／163／162／165；第1轮为164／162／167／162／163。没有一个固定干预在两轮、两作者上都呈现清楚的正向方向。

{table(['作者','条件','正确数','PA','AC1','MCC'],first)}

与同轮C48配对；rescue/harm为该轮改对／改错数，与上文要求两次稳定的口径不同。区间为第0轮患者bootstrap ΔMCC 95%区间，不对多种动作选出事后“最佳方案”。

{table(['作者','条件','R0改对/改错','R0净增','R1净增','R0 ΔMCC区间'],repeated)}

三类别第0轮TP（正确识别该类别的条数）；分母为同一作者／类别支持数。完整precision／recall／F1、混淆矩阵、PA/AC1/MCC区间及配对差见[机器评价](analysis_001/metrics.json)与[配对评价](analysis_001/paired.json)。

LLM样本中S占91/96，NS仅4条、NA仅1条。即使完全相同的baseline输入，两轮LLM正确数也由93变为88、MCC由0.7171变为0.3001；因此不能把第二轮某个较高MCC当作稳定选择收益。上述两轮结果均保留，不选优。

{table(['作者','GT','支持数','C48 TP','同note TP','跨note TP','wide swap TP','wide原selection TP'],classes)}

## 3. 患者分布与停止依据

{table(['患者','稳定错误','稳定rescue','同池rescue','稳定正确','稳定harm'],patientrows)}

完整各条件、各轮、各作者逐患者正确数见[patients.csv](analysis_001/patients.csv)。稳定结果按病例并集计数，同一病例被两个动作救回也只计一次。

{table(['预设条件','是否满足'],[[names[k],'是' if v else '**否**'] for k,v in g['conditions'].items()])}

不满足门槛后按预案终止；没有训练后再挑结果，没有v2/v3，也没有扩大到新10人或reserved test。

## 4. 对任务六个问题的回答

1. **可修复比例**：有限动作稳定救回{rc}/{we}个稳定错误；同池{g['same_pool_rescued']}，宽池独有{g['wide_only_rescued']}。不能据此推算所有错误中有用候选的总体比例。
2. **医生verdict能否产生可学习监督**：可构造observed rescue/harm弱标签，但本次headroom／监督门槛未全部通过，未证明足以学习可泛化utility。标签是claim正确性变化，不是新passage标注。
3. **patient-disjoint泛化**：未进入训练／模型选择，不能声称泛化成功或训练后失败；六训／六选已预设但未启用。
4. **相对C48变化**：上表完整报告PA、AC1、MCC、正确数、两作者与三类别；没有learned selector成绩。
5. **wide是否只有配合utility才有效**：本轮有W＋原selection实测，utility学习未启动，因此此交互问题未得到验证；013历史失败不能替代本轮因果比较。
6. **剩余10人冻结确认**：未触发，10人继续保留；reserved test未用于本任务。

## 5. 文献定位、成本与审计

[FER](https://arxiv.org/html/2310.11675v2)已有verifier反馈utility学习；[REPLUG](https://aclanthology.org/2024.naacl-long.463/)用冻结LM监督检索；[W-RAG](https://arxiv.org/abs/2408.08444)研究下游QA弱监督检索；[CUE-R预印本](https://arxiv.org/abs/2604.05467)研究counterfactual evidence utility。因此不主张utility-aware evidence selection首创；这次提供的是“只有临床claim verdict、有限GT盲证据替换”条件下的实证筛选结果，尚非已验证新方法。具体关系与版本边界见[相关工作](related_work.md)。

- {s['HTTP_attempts']}次HTTP尝试，{s['unique_requests']}份有效回答，状态计数{s['status_counts']}；全部失败、重试、实际body、回执、usage与预测保留。HTTP200回答不重跑、不选优。
- 累计usage费用估算＋未知预留 **¥{s['used_or_reserved_cny']:.8f}/¥80**，其中未知usage预留¥{s['unknown_reservations_cny']:.8f}；不是平台账单。有效回答input/output tokens为{s['actual_usage']['input_tokens']:,}/{s['actual_usage']['output_tokens']:,}。账号分布{s['accounts']}，成功回答供应商分布{s['providers']}。
- 供应商仅给模型别名，未取得不可变权重版本；保留输出遵守诊断{s['adherence_flagged']}条，不因解释格式偏差修改合法标签。原001–016报告、回执、审计和原始数据保持。
- 这是执行者报告与自查，**尚未独立审计**。离线重放、代码／成果指纹及交审范围见[审计交接](audit_handoff.md)。
'''
    output.parent.mkdir(parents=True,exist_ok=True)
    c.write_json(output.with_name(output.stem+'_sources.json'),dict(source_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in (root/'summary.json',root/'gate.json',root/'metrics.json',root/'paired.json')},renderer_sha256=c.file_hash(c.TASK/'report017.py')))
    output.write_text(text,encoding='utf-8',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);render(p.parse_args().output)
