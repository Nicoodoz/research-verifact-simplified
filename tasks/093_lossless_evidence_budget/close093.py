"""Record the single completed experiment's interpretation; no new requests."""
import common093 as c
def main():
    c.put(c.OUT/'decision.json',dict(
      conclusion='停止本版本，不扩大实测、不升级默认B。',
      reason='自然面板共同核心有效88条，B/F/A最终正确76/77/76，A较B净0、MCC 0.6250→0.6130、false-S 1→2；压力30条正确17/16/18，A较B净+1、false-S 10→9。压力唯一最终救回集中于一名患者，不能抵消自然面板未改善及新增错误支持而据此扩大。操作确实保留原包并加入原文，但可用空间并不保证新增片段包含命题缺口；本轮未证明综合质量优势。',
      raw_final_interpretation='自然90条raw B/F/A均70正确，但标签并非逐例相同；最终88条A与B没有救回或伤害，增加的false-S来自一条原本已判错的NA变为S。F仅有的一条真S最终救回在A中消失。压力raw B/F/A为20/20/21：A相对B的NS原生救回在F中已出现，随后被U2和PriorG翻回S，不能归功于新增证据；最终唯一NS救回是另一条三臂raw均为NS的病例，只在A的分数组合下保持NS。A较F压力净+2包括恢复F误伤的NA和这条边界救回，均属同一患者。补证、呈现和调用波动尚不能作确定因果拆分；没有原生正向变化稳定转化为新增信息收益的证据。',
      next_step='保留无损来源编码与预算核查实现作为工程成果，停止这版“按旧rerank能放就加”的分类候选。若未来另行授权，重启前最低缺口是证明新增片段含有原包欠缺、可定位到命题关系的内容，并给出与046/048已测要求扩检不同的操作；不能只加样本或修改折叠阈值。本轮不实现该修正，也不按诊断重调PriorG。'))
    notes={
      '7d4e428a-99fb-38d3-e3d4-454e7db89b57':('最终救回（A−B）','命题涉及干预后的状态。新增段主要确认操作和装置，原包已有相关操作及状态记录；不能认定补到了此前缺失的决定性反证。三臂原生均NS，变化可直接定位为分数组合跨最终边界。'),
      '86878c0d-fa7f-294d-1fc7-2d410f7d808f':('原生救回被抵消','命题涉及转入事件及诊断对应。新增段为检查元信息和孤立标题，未直接证明事件关系。F已经产生与A相同的NS原生改判，因此不能把该救回归因于新增原文；两者最终都被翻回S。'),
      '0fb50da1-8a08-209b-c0f1-21034ed049ed':('错误支持增加，但非正确→错误伤害','命题涉及转运地点。新增段主要为入院背景及片段尾部，不直接补足目的地点。raw三臂均NS、GT为NA；F/A最后变S。原来已错，PA没有下降，但false-S风险增加。'),
      '8958e24b-66e4-1224-4f8d-dadc0562343a':('F伤害及A恢复','命题涉及特定装置的撤除。原包存在装置仍在位的时点描述，新增段涉及另一类操作，不能把关键词相似当作同一事件。B/A均NA、F为NS；A相对F救回，但相对B没有新增收益。'),
      '891d2edd-bab1-093d-b01b-45537423988a':('A相对F伤害真S','命题含发现者与装置位置关系。新增段含极短碎片和操作摘要，不直接补足发现者关系。三臂raw都错；F经PriorG改对，A未保持。不能把F的边界救回解释为已经学会正确关系。')}
    rows={r['id']:r for r in c.lines(c.OUT/'predictions_public.jsonl')};ops={r['id']:r for r in c.lines(c.OUT/'pool_operations.jsonl')}
    out=['# 093 代表病例与机制界限','','以下覆盖全部发生raw或final跨臂标签变化的病例。仅发布抽象关系、ID、分数与来源指纹，不复制临床原文；S/NS/NA为固定原标签，分数顺序S/NS/NA。没有新增医生标注，也不依据模型reason断言内部机制。','']
    for pid,(title,note) in notes.items():
        r=rows[pid];o=ops[pid];out+=['## '+title,'',f"ID `{pid}`；患者 `{r['sid']}`；{r['panel']}；GT={r['GT']}。",'',note,'','|臂|raw|U2|PriorG|自报分数S/NS/NA|','|---|---|---|---|---|']
        for a in ['B','F','A']:
            p=r['labels'][a];scores=r['arms'][a]['scores'];out.append(f"|{a}|{p['raw']}|{p['U2']}|{p['PriorG']}|{[scores[k] for k in ['Supported','Not Supported','Not Addressed']]}|")
        out+=['','新增来源ID：'+', '.join('`'+x+'`' for x in o['added_ids'])+'。对应note/offset/text SHA见pool_operations.jsonl。','']
    out+=['## 解释限制','','A−B自然0救回/0伤害，压力1救回/0伤害，不虚构不存在的A−B伤害病例；上表另列A−F真S伤害和F−B NA伤害。新增正文未见关键关系增量、部分只是标题或短尾片，是本次原文核查发现，不代表所有198个可补证病例都如此。无同体重复，不能排除调用波动；程序无损也没有证明模型语义无损。','']
    (c.OUT/'case_analysis.md').write_text('\n'.join(out),encoding='utf-8')
if __name__=='__main__':main()
