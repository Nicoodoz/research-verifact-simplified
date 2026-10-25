"""Interpret completed single screen without tuning or additional calls."""
import common094 as c
NOTES={
 'dd6a7f62-eba8-03af-b8d9-0eb43b35df8c':('Q原生伤害、被后处理修回','数值与干预关系命题；V/Q引用同一材料、事实基本相同，仅措辞不同，Q原生从S变NS。U2/PriorG将Q修回S。没有新的错误取证事实可以解释这次伤害，不能排除措辞影响或调用波动。'),
 '1da2eed5-19d1-76f9-ae93-679c847f077d':('原生救回，但最终基线本已正确','影像解释随时间变化的命题。V有两时点合法记录，Q因引用编号错误只收到不可用标记，却同样raw改对。B经PriorG原本已对，V/Q最终无新增救回；不能把Q原生改对归于隔离得到正确事实。'),
 '949cae52-2eaf-26ed-6782-36be766b7a13':('Q−V唯一最终救回：辅助有效性与边界','干预后的数值命题。Q引用了可定位的另一数值；V有一处引用不合法，整记录被标不可用。三臂raw均NS，V被PriorG推为S，Q/B保持NS。该差异有工程可用性混杂，不证明双方合法取证时隔离优于可见。'),
 '4198b49f-b210-dfba-98ab-4f9fa4e6bfad':('新增false-S但不是正确→错误','后续转运状态命题。V/Q均报告不足、记录及最终请求完全相同；原生三臂均NS且都不等于GT=NA，V/Q最终被推为S。总正确数不变也可能增加错误支持。'),
 '5be24fb4-697c-8cf9-1536-ccce660e41e3':('Q−B救回，但V同样且没有非空取证','治疗与状态变化关系命题。V/Q都只给不足记录，使用同一最终请求；两者raw与final均从NA变为GT=NS。这个正向个例支持额外问题/比较提示可影响结果，不支持独立事实读取带来增量。'),
 'f99a6810-e5e3-da78-e44c-97431b34402d':('Q−B伤害，同样发生于V','检查完成情况及原因命题。V/Q都报告不足、同一最终请求；B为GT=NA，V/Q原生与最终均NS。不能用“不足”来推断真实全记录标签，实际程序未硬设NS，但模型仍出现这种伤害。')}
def main():
    c.put(c.OUT/'decision.json',dict(conclusion='停止当前单问题答案隔离原型，不扩大、不升级默认B。',
      reason='自然20条B/V/Q最终均19正确、MCC均0.7935、false-S均0；机制12条B/V/Q为9/8/9正确，Q与B的MCC同为0.6316，但false-S由B的0增至Q的1。Q较V机制净+1只涉及一例V引用无效且B本已判对的病例；没有证明相对B的系统增量或双方有效取证条件下的隔离优势。该停止决定基于收益归因、类别代价和额外成本，不是把小样本区间跨0解释为方向无效。',
      raw_final_interpretation='自然raw B/V/Q为18/19/18：Q相对B救回1真S、伤害1真S，最终均被原PriorG对齐为19正确，无final净增量。机制raw三臂均9正确，但V/Q相对B均救回1 NS、伤害1 NA；这两例V/Q辅助记录都是相同的证据不足。final Q保留这组救回/伤害，另有原先已判错的NA转S，增加false-S；V额外把另一条raw正确NS经PriorG推成S。Q−V唯一final救回是后者，且V引用无效，不能称为两个正常取证输出之间的纯隔离效应。',
      content_interpretation='在读取最终预测前对26对取证记录分类：13对完全相同；5对事实相同而措辞/时间格式不同；2对仅重复引用数量变化；3对有效记录的内容覆盖变化；3对无效记录差异。那3对内容覆盖变化并未带来任何raw或final的跨臂标签改变。Q在一例丢掉V可定位的事实，在另两例提供更具体概括，但缺少QA医生gold，不把概括自动称正确新证据。实际Q−V改判集中于同事实不同措辞的raw伤害，以及引用有效性不同的final变化。',
      next_step='不建议仅增加样本或继续改提示来扩当前版本。若未来另行授权重启，先解决可自动检查的中立问题范围保留，以及双方均可定位引用下的事实差异测量；需保留可见V、正确病例和NA保护，不把取证不足直接转标签。该具体缺口只作交接，本轮不实现新版本、不新增QA标注、不调PriorG。现有结果可作为论文的有限阴性证据：在固定检索证据下，隔离输入能改变少量取证内容，但尚未证明分类收益，额外流程不能仅靠改判数宣称机制成功。'))
    rows={r['id']:r for r in c.lines(c.OUT/'predictions_public.jsonl')};inp={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};ext={(r['id'],r['arm']):r for r in c.lines(c.PRIVATE/'extracted_aligned.jsonl')}
    out=['# 094 代表病例与可核查归因','','以下为全部出现raw或final跨臂标签变化的6条。只公开ID、标签、自报分数和来源SHA；不复制原claim/EHR。分数顺序S/NS/NA，来源的reference_id是该例原C48内编号，不是新增证据。','']
    for pid,(title,note) in NOTES.items():
        r=rows[pid];out+=['## '+title,'',f"ID `{pid}`，患者 `{r['sid']}`，{r['panel']}，GT={r['GT']}。",'',note,'','|臂|raw|U2|PriorG|自报S/NS/NA分数|','|---|---|---|---|---|']
        for arm in ['B','V','Q']:
            z=r['labels'][arm];scores=r['arms'][arm]['scores'];out.append(f"|{arm}|{z['raw']}|{z['U2']}|{z['PriorG']}|{[scores[k] for k in ['Supported','Not Supported','Not Addressed']]}|")
        out+=['',f"原C48 SHA256：`{c.h(inp[pid]['reference'])}`。",'']
        for arm in ['V','Q']:
            e=ext[pid,arm];out.append(f"{arm}取证：{e['record']['status']}；可定位来源："+str(e['citations']))
        out+=['']
    out+=['## 确有取证内容变化、但未改判的3例','','`57d58ad8-24c3-c0e7-c488-6ea193dee45c`：V有事件原文，Q不足；`5dcc5638-024a-f443-f920-ce04707baf3e`：V不足，Q给出照护方向概括；`197fbcad-e09e-f5fa-504e-19df52c6435a`：V不足，Q给出时点位置概括。三例均没有跨臂raw/final标签改变。最后一例引用提及某时点和转出安排，不能仅凭引用存在就认为事件完成状态被正确读出。完整内容检查见content_review.json。','','所有解释是执行者对可见材料的核对，未新增医生GT；同体共享会让13对最终V/Q严格相同，这是部署缓存逻辑，不是重复调用稳定性证据。其余差异未做同体重复，不能排除调用波动。']
    (c.OUT/'case_analysis.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
    print('Decision: stop version; case report written')
if __name__=='__main__':main()
