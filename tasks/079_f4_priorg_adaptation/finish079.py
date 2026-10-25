"""Render079 result and update current docs without modifying historical artifacts."""
import re
import common079 as c
import run079

def write(p,s):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)

def rewrite(path,fn):
    b=path.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n'
    s=b.decode('utf-8-sig').replace('\r\n','\n')
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+fn(s).replace('\n',nl).encode('utf-8'))

def table(rows):
    lines=['| 实验配置 | MCC | PA | Macro-F1 | S召回 | NS召回 | NA召回 | 正确数 | 错误支持数 | 回退 |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in rows:
        vals=' | '.join(f"{m['recall'][k]*100:.2f}%" for k in c.c53.LABELS)
        lines.append(f"| {m['name']} | {m['MCC']:.4f} | {m['PA']*100:.2f}% | {m['macro_F1']*100:.2f}% | {vals} | {m['correct']}/{m['n']} | {m['falseS']} | {m['fallback']} |")
    return '\n'.join(lines)+'\n'

def main():
    run079.verify()
    t=c.read(c.OUT/'tables.json');pairs=c.read(c.OUT/'paired_comparisons.json');changes=c.read(c.OUT/'changes.json')
    model=c.read(c.OUT/'fitted_models.json');cost=c.read(c.OUT/'cost_ledger.json');v=c.read(c.OUT/'verification.json')
    assert v['status']=='PASS'
    idx={x['method']:x for x in t['all352']};first=changes['all352'][0];second=changes['all352'][1];third=changes['all352'][2]
    summary=(f"079固定F4对称PriorG适配完成：114条/14人校准，复用19条F4、新增{cost['new_logical']}条，共同有效{model['common_n']}条分别拟合B/F4两个G；"
             f"352条/22人评价，F4新/旧PriorG正确{idx['F4_newPriorG']['correct']}/{idx['F4_PriorG']['correct']}，MCC {idx['F4_newPriorG']['MCC']:.4f}/{idx['F4_PriorG']['MCC']:.4f}，"
             f"新F4较旧F4净{first['net']:+d}、错误支持{first['delta_falseS']:+d}；较对称B新PriorG净{second['net']:+d}。"
             f"费用估算¥{cost['estimated_cny']:.6f}/20，两个拟合参数先冻结再评价，无搜索。已暴露development；自检PASS，独立审计未执行。")
    b=['# 079：固定F4的对称PriorG适配\n',summary+'\n',
       '## 设计与解释\n',
       'B=无示例T-S thinking-high；F4=同提示加入071固定四例；旧PriorG=053冻结规则；新G=本次同一共同有效校准病例上分别拟合的Supported单参数偏置；新分布仅先验=保持1378条参考比例，分母改为本次共同有效校准样本比例；适配PriorG=新G＋新分布先验。原U2/Gate/StdM/V均来自相同352条历史预测。\n',
       '校准14人与评价22人完全不重叠，双方均排除实际示例所属患者。参考prior仍为原16名校准患者的1108/100/170标签计数（含其中两名实际示例患者，且不含评价患者）。352条仍与历史示例候选池重叠；GT与成绩早已暴露，不称新盲测。历史B/F4回答与新校准调用跨批次，不重复成功回答。\n',
       f"计划校准114条 S/NS/NA=36/42/36；共同有效{model['common_n']}条，实际GT计数{model['calibration_counts']}。两臂拟合样本完全相同；排除病例见[fitted_models.json](fitted_models.json)。本次仅2个最终拟合；沿用052的平均NLL+0.01*g²，范围[-6,6]，未依据352成绩修改。\n",
       '## 参数\n','| 参数 | B | F4 |','|---|---:|---:|',
       f"| 新G | {model['models']['B']['fit']['theta'][0]:.8f} | {model['models']['F4']['fit']['theta'][0]:.8f} |"]
    for k in c.c53.LABELS:b.append(f"| 最终{k}乘数 | {model['models']['B']['effective_PriorG_multipliers'][k]:.6f} | {model['models']['F4']['effective_PriorG_multipliers'][k]:.6f} |")
    b+=['','旧T-S G为+0.13429095，旧最终S/NS/NA乘数约2.739726/0.220795/0.367531。新旧之间还改变了实际校准类别组成，故必须同时看新分布仅先验与B重拟合对照。\n',
        '## 同352条完整比较\n',table(t['all352']),
        '## 主要配对\n','患者级bootstrap1000次，未作多重比较校正；PA单位为百分点。\n',
        '| 基线→候选 | 救回/伤害 | 净正确 | 错误支持变化 | ΔPA [95%区间] | ΔMCC [95%区间] |',
        '|---|---:|---:|---:|---:|---:|']
    for p in pairs['all352']:
        pa=p['metrics']['percent_agreement'];mc=p['metrics']['mcc']
        b.append(f"| {p['base']} → {p['candidate']} | {p['rescue']}/{p['harm']} | {p['net']:+d} | {p['delta_falseS']:+d} | {pa['delta']*100:+.2f} [{pa['ci95'][0]*100:+.2f}, {pa['ci95'][1]*100:+.2f}] | {mc['delta']:+.4f} [{mc['ci95'][0]:+.4f}, {mc['ci95'][1]:+.4f}] |")
    b+=['','## 研究决策\n',c.read(c.OUT/'interpretation.json')['text']+'\n',
        '## 费用与验证\n',
        f"新增{cost['new_api_attempts']}次请求，状态{cost['http_counts']}，新回答核心有效{v['new_core_valid']}；未知预留¥{cost['unknown_reserved_cny']:.6f}。费用按[官方0731北京忙时价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)及usage估算，不是账单核对。既有无效回答保留，评价沿用原078回退；共同核心有效340条单列。\n",
        '公共evaluate/paired_compare；旧352各基线指标精确复现，训练评价患者隔离、拟合有限差分与收敛检查PASS，普通通信恢复/预算/内容不重试四项合成测试PASS（0网络）。未使用reserved、未修改.gitignore、未提交推送，不自动080。\n',
        '[全部分层表](performance_tables.md) · [参数](fitted_models.json) · [病例变化](paired_comparisons.json) · [账本](cost_ledger.json) · [自检](verification.json)\n']
    write(c.OUT/'report.md','\n'.join(b))
    write(c.OUT/'performance_tables.md','# 079各队列完整表\n\n'+'\n'.join('## '+k+'\n\n'+table(ms) for k,ms in t.items()))
    for folder in [c.OUT,c.TASK]:
        link='report.md' if folder==c.OUT else '../../outputs/079_f4_priorg_adaptation/report.md'
        write(folder/'CURRENT_STATUS.md','# 079当前状态\n\n'+summary+'\n\n'+c.read(c.OUT/'interpretation.json')['short']+f'\n\n[报告]({link})\n')
    write(c.OUT/'README.md','# 079结果入口\n\n'+summary+'\n\n[报告](report.md) · [全部性能表](performance_tables.md)\n')
    for name,link in [('AGENTS.md','outputs/079_f4_priorg_adaptation/report.md'),('README.md','outputs/079_f4_priorg_adaptation/report.md'),('docs/PROJECT_STATUS.md','../outputs/079_f4_priorg_adaptation/report.md')]:
        note='**079最新（2026-09-24）：** '+summary+' '+c.read(c.OUT/'interpretation.json')['short']+f' [079报告]({link})\n\n'
        rewrite(c.ROOT/name,lambda s,note=note:s.split('\n',1)[0]+'\n\n'+note+s.split('\n',1)[1].lstrip('\n'))
    for name,note in [('docs/API_POLICY.md',f"079由用户另行交办，按20元任务上限完成固定F4校准，累计估算¥{cost['estimated_cny']:.6f}/20；079与078费用分开登记，不改变078累计¥31.527954/35的历史记录。"),
                      ('docs/RESEARCH_EXECUTION.md','079已由用户明确交办完成固定F4对称PriorG适配；本次明确授权仅拟合两个G，历史“后处理暂冻”不阻止该项已授权工作。'+c.read(c.OUT/'interpretation.json')['short']+' 不自动080。')]:
        rewrite(c.ROOT/name,lambda s,note=note:s.split('\n',1)[0]+'\n\n**079更新：** '+note+'\n\n'+s.split('\n',1)[1].lstrip('\n'))
    checks=0
    for p,h in c.read(c.OUT/'analysis_registration.json')['code_sha256'].items():assert c.sha(c.ROOT/p)==h;checks+=1
    for path in [c.ROOT/'outputs/078_component_ablation/manifest.json',c.ROOT/'outputs/078_component_ablation/f4_extension_001/manifest.json']:
        for p,h in c.read(path)['files'].items():assert c.sha(c.ROOT/p)==h,p;checks+=1
    for p,h in c.read(c.OUT/'freeze.json')['source_sha256'].items():assert c.sha(c.ROOT/p)==h,p;checks+=1
    for path in list(c.OUT.glob('*.md'))+list(c.TASK.glob('*.md')):
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):assert (path.parent/link).exists(),link
    c.put(c.OUT/'closure_checks.json',dict(status='PASS',source_hash_checks=checks,old078_artifacts_unchanged=True,independent_audit='not performed'))
    files=[p for base in [c.TASK,c.OUT] for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest.json']
    c.put(c.OUT/'manifest.json',dict(files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in files},mutable_docs={p:c.sha(c.ROOT/p) for p in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md','docs/RESEARCH_EXECUTION.md']}))
    print(summary+' '+c.read(c.OUT/'interpretation.json')['short'])

if __name__=='__main__':main()
