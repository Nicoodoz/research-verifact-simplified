"""Readable tables and current documentation for the approved078 supplement."""
import re
import common078 as c
OLD=c.OUT
OUT=OLD/'f4_extension_001'

def write(p,s):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)

def table(ms):
    lines=['| 实验配置 | MCC | PA | 正确数 | 错误支持数 | 回退数 |','|---|---:|---:|---:|---:|---:|']
    for m in ms:
        lines.append(f"| {m['name']} | {m['MCC']:.4f} | {m['PA']*100:.2f}% | {m['correct']}/{m['n']} | {m['falseS']} | {m['fallback']} |")
    return '\n'.join(lines)+'\n'

def rewrite(path,fn):
    b=path.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n'
    s=b.decode('utf-8-sig').replace('\r\n','\n')
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+fn(s).replace('\n',nl).encode('utf-8'))

def main():
    t=c.read(OUT/'tables.json');p=c.read(OUT/'paired_comparisons.json');cost=c.read(OUT/'cost_ledger.json');v=c.read(OUT/'verification.json')
    assert v['status']=='PASS'
    def index(key):return {x['method']:x for x in t[key]}
    full=index('all384_descriptive');clean=index('exclude_actual_example_patients352');new=index('new224_no_example_patient')
    def diff(mm,post):return mm['F4_'+post]['correct']-mm['TS_'+post]['correct']
    summary=(f"078固定F4已补齐384条：复用128条、新补256条，新增{cost['new_attempts']}次请求，核心有效{v['new_core_valid']}条；"
             f"补跑估算¥{cost['extension_cny']:.6f}，078累计¥{cost['total078_cny']:.6f}/35。"
             f"排除示例患者后的352条，F4相对无示例raw/U2/PriorG净正确{diff(clean,'raw'):+d}/{diff(clean,'U2'):+d}/{diff(clean,'PriorG'):+d}；"
             f"F4＋PriorG MCC {clean['F4_PriorG']['MCC']:.4f}，无示例{clean['TS_PriorG']['MCC']:.4f}。"
             '完整384含2条示例本身、32条示例同患者病例，仅描述性展示；352仍有示例候选池重叠，原128保持全候选池隔离。未重新拟合PriorG，未改变默认系统。')
    u2pair=next(z for z in p['exclude_actual_example_patients352'] if z['base']=='TS_U2')
    rawpair=next(z for z in p['exclude_actual_example_patients352'] if z['base']=='TS_raw')
    pgpair=next(z for z in p['exclude_actual_example_patients352'] if z['base']=='TS_PriorG')
    findings=(
        '**核心结论：补齐后的F4有更明确的开发阶段正向证据，不能再概括为“加示例无效”。最清楚的增量出现在固定U2下；接旧PriorG后的收益较小，仍未确认稳定升级。**\n\n'
        f"排除实际示例患者的352条：F4 raw净+5、错误支持−2，MCC差95%区间{rawpair['metrics']['mcc']['ci95']}，PA区间下界为0；"
        f"F4＋U2净+9、错误支持+1，PA提升2.56个百分点，95%区间[{u2pair['metrics']['percent_agreement']['ci95'][0]*100:.2f}, {u2pair['metrics']['percent_agreement']['ci95'][1]*100:.2f}]个百分点，"
        f"MCC提升{u2pair['metrics']['mcc']['delta']:.4f}，95%区间[{u2pair['metrics']['mcc']['ci95'][0]:.4f}, {u2pair['metrics']['mcc']['ci95'][1]:.4f}]。"
        '排除所有回退后的340条，U2下仍净+8，PA/MCC区间均高于0，收益并非全由回退产生。\n\n'
        'F4＋PriorG相对无示例＋PriorG净+4、错误支持+2，PA/MCC提升区间仍跨0。新增且非示例患者的224条中，raw/U2/PriorG分别净+2/+5/+2，说明正向结果不只来自复用128条；但这是已暴露开发数据上的扩展，不能称新的独立最终确认。\n\n'
        '这些结果支持“示例收益与后处理存在交互，值得区分评价”，不直接证明“旧PriorG失配是唯一原因”或“重训必定更好”。F4＋U2在352条仍低于无示例＋PriorG的PA/MCC点估计，组件增量与整套系统升级不是一回事。\n')
    body=['# 078 F4补齐报告\n',summary+'\n',findings,
          '## 配置与评价范围\n',
          'B/无示例为C48 → T-S thinking-high；F4在同一提示加入071固定四例。raw取模型原始判断；U2为固定λ=2决策；PriorG沿用原无示例T-S的冻结参数，未做F4适配。U2基线指非thinking评分＋λ2；Gate为患者外Gate A；StdM/V为历史患者外标准校准。原VeriFact使用同ID的官方发布预测。\n',
          '384条同24名开发患者；352条排除两名实际示例患者（72844、97212），共22人；原128条8人继续与整个24人教学候选池隔离。新增256条中224条不属于实际示例患者。全部是已暴露development，352不是全候选池隔离的独立确认，更不是新最终测试。固定示例本身的2条仅用于满足全384覆盖，不计入352结果。\n',
          '旧128回答和所有无示例/作者/后处理基线逐条保留。新旧调用批次不同；只对未成功的通信请求有限恢复，HTTP200核心无效不重发，按原078规则回退已有N-S＋U2，并另列共同核心有效结果。\n']
    for key,title in [('all384_descriptive','完整384条：描述性结果'),('exclude_actual_example_patients352','排除实际示例患者后的352条'),('original_pool_isolated128','原128条：整个候选池隔离'),('new224_no_example_patient','新增224条：排除实际示例患者')]:
        body += ['## '+title+'\n',table(t[key]),'配对结果（救回/伤害是相对同病例无示例，错误支持变化越少越好）：\n']
        for z in p[key][:3]:
            body.append(f"- {z['base']} → {z['candidate']}：救回{z['rescue']}、伤害{z['harm']}、净{z['net']:+d}，错误支持{z['delta_falseS']:+d}。\n")
    body += ['## 解释边界\n',
             '本次直接检验固定F4扩大覆盖后的表现及其与现有后处理的兼容性。不能把冻结PriorG下的表现等同于F4经过单独校准的表现，也不能因这一可能性就认定重新校准一定有效。未选择新示例、未拟合新参数、未使用reserved。原078主报告保留原始结项快照，本补充报告与现行总览优先反映F4覆盖。\n',
             f"## 费用与复核\n\n新增请求状态：{cost['http_counts']}；未知预留¥{cost['unknown_reserved_cny']:.6f}。费用按[官方0731快照北京忙时价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)及usage估算，非账单对账。旧078费用继续累计，用户在‘补齐’回复中确认35元总上限。\n",
             f"自检PASS：原078清单{v['old_manifest_files_unchanged']}个文件指纹不变，所有基线与旧128条F4保持原值；新增核心无效{v['new_core_invalid']}条。独立审计未执行。\n",
             '[完整分层表](performance_tables.md) · [患者bootstrap配对结果](paired_comparisons.json) · [费用账本](cost_ledger.json) · [自检](verification.json) · [冻结](freeze.json)\n']
    write(OUT/'report.md','\n'.join(body))
    write(OUT/'performance_tables.md','# F4补齐全部性能表\n\n'+'\n'.join('## '+key+'\n\n'+table(ms) for key,ms in t.items()))
    write(OUT/'CURRENT_STATUS.md','# F4补齐状态\n\n'+summary+'\n\n[报告](report.md)\n')
    write(OUT/'README.md','# F4补齐结果入口\n\n'+summary+'\n\n[报告](report.md) · [完整表](performance_tables.md)\n')
    for name,link in [('README.md','outputs/078_component_ablation/f4_extension_001/report.md'),('AGENTS.md','outputs/078_component_ablation/f4_extension_001/report.md'),('docs/PROJECT_STATUS.md','../outputs/078_component_ablation/f4_extension_001/report.md')]:
        note='**078 F4补充更新（2026-09-24）：** '+summary+f' [补充报告]({link})\n\n'
        rewrite(c.ROOT/name,lambda s,note=note:s.split('\n',1)[0]+'\n\n'+note+s.split('\n',1)[1].lstrip('\n'))
    policy=f"**078补跑授权更新（2026-09-24）：** 用户确认将078全任务累计上限由30元提高到35元，固定F4已补齐384条；补跑估算¥{cost['extension_cny']:.6f}，含原任务累计¥{cost['total078_cny']:.6f}/35。下方30元与¥21.043860为补跑前历史快照，不改变其他任务默认20元。\n\n"
    rewrite(c.ROOT/'docs/API_POLICY.md',lambda s:s.split('\n',1)[0]+'\n\n'+policy+s.split('\n',1)[1].lstrip('\n'))
    rewrite(c.ROOT/'docs/RESEARCH_EXECUTION.md',lambda s:s.split('\n',1)[0]+'\n\n078固定F4已按用户确认补齐384条，35元累计上限；完整384/排除实际示例患者352/原候选池隔离128分开报告。未做F4校准，不自动启动079。[补充报告](../outputs/078_component_ablation/f4_extension_001/report.md)。\n\n'+s.split('\n',1)[1].lstrip('\n'))
    # Frozen prior078 artifacts remain untouched; current docs have new snapshots here.
    for path,h in c.read(OLD/'manifest.json')['files'].items():assert c.sha(c.ROOT/path)==h,path
    assert c.sha(c.ROOT/'.gitignore')==c.read(c.ROOT/'outputs/076_existing_results_synthesis/closure_checks.json')['gitignore_sha256']
    paths=[x for x in OUT.rglob('*') if x.is_file() and x.name!='manifest.json']
    paths += [c.TASK/n for n in ['prepare_f4_extension.py','register_f4_extension.py','run_f4_extension.py','test_f4_extension_budget.py','analyze_f4_extension.py','render_f4_extension.py']]
    for path in OUT.glob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):assert (path.parent/link).exists(),link
    c.put(OUT/'manifest.json',dict(files={x.relative_to(c.ROOT).as_posix():c.sha(x) for x in paths},mutable_docs={n:c.sha(c.ROOT/n) for n in ['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md','docs/RESEARCH_EXECUTION.md']}))
    print(summary)

if __name__=='__main__':main()
