"""Update current navigation after101 is complete; preserve UTF8 BOM and existing newline style."""
import common101 as c
def edit(rel,fn):
 p=c.ROOT/rel;raw=p.read_bytes();text=raw.decode('utf-8');nl='\r\n' if b'\r\n' in raw else '\n';normalized=text.replace('\r\n','\n');new=fn(normalized);p.write_bytes(new.replace('\n',nl).encode('utf-8'))
def replace_line_start(text,prefix,replacement):
 lines=text.split('\n');found=[i for i,s in enumerate(lines) if s.startswith(prefix)];assert len(found)==1,(prefix,found);lines[found[0]]=replacement;return '\n'.join(lines)
def main():
 a=c.read(c.OUT/'analysis.json');cost=c.read(c.OUT/'cost_ledger.json');check=c.read(c.OUT/'selfcheck.json');assert check['status']=='PASS'
 t=a['tables']['natural'];p=a['paired']['natural'];plain=p['nsna_plain__vs__verifact_ref'];review=p['nsna_review__vs__verifact_ref'];extra=p['nsna_review__vs__nsna_plain'];decision=a['decision']
 overview=f"101 NS/NA定向复核已结项：确认600自然＋100压力、282触发双臂、24条双臂重复。自然共同{t['verifact_ref']['n']}条，verifact_ref/nsna_plain/nsna_review正确{t['verifact_ref']['correct']}/{t['nsna_plain']['correct']}/{t['nsna_review']['correct']}，MCC {t['verifact_ref']['mcc']:.4f}/{t['nsna_plain']['mcc']:.4f}/{t['nsna_review']['mcc']:.4f}；false-S均{t['verifact_ref']['false_S']}，Supported集合逐条不变。plain：{decision['nsna_plain']['status']}；review：{decision['nsna_review']['status']}；对应检查实际增量门槛={decision['review_increment']['practical_extra']}。新增费用及预留¥{cost['used_or_reserved_cny']:.6f}/30，默认不变。"
 edit('AGENTS.md',lambda s:replace_line_start(s,'- 098—100已结项；','- 101已结项；NS/NA定向复核的正式结果和停止决定见PROJECT_STATUS及101报告。098—100原结论保留，原始GT、默认系统和099选型未改变；新实验仍需明确授权。'))
 def status(s):
  s=replace_line_start(s,'# 项目现状','# 项目现状（2026-10-27，研究完成至101）')
  s=replace_line_start(s,'098已完整收尾：',overview+'[101报告](../outputs/101_nsna_review/report.md) · [病例解释](../outputs/101_nsna_review/case_analysis.md)。098和100均已完成、原版本停止；[098报告](../outputs/098_p90_native_confirmation/report_display.md) · [100报告](../outputs/100_preregistered_followup/report_display.md)。')
  marker='|097原生Judge/源文门槛|';row=f"|101 NS/NA定向复核|600自然＋100压力、282触发、24双臂重复；同S集合|plain净{plain['net']:+d}、review净{review['net']:+d}；review−plain净{extra['net']:+d}；详见正式报告，默认不变|\n"
  return s.replace(marker,row+marker,1)
 edit('docs/PROJECT_STATUS.md',status)
 def readme(s):
  s=replace_line_start(s,'临床文本与患者EHR的一致性核验研究。','临床文本与患者EHR的一致性核验研究。101 NS/NA定向复核已结项，默认不变。[101正式报告](outputs/101_nsna_review/report.md) · [类别及病例分析](outputs/101_nsna_review/case_analysis.md)。')
  s=replace_line_start(s,'最新同模型患者隔离确认见',overview+'[101完整结果](outputs/101_nsna_review/report.md)。下面097表保留历史强对照背景，共同158条：')
  return s
 edit('README.md',readme)
 def index(s):
  s=replace_line_start(s,'# 全部任务与当前入口','# 全部任务与当前入口（研究完成至101；2026-10-27）')
  marker='|100_preregistered_followup|';row=f"|101_nsna_review|[正式报告](../outputs/101_nsna_review/report.md) · [病例](../outputs/101_nsna_review/case_analysis.md)|[执行者自检](../outputs/101_nsna_review/selfcheck.json)，独立审计未执行|plain：{decision['nsna_plain']['status']}；review：{decision['nsna_review']['status']}；默认不变，不自动新实验|\n"
  return s.replace(marker,row+marker,1)
 edit('docs/TASK_INDEX.md',index)
 edit('docs/RESEARCH_EXECUTION.md',lambda s:replace_line_start(s,'当前097已完成，','当前研究完成至101，默认无示例B＋Frozen PriorG不变。新研究须用户明确交办，本文件不是自动启动、重复训练、云部署或下一任务的授权。[最新状态](PROJECT_STATUS.md) · [任务索引](TASK_INDEX.md)。'))
 edit('docs/API_POLICY.md',lambda s:replace_line_start(s,'研究完成至097。','研究完成至101。本页只规定新任务的费用与服务边界，不授权在线测试或新实验。101专项30元及实际费用见正式报告；其他任务费用查各自正式报告，历史额度不结转。'))
 print('Current navigation updated, old reports and frozen hashes unchanged')
if __name__=='__main__':main()
