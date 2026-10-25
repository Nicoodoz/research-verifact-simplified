"""Automatic factual report and execution self-check; not independent audit."""
import json,subprocess,sys
import common032 as c
NAMES={'U0':'原评分U0','U2':'固定lambda=2','SD_A':'031评分Gate A','score':'仅评分三分类纠错','fixed':'NLI固定聚合纠错','attention':'NLI双粒度注意力纠错','attention_single':'仅片段注意力','attention_no_lambda':'注意力去lambda','attention_candidate_only':'注意力仅作用旧候选'}
def main():
    c.block_network();a=c.OUT/'analysis_001';m=c.read(a/'metrics.json');pairs=c.read(a/'paired.json');changes=c.read(a/'changes.json');sel=c.read(c.OUT/'training_001/selections.json');checks={}
    p=c.read(c.OUT/'preparation_001/manifest.json')
    for rel,h in p['sources'].items():checks['source:'+rel]=c.sha(c.ROOT/'outputs'/rel)==h
    train=set(c.read(c.OUT/'inference_001/manifest.json')['training_patients']);test=set(c.read(c.OUT/'inference_001/manifest.json')['confirmation_patients']);checks['patient_disjoint']=not bool(train&test)
    count=0
    for folder in [c.OUT/'training_001/models',c.OUT/'inference_001/models']:
        for path in folder.rglob('model.json'):
            v=c.read(path);checks['model:'+str(path.relative_to(c.OUT))]=set(v['training_patients'])<=train and not bool(set(v['training_patients'])&test) and c.sha(path.parent/'weights.pt')==v['weights_sha256'];count+=1
    checks.update(c.read(a/'baseline_checks.json'));c.require(all(checks.values()),'Self-check failed')
    rows=['# 032：预训练证据关系增强的三分类纠错','', '**执行与自检完成；尚未独立审计。** 本轮只使用已暴露development：28名/2527条训练，12名/1148条确认；reserved40未使用。','', '## 设置','冻结DeBERTa-v3 NLI本地推理；原C48片段及同note已选片段的上下文两个粒度。缓存三类关系和固定32维投影，仅训练小型聚合与残差头。NLI关系不是医生三分类真值。','', '训练内4折按患者隔离，宽度16/32、3固定种子、60轮，修正系数仅从训练折外选择。主选择优先PA不低于U2时最高MCC；可选择零修正，零修正意味着本配置没有训练内增量依据。确认组不参与选择。','', '## 完整确认结果','PA是完整队列判对比例；MCC是三类预测相关性；false-S是真实非Supported却预测Supported。以下不是训练成绩。','', '|方法|正确/1148|PA|MCC|AC1|总false-S|','|---|---:|---:|---:|---:|---:|']
    for name in NAMES:
        v=m['all/'+name];rows.append(f"|{NAMES[name]}|{v['correct']}|{v['PA']:.2%}|{v['MCC']:.4f}|{v['AC1']:.4f}|{v['false_S']}|")
    rows+=['','## 训练内选定配置','|家族|隐藏维|修正系数|训练内PA约束满足|','|---|---:|---:|---|']
    for name,v in sel.items():rows.append(f"|{NAMES[name]}|{v['hidden']}|{v['scale']}|{not v['constraint_failed']}|")
    rows+=['','## 修错与误伤（相对固定lambda=2）','|方法|修对|改错|旧候选之外修对|旧候选之外改错|阻止false-S|新产生false-S|','|---|---:|---:|---:|---:|---:|---:|']
    for name in sel:
        v=changes[name];rows.append(f"|{NAMES[name]}|{v['fixes']}|{v['harms']}|{v['noncandidate_fixes']}|{v['noncandidate_harms']}|{v['prevented_false_S']}|{v['new_false_S']}|")
    rows+=['','## 配对不确定性','患者bootstrap为1000次配对重抽，固定已训练预测，不在每次重抽中重训；多条件探索的辅助区间不构成全部比较的显著性保证。','|注意力方案相对|PA差（百分点）及95%区间|MCC差及95%区间|','|---|---|---|']
    for old in ['U2','SD_A','score','fixed','attention_single','attention_no_lambda','attention_candidate_only']:
        v=pairs['attention__vs__'+old]['metrics'];pa=v['percent_agreement'];mc=v['mcc']
        rows.append(f"|{NAMES[old]}|{100*pa['delta']:+.3f} [{100*pa['ci95'][0]:+.3f},{100*pa['ci95'][1]:+.3f}]|{mc['delta']:+.4f} [{mc['ci95'][0]:+.4f},{mc['ci95'][1]:+.4f}]|")
    rows+=['','## 作者分层','|来源/方法|正确|PA|MCC|false-S|','|---|---:|---:|---:|---:|']
    for key,v in m.items():
        scope,name=key.split('/')
        if scope!='all' and name in ['U2','SD_A','score','fixed','attention']:rows.append(f"|{scope}/{NAMES[name]}|{v['correct']}/{v['n']}|{v['PA']:.2%}|{v['MCC']:.4f}|{v['false_S']}|")
    base=m['all/U2'];new=m['all/attention'];dp=new['PA']-base['PA'];dm=new['MCC']-base['MCC'];df=new['false_S']-base['false_S']
    rows+=['','## 当前结论',f'预先选择的注意力主方案相对U2：PA {100*dp:+.3f}个百分点，MCC {dm:+.4f}，false-S {df:+d}。这是固定工作点实际结果，不从确认曲线选新阈值。', '点估计同时改善，仍须结合上表区间和简单对照判断。' if dp>=0 and dm>0 else '没有在确认点估计上同时提高PA与MCC；不得因个别辅助配置较高而改选最终winner。', '零修正配置不能作为证据模块有效的证明。候选限制消融只改变应用范围，未重新训练；去lambda与单粒度分别在训练侧独立选配置。','', '## 成本、环境与限制','新增收费API为0；公开模型下载后完全本地推理。原claim、C48与031划分未改，没有新增医学标注。预训练模型可能不适应临床文本，当前标签仍依据原医生判断，不按NLI关系重标。','GPU环境离线clone因缺失历史conda包失败。实际采用.local_models/032/venv任务专用虚拟环境，启用system-site-packages读取已有research GPU库；未修改主环境、029环境或research库。依赖版本已记录。','NLI计算批量先从4改16；长文本尾段吞吐下降后恢复为4，已有52520组缓存保留，只补算剩余输入。批量变更是计算调整，未按分类成绩更改模型或输入；不声称不同批量逐位数值等价。权重及大缓存位于已忽略的.local_models/032。','',f'执行者检查{len(checks)}项通过、保存模型{count}套；未进行独立审计，不自动033或reserved测试，不自动提交推送。']
    c.text(c.OUT/'report.md','\n'.join(rows)+'\n');close=c.OUT/'closeout_001';close.mkdir(exist_ok=True);c.put(close/'checks.json',dict(created_utc=c.now(),passed=all(checks.values()),checks=checks,model_count=count,independent_audit=False))
    c.text(c.OUT/'RUN_STATUS.md','# 032运行状态\n\n执行、评价与自检完成；待独立审计。\n\n主报告：report.md；正式结果：analysis_001；模型：inference_001/models。\n')
    c.state('completed',state='completed',API_calls=0,independent_audit=False);print('Report and self-check complete',flush=True)
if __name__=='__main__':main()
