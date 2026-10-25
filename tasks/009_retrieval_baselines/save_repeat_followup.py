"""Preserve the sole preplanned confirmation repeat flip for complete reading."""
import study009 as s


if __name__=='__main__':
    folder=s.OUT/'confirmation_001'
    repeat=next(x for x in s.read_json(folder/'analysis_001/repeat_diagnostics.json') if x['changed'])
    item=next(x for x in s.pilot.jsonl(folder/'judge_preparation/inputs.jsonl') if x['case_id']==repeat['case_id'])
    values={r['request_id']:r for r in s.pilot.jsonl(folder/'analysis_001/normalized_responses.jsonl')}
    responses=[values[repeat[k]] for k in ('canonical_request_id','request_id')]
    text=['# N119：预设同输入重复的唯一标签翻转',item['text'],
        '执行者观察：完整body相同，原NA、重复NS。两份解释均指出只有吸入/雾化治疗，没有吸入器教学记录，差别集中在“部分相关但缺特定行为”落入哪一类。不是新证据引起，也不证明内部机制。原canonical答案不变，不纳入方法增益；此额外阅读不属于35例分层案例集。',
        '## 完整reference',item['retrieval']['A48']['reference']]
    for label,result in zip(('原答案','重复诊断'),responses):
        text.extend(['## '+label,'```json\n'+result['output_text']+'\n```'])
    out=folder/'repeat_followup_001'
    out.mkdir(exist_ok=False)
    (out/'N119.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')
    s.pilot.write_json(out/'binding.json',repeat)
    s.seal(out,[folder/'analysis_001/manifest.json',folder/'judge_preparation/manifest.json'],[s.TASK/'save_repeat_followup.py'])
    print('N119 full request and both outputs recorded without changing predictions')
