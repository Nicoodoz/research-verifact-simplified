"""Publish abstract issue descriptions and private pointers, never clinical text."""
import common104 as c

CASES={
4:('剂量与药物绑定','核对的是同一药物的剂量；另一药物的相同数字不能补足目标用药。'),
10:('治疗反应与时间绑定','较晚记录的数值不能倒接成较早某次治疗的直接反应。'),
19:('时间相关与因果机制','事件发生在操作之后，不自动证明命题提出的具体机制；也不能编造另一原因作反证。'),
28:('客观体征与主观报告','皮肤查体和外用处理已涉及相关部位，但不能直接补成患者主诉了特定症状；须写清部分支持的边界。'),
52:('历史治疗期与后续状态','后续住院症状不等于此前治疗留置期的疗效，NA理由必须说明缺失的是哪个时间段的反应。'),
112:('不同设备不可互换','教师理由混用了临时输注导管与另一植入通路；最终依据回到实际目标通路的后续使用记录。'),
153:('治疗—结局关系','检查改善和清理分泌物不能直接证明补液反应；须引用原文真正连在一起的治疗与结局。'),
180:('去标识化后的对象不明','核心检查对象被遮蔽时，不能任选一项正常结果来解释泛化命题；保持未解决。'),
185:('事件已涉及与特定因果未涉及','同一事件与处置已记录，不代表某个特定病因也被涉及；独立判断可在NS/NA边界分歧，不据此认定原GT错误。'),
259:('相关处置不等于特定事件','存在导尿和低尿量，不自动说明发生排空障碍；首审将其列作原GT解释缺口待核。'),
264:('初始结局缺少纵向对应','某日仍异常和其他器官改善，不能替代目标指标最初已纠正的过程；需要相应趋势材料核查。'),
267:('照护意向与设备决策','限制侵入治疗或询问照护安排，不自动等于已决定撤除某一具体设备。'),
}


def main():
    joined=c.lines(c.PRIVATE/'review_joined.jsonl');rows={r['review_index']:(line,r) for line,r in enumerate(joined,1)}
    provenance={r['id']:r for r in c.lines(c.OUT/'teacher_provenance.jsonl')}
    public=[];table=[]
    for index,(kind,note) in CASES.items():
        line,r=rows[index]
        pointers=[]
        for quote in r['mechanical']['quote_spans']:
            pointers.append(dict(quote_sha256=quote['quote_sha256'],occurrences=[{k:o[k] for k in ('start','end')} for o in quote['occurrences']]))
        item=dict(review_index=index,id=r['id'],GT=r['GT'],independent_verdict=r['independent_verdict'],final_status=r['final_status'],
                  issue_type=kind,reference_sha256=r['source_reference_sha256'],
                  private_ledger='.local_models/104_supervision_evidence/review_joined.jsonl',private_line=line,
                  quotation_positions=pointers,teacher_action=provenance.get(r['id'],{}).get('action'))
        public.append(item)
        table.append(f"|{index} / `{r['id']}`|{kind}|{note}|{r['final_status']}|")
    c.putl(c.OUT/'case_pointers.jsonl',public)
    body='''# 104：具体发现与位置导航

下面是已实际审查条目的抽象问题描述，不是新医学标签。原claim、完整reference、短理由、原GT和精确引用均在私有台账；公开仅给ID与位置。`reference_gap`是当前输入不能可靠解释原GT的待核状态，不证明医生错标；`unresolved`不强行归因。

|审查号 / proposition ID|关系问题|发现与处理|最终状态|
|---|---|---|---|
'''+ '\n'.join(table)+'''

引用字符offset、quote SHA、private JSONL行号见[case_pointers](case_pointers.jsonl)。offset基于原始reference的Python字符索引，不是token或UTF-8字节；重复原文保留全部位置。显示源单元编号不能冒充未发布的原note ID。

这些例证解释数据处理决策，不是103错误病例回填，也不是证明短理由训练有效。尤其“没找到某事实”与“同一事件得到部分支持”的边界仍需按具体对象、时点和关系逐条处理，不能写成一套新的关键词分类器。
'''
    (c.OUT/'case_findings.md').write_bytes(body.encode('utf-8'))
    print(c.canonical(dict(case_pointers=len(public),clinical_text_published=False)))


if __name__=='__main__':main()
