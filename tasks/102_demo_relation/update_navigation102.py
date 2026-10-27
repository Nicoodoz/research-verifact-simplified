"""Current navigation only; preserve previous reports and file encoding/newlines."""
import common102 as c
def edit(rel,fn):
 p=c.ROOT/rel;raw=p.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n';text=raw.decode('utf-8').replace('\r\n','\n');p.write_bytes(fn(text).replace('\n',nl).encode('utf-8'))
def line(text,prefix,new):
 rows=text.split('\n');ix=[i for i,r in enumerate(rows) if r.startswith(prefix)];assert len(ix)==1,(prefix,ix);rows[ix[0]]=new;return '\n'.join(rows)
def main():
 complete=c.read(c.OUT/'complete.json');assert complete['paid_calls']==0
 summary='102已完成零费用构造与核查，在付费分类前停止。23条完整历史教学例、13教师患者与098的40评价患者隔离；485/500选例不同，reference特征消融改变426条，最大输入token差2.06%。完整500三臂＋24重复去重后1556请求，预设保守闲时预算¥35.364127/35，缺口¥0.364127；原文抽查另发现对象/事件/否定作用域绑定不足。新增API0次/0元，没有分类阴性结论，默认不变。'
 edit('AGENTS.md',lambda s:line(s,'- 101已结项；','- 102完成零费用可行性核查，因预算计划未满足且关系绑定仍有局限，付费分类前停止；不是分类阴性结果。101及098—100原结论保留，原始GT、默认系统和099选型未变；新研究仍须明确授权。'))
 def status(s):
  s=line(s,'# 项目现状','# 项目现状（2026-10-27，102付费前停止，正式分类完成至101）')
  s=line(s,'101 NS/NA定向复核已结项：',summary+'[102报告](../outputs/102_demo_relation/report.md) · [原文关系核查](../outputs/102_demo_relation/method_review.md)。101两种NS/NA复核失败停止，历史默认保留；[101报告](../outputs/101_nsna_review/report.md)。')
  marker='|101 NS/NA定向复核|'
  return s.replace(marker,'|102动态关系选例|完整500三臂＋24重复输入已构造，0 API；预算门槛未过|自动构造检查通过不等于关系语义正确；未产生分类指标，付费前停止|\n'+marker,1)
 edit('docs/PROJECT_STATUS.md',status)
 def readme(s):
  s=line(s,'临床文本与患者EHR的一致性核验研究。','临床文本与患者EHR的一致性核验研究。102已完成零费用可行性核查并在付费分类前停止；不是分类效果阴性。[102报告](outputs/102_demo_relation/report.md) · [101正式分类报告](outputs/101_nsna_review/report.md)。默认不变。')
  return s
 edit('README.md',readme)
 def index(s):
  s=line(s,'# 全部任务与当前入口','# 全部任务与当前入口（102付费前停止，正式分类完成至101；2026-10-27）')
  return s.replace('|101_nsna_review|','|102_demo_relation|[报告](../outputs/102_demo_relation/report.md) · [关系核查](../outputs/102_demo_relation/method_review.md)|[执行者自检](../outputs/102_demo_relation/selfcheck.json)，独立审计未执行|零API；构造及预算核查后停止，未运行分类，不自动103|\n|101_nsna_review|',1)
 edit('docs/TASK_INDEX.md',index)
 edit('docs/RESEARCH_EXECUTION.md',lambda s:line(s,'当前研究完成至101，','当前102已完成零费用可行性核查并在付费分类前停止；正式分类研究完成至101，默认无示例B＋Frozen PriorG不变。新研究须用户明确交办，本文件不是自动启动、重复训练、云部署或下一任务的授权。[最新状态](PROJECT_STATUS.md) · [任务索引](TASK_INDEX.md)。'))
 edit('docs/API_POLICY.md',lambda s:line(s,'研究完成至101。','研究执行至102：102零API、付费前停止，正式分类完成至101。本页只规定费用与服务边界，不授权新调用。102专项35元未开销；实际计划及停止原因见正式报告。历史额度不结转。'))
 print('Current navigation updated; historical tasks/default unchanged; no Git publication')
if __name__=='__main__':main()
