"""Close080 with selected result and all predeclared tradeoffs, preserving history."""
import math,re
from collections import Counter
import common080 as c

def write(p,s):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
def rewrite(path,fn):
    b=path.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n'
    s=b.decode('utf-8-sig').replace('\r\n','\n')
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+fn(s).replace('\n',nl).encode('utf-8'))
def table(rows):
    s=['| 配置 | MCC | PA | Macro-F1 | S召回 | NS召回 | NA召回 | 正确数 | 错误支持 | 回退 |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for x in rows:
        rr=' | '.join(f"{x['recall'][k]*100:.2f}%" for k in c.LABELS)
        s.append(f"| {x['name']} | {x['MCC']:.4f} | {x['PA']*100:.2f}% | {x['macro_F1']*100:.2f}% | {rr} | {x['correct']}/{x['n']} | {x['falseS']} | {x['fallback']} |")
    return '\n'.join(s)+'\n'

def main():
    t=c.read(c.OUT/'tables.json');idx={x['method']:x for x in t['all352']};models=c.read(c.OUT/'models_frozen.json')
    sel=c.read(c.OUT/'selection.json');diag=c.read(c.OUT/'transfer_diagnosis.json');pairs=c.read(c.OUT/'paired_comparisons.json')
    assert c.read(c.OUT/'verification.json')['status']=='PASS'
    summary=('080最终分类目标适配完成，0 API、0元。112条/14人校准留一验证为F4选WMCC1（直接优化加权MCC、只调S）；'
             '352条/22人上正确291，MCC0.5576，较旧F4的298/0.5771净−7，错误支持12→10。'
             '预设WNLL1/2候选均304正确、MCC约0.5876/0.5878，但错误支持17、NS召回24%，且未被校准选择。'
             '有提高PA/MCC的风险取舍候选，未实现可靠的跨患者适配；不改默认、不追加本轮搜索、不自动081。自检PASS，独立审计未执行。')
    interpretation=(
        '**本次得到一个PA/MCC点估计更高的开发候选，但事前校准选择流程未能选中它；没有得到可靠的整体升级。**\n\n'
        '最终输出加权NLL已经修正079“先在原校准分布优化G，再追加prior”的目标错位。WNLL1只调S、WNLL2同时调S/NS，均比旧F4多对6条、PA+1.70个百分点、MCC约+0.0105/+0.0108；代价是错误支持+5、NS召回36%→24%、Macro-F1约64.20%→63.27%。其PA差区间[0,+3.98]个百分点，MCC差区间跨0。它们是预设候选的真实观察，不能说全部适配都无效；但不能因看见352成绩更好就回写为校准选出的主方案。\n\n'
        '校准留一选中的WMCC1：OOF加权MCC从BASE的0.5350到0.5749；最终352条反而0.5771→0.5576，净少对7条，PA差95%区间[−3.41,−0.28]个百分点，MCC区间跨0。错误支持少2条，NS召回36%→44%，S召回90.49%→87.32%，NA不变。共同核心有效340条仍净−7，human/llm分别净−4/−3，结论不靠回退或单一作者组。\n\n'
        '对称无示例B选择WNLL1：正确294→299，但MCC0.5672→0.5501、错误支持10→18、NS召回44%→20%，同样不是全面升级。\n\n'
        '**校准到评价的关键差异：** 全112条上拟合的F4-WMCC1在校准集改变10条，GT为6条NS和4条NA，没有真实S；应用352条后改变11条，GT却为9条S和2条NS。训练时看起来没有S损失的边界移动，在另一组患者上伤害了9条真实S。校准14折中13折都选S偏置−ln2，仍没迁移成功；不能只用“折内参数稳定”证明泛化。\n\n'
        '这表明分数接近决策边界的病例组成没有被当前校准样本可靠代表。总体类别比例加权不能保证纠正这种类内分数差异；有限样本与真实患者差异各贡献多少，本实验不能分开确定。现在已有直接MCC与最终输出NLL两种目标的对照，不宜继续用同一112条反复换目标和偏置范围追逐352成绩。\n\n'
        '建议保留F4＋旧PriorG的现有结果，以及WNLL1作为“更高PA/MCC、更多错误支持”的开发取舍点；不宣布新默认。若未来继续，需要能提供额外泛化信息的校准材料或独立确认，而不是在352条上选最好参数。本任务不自动执行后续。')
    mainmethods=['Original','TS_PriorG','B_selected080','F4_PriorG','F4_newPriorG','F4_WNLL1','F4_WNLL2','F4_WMCC1','F4_WMCC2']
    body=['# 080：面向最终分类的F4适配\n',summary+'\n',
          '## 本次具体改变\n',
          '固定模型、提示、示例、证据与原生分数，全部离线。基础映射为原始log分数＋log(1378条参考比例/112条校准比例)。WNLL1/2直接在最终映射后优化目标分布加权NLL；WMCC1/2直接优化加权MCC。1/2表示只调S或同时调S/NS，NA固定。另有BASE零偏置。正则、范围、网格、选择标准均事前冻结。\n',
          '14名校准患者每次留一人；该患者也从该折的参考先验1378条来源中排除。B/F4用相同112条、相同配方集合，分别按OOF加权MCC选择；OOF用于选方法，不能当成无偏最终确认。352条评价患者与校准/先验来源患者均不重叠，但已经暴露且与历史教学候选池有重叠，属于development。既有核心无效输出沿用078回退，不生成新回答。\n',
          '## 同352条主要比较\n',table([idx[k] for k in mainmethods]),
          'WNLL1/2的成绩是事前规定候选的开发观察；F4_selected080明确绑定WMCC1，不能用WNLL的分数替代其主结果。\n',
          '## 校准患者留一选择\n','| 模型 | 配方 | 加权MCC | 加权PA | 加权Macro-F1 | 被选中 |','|---|---|---:|---:|---:|---|']
    for arm,s in sel.items():
        for x in s['OOF']:body.append(f"| {arm} | {x['recipe']} | {x['MCC']:.4f} | {x['PA']*100:.2f}% | {x['macro_F1']*100:.2f}% | {'是' if x['recipe']==s['chosen'] else '否'} |")
    body+=['','这些加权校准分数模拟参考类别比例，不是352条实测分数，不与主表直接相减。\n',
           '## 研究结论与机制\n',interpretation+'\n',
           '## 参数与求解记录\n',
           '最终NLL1偏置B/F4为+0.547967/+0.359086；F4-NLL2为S−0.018492、NS−0.804753。F4-MCC1为S−ln2；F4-MCC2为S−ln4、NS−ln2。参数全部来自校准患者。直接MCC每折仅固定5/25组，未根据评价扩展范围。\n',
           '最终保存120个参数模型（60个NLL优化、60个MCC网格选择，含两模型的14折与全量拟合），另有BASE参照。初次计算在F4一折L-BFGS-B数值收敛异常时中断，未写最终模型、未读本任务评价成绩；保留原代码与数值修订记录。重算相同问题，异常时改用SLSQP，所有最终NLL模型通过有限差分/投影梯度与目标下降检查；不是增加方法候选。\n',
           '## 交付与边界\n',
           '0新增API/0元，不使用reserved、不改.gitignore、不提交推送。采用公共评价与1000次患者bootstrap；区间未经多重比较校正。自检通过，独立审计未执行。\n',
           '[所有配置与分层表](performance_tables.md) · [逐类P/R/F1](class_metrics.md) · [冻结模型](models_frozen.json) · [可复用映射参数](decision_mappings.json) · [主要配对](paired_comparisons.json) · [迁移诊断](transfer_diagnosis.json) · [协议](../../tasks/080_final_decision_adaptation/README.md)\n']
    write(c.OUT/'report.md','\n'.join(body))
    write(c.OUT/'performance_tables.md','# 080全部配置与分层\n\n'+'\n'.join('## '+k+'\n\n'+table(v) for k,v in t.items()))
    cl=['# 同352条逐类精确率/召回率/F1\n','各格依次为P/R/F1，单位%。\n','| 配置 | S | NS | NA |','|---|---:|---:|---:|']
    for x in t['all352']:
        vals=[' / '.join(f"{(x['per_class'][k][m] or 0)*100:.2f}" for m in ['precision','recall','f1']) for k in c.LABELS]
        cl.append('| '+x['name']+' | '+' | '.join(vals)+' |')
    write(c.OUT/'class_metrics.md','\n'.join(cl)+'\n')
    mappings={}
    for arm,mm in models['full_models'].items():
        mappings[arm]={r:dict(multipliers={k:math.exp(m['anchor_log_offsets'][i]+(m['delta']+[0.])[i]) for i,k in enumerate(c.LABELS)},selected_by_calibration=r==sel[arm]['chosen']) for r,m in mm.items()}
    c.put(c.OUT/'decision_mappings.json',dict(score_floor=1e-6,input='label_scores / 100',decision='multiply floored scores by fixed class multipliers, argmax; tie NS then NA then S',mappings=mappings,
        default_system_changed=False,caution='Final-score transformations; do not assume normalized values are calibrated probabilities.'))
    c.put(c.OUT/'interpretation.json',dict(summary=summary,text=interpretation))
    for folder in [c.OUT,c.TASK]:
        link='report.md' if folder==c.OUT else '../../outputs/080_final_decision_adaptation/report.md'
        write(folder/'CURRENT_STATUS.md','# 080当前状态\n\n'+summary+f'\n\n[报告]({link})\n')
    write(c.OUT/'README.md','# 080结果入口\n\n'+summary+'\n\n[报告](report.md) · [全部表](performance_tables.md)\n')
    for name,link in [('AGENTS.md','outputs/080_final_decision_adaptation/report.md'),('README.md','outputs/080_final_decision_adaptation/report.md'),('docs/PROJECT_STATUS.md','../outputs/080_final_decision_adaptation/report.md')]:
        note='**080最新（2026-09-24）：** '+summary+f' [080报告]({link})\n\n'
        rewrite(c.ROOT/name,lambda s,note=note:s.split('\n',1)[0]+'\n\n'+note+s.split('\n',1)[1].lstrip('\n'))
    for name,note in [('docs/API_POLICY.md','080由用户交办完成离线最终决策适配，新增API0、费用0元；079/078历史账目不变。'),
                      ('docs/RESEARCH_EXECUTION.md',summary)]:
        rewrite(c.ROOT/name,lambda s,note=note:s.split('\n',1)[0]+'\n\n**080更新：** '+note+'\n\n'+s.split('\n',1)[1].lstrip('\n'))
    checks=0
    for p,h in c.read(c.OUT/'freeze.json')['source_sha256'].items():assert c.sha(c.ROOT/p)==h,p;checks+=1
    for p,h in c.read(c.OUT/'numerical_amendment.json')['code_sha256'].items():assert c.sha(c.ROOT/p)==h,p;checks+=1
    for p,h in c.read(c.ROOT/'outputs/079_f4_priorg_adaptation/manifest.json')['files'].items():assert c.sha(c.ROOT/p)==h,p;checks+=1
    assert c.sha(c.ROOT/'.gitignore')==c.read(c.OUT/'freeze.json')['gitignore_sha256']
    folds=c.read(c.OUT/'fold_models.json');assert len(folds)==140
    train=c.lines(c.OUT/'calibration.jsonl');pr=c.lines(c.OUT/'reference_prior_rows.jsonl')
    for f in folds:
        sid=f['heldout_patient'];m=f['model'];assert sid not in m['training_patients']
        assert set(m['training_ids'])=={x['id'] for x in train if x['sid']!=sid}
        assert m['reference_counts']==dict(Counter(x['GT'] for x in pr if x['sid']!=sid));checks+=3
    assert len(c.lines(c.OUT/'oof_predictions.jsonl'))==112*5*2
    for path in list(c.OUT.glob('*.md'))+list(c.TASK.glob('*.md')):
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):assert (path.parent/link).exists(),link
    c.put(c.OUT/'closure_checks.json',dict(status='PASS',source_and_fold_checks=checks,old079_artifacts_unchanged=True,selected_recipe_unchanged_after_evaluation=True,
        numerical_fallbacks=len(diag['solver_fallbacks']),new_API_calls=0,cost_cny=0,independent_audit='not performed'))
    files=[p for base in [c.TASK,c.OUT] for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest.json']
    c.put(c.OUT/'manifest.json',dict(files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in files},mutable_docs={p:c.sha(c.ROOT/p) for p in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md','docs/RESEARCH_EXECUTION.md']}))
    print(summary)

if __name__=='__main__':main()
