最终状态：执行与自查完成，等待独立审计。以report.md、audit_handoff.md及review_final_002为准；所有调用停止，不执行组合/新患者。35个预定案例（37对、75个完整输出）和事前探针5个额外输出已读；三处初稿成员解释由16项程序检查纠正。174测试、58内容文件重放、25 raw/10437历史保护通过。以下为过程记录，执行中/待做措辞仅是历史状态。

2026-09-15 更新：全部API已停止。screen六条件各231有效；四分支净正确数contract -12、guard -4、wide -5、selector -5，均未过预设门槛，gate已禁止组合/确认。总费估算/预留18.80024461元，其中未知回执预留0.05928；仅account_2，1435个请求、1436次HTTP，1次通信未知后同请求重试成功。剩余dev16/reserved40不动。正在做35案例/37比较的预登记定向诊断（完整输出＋实际增删/引用块，不声称所有reference全文重读）。已读完15057/27036/59250/59840全部17个选中案例，笔记3批已保存；接下来66218十例、93640八例。

# 013执行状态（可变交接记录，不是最终报告）

当前baseline与方法已经冻结，禁止看到结果后改规则/门槛。主Judge正在执行；暂未查看screen新标签，只有进度/输入诊断。

- 起始main/HEAD及origin/main：a7fca7edfde3a632f340649bbce8fc2fdeccbdbd；起始工作区干净，012已独立审计PASS。
- 四臂：contract（只做字面主谓合同）、text_guard（≤180字符否定/条件前缀）、wide_candidates（两路top80并集真实重排，refresh48同分数控制）、selector（原C48候选短ID集合选择，最终8000字符）。具体以protocol_001和mechanisms013.py为准。
- 231固定压力集=195错误并集+36哈希正确对照，LLM71/human160。三个同患者/作者稳定对照不重抽；first24 development已用，剩余16/reserved40无新实验。
- 单元：unit_aux16请求、unit_judge15独立/16逻辑，全部200、无重试。费用0.26049813+0.1903188=0.45081693；四分支通过窄机制门槛。N264目标保持后S→NA仍不符合原GT NS，不能当单元性能改对；N359/N139旧范围问题未解决。
- screen_aux：462请求全部200、无重试、费用7.69694908；selector没有格式退回。代码/协议/aux回执已冻结。
- screen_judge：1398逻辑（baseline+4分支+refresh48各231，加12baseline重复），942独立完整body。当前进程session由会话工具记录，不要重复启动；检查live/screen_judge/runner.lock及state/summary。所有200终态，非法或截断不重跑。
- API都从account_2，仅专用pool，不用.env或进程_1；全任务40元累计上限。native_stage013.py沿用011恢复方式，跨阶段费用单任务锁汇总。没有查余额/收费预检。
- preflight_001为172项断网测试通过；随后新增两个gate负测试，当前新增9项测试通过，最终应共174项。
- 历史保护history_before_hashes.json为10437个001–012跟踪成果/源码文件；evaluation_source_hashes.json固定10个评价/环境文件。
- screen_input_diagnostics_002为当前机器诊断。001错误用旧分数显示refresh48锚点rank；初版脚本和输出保留，final脚本只更正展示，方法/输入/指标/门槛没改。
- precharge_draft_001保留未发送预算草稿。39.8无条件总费概括已撤回，authority目前初始预计0.55559133；后续每阶段按实际请求和剩余额度预测，不承诺所有分支加确认无条件能完成。

接下来：等待screen_judge完整终结；跑score013.py，查看预设mechanical_gates；按已登记prepare_review013.py规则选读（统计候选全部翻转，未通过分支按作者/方向哈希及稳定对照）。写可追溯机制分析、最终gate。不能为过门槛追加v2/v3。

无分支通过就停止组合/新患者并完成负结果交付。有winner才冻结并实现确认（目前尚未实现确认管道，也尚未读取新患者逐例临床内容）：非selector优先下一8人789条；含selector前4人372条，均协议中预先按顺序固定。严格核算剩余额度，无法完整确认不能当论文方法候选。

score013统计snapshot费用只绑定unit_aux/unit_judge/screen_aux/screen_judge四阶段，后续费用不回填历史统计。export013在任务结束后统一导出全部实际阶段费用。verify013是待最后运行的断网重放/历史检查入口；如有确认必须相应扩展其复查范围。

交付尚待：screen指标与语义诊断、必要条件后续、中文主报告、最终自查、README/AGENTS/reviews索引同步、013源码Git字节保留、审计版本/哈希快照。旧run、raw、审计原文和.gitignore不动。不提交/推送或自行写审计PASS。
