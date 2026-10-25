# 013执行者自查与独立审计交接

**执行完成，等待独立审计。** 主报告是[report.md](report.md)。没有通过筛选的组件；不执行组合或新患者确认，不追加v2/v3规则。执行者不宣布审计PASS，也没有改写001–012的独立意见。

## 实际版本

- 基础分支`main`，开始fetch后HEAD与origin/main均为`a7fca7edfde3a632f340649bbce8fc2fdeccbdbd`；开始工作区干净。
- **本次013尚未提交或推送。实际被审对象是HEAD加当前未提交成果，不是单独该commit。** 精确文件清单、SHA256、Git状态与快照时间见[handoff_snapshot.json](handoff_snapshot.json)。审计期间停止修改同批成果。
- 新增`tasks/013_multi_mechanism_screen/`、`outputs/013_multi_mechanism_screen/`、`tests/test_multi_mechanism_screen013.py`；同步根README、AGENTS、reviews索引以及013当前入口。`.gitattributes`仅为013新增源码/测试追加字节保留，防止Windows换行转换破坏指纹；`.gitignore`不改。
- 没有修改原始数据、历史任务代码/回答/run、医生GT、既有审计原文、环境依赖或key文件。API专用pool内部读取，从account_2开始；没有余额查询或密钥输出。

## 建议审计顺序

1. **协议和冻结时序。** `protocol_001.md`、`preparation_001/selection.json`及`authority_001.json`：195错误并集＋36哈希正确对照，原GT不改，四个独立分支和数值/类别/患者门槛在新输出前登记。新患者8人/含selector前4人仅为未执行条件方案。
2. **单位干预。** `unit_*_preparation_001`、`unit_analysis_001`：8个selector、8个重排、8对baseline/contract但仅15不同Judge请求。检查程序/原文事实与语义解释分离。四分支均过窄机制门槛，不代表全部问题已修复。N264单位答案NA仍不等于原NS；没有把单位结果充作压力集baseline。
3. **真实对照。** `screen_aux_preparation_001`、`screen_inputs_001`、`screen_judge_preparation_001`与`live/`：两个top80并集的完整真实重排；refresh48限原候选且用同次新分数；selector只选原C48 ID，没有生成证据/查询。最终Judge没有GT/source/BHC，合同也只含原claim逐字跨度。
4. **成绩和停止。** `screen_analysis_001`、`synthesis_001`：六条件各231完整；主1386逻辑条件共享到930主请求，另12重复。各作者/类别/患者与全部转移可重建；四分支总净正确数−12/−4/−5/−5。wide相对refresh48只有+2且LLM−1/human+3。没有用更好单个MCC点、单位案例、部分成功子集或人工补证替换主要结果。
5. **语义证据与可观察层。** 当前`review_final_002`为35案例/37个预定对照、75个不同完整Judge输出、87处字面锚点。`probe_followthrough.md`另跟踪事前探针，新增读取5个完整输出。检查`membership_backcheck_001`、`mechanism_analysis_001`，不要用是否被模型引用或阅读界面是否展开推断是否入选。
6. **费用与恢复。** `synthesis_001/attempts.csv`、`costs.json`及四阶段原生回执：1435请求/1436尝试；一次通信未知，旧预留0.05928元保留，按事前政策原样重试后成功。没有对收到的200答案重生成。总估算/预留18.80024461元，account_2承担所有本轮尝试，未核对账单。

## 自查结果与命令

[verification_001/verification.json](verification_001/verification.json)及[tests.log](verification_001/tests.log)：

|检查|结果|
|---|---|
|断网测试|174项成功；包括跨患者拒绝、非法selector ID退回、条件/否定正反例、全任务跨阶段预留、单患者收益/缺失不准晋级|
|输入/请求重建|1386份条件reference与1398条assignment一致；942个实际screen Judge请求（含12预定重复）|
|评分及诊断重放|58个评分、案例、机制/成员检查内容文件逐字节一致，manifest时间不参与内容比较|
|原始数据保护|25个文件仍匹配001输入指纹|
|历史保护|001–012的10437个Git跟踪代码/成果文件未改变；评价与环境的10个指纹亦核对|
|费用/边界|无组合/确认调用，无新患者实验、无reserved test方法选择；验证期间新增API=0|

使用Conda `research-verifact`，输出目录必须不存在：

```powershell
E:/miniconda3/envs/research-verifact/python.exe -B tasks/013_multi_mechanism_screen/verify013.py --output outputs/013_multi_mechanism_screen/verification_replay_002
```

该脚本封锁socket连接，只读已有回执。根README、AGENTS及正常审计索引变化不属于日常重放条件；实际数据、方法代码、请求、回执、分析结果继续严格校验。交审快照中的文档哈希用于确认本次被审版本，不是永久计算依赖。

## 执行准备与诊断修正记录

- `precharge_draft_001`保留未发送预算草稿及原代码。无条件全四分支再确认可能超过40元，旧39.8总费概括撤回；现行按阶段实际规模与整个任务剩余总额度检查，不把40元按阶段/账号重置。最后因效果门槛而停止，不是因预算耗尽。
- `screen_input_diagnostics_001`的refresh48锚点rank曾误用旧分数；当前002使用同次新分数。原脚本/输出保留，两个版本汇总量不变；没有改实验规则、reference或指标。
- `review_final_001`保留诊断初稿；`case_corrections.json`与`review_final_002`纠正N305的ASA、N425的8月5日拔管、N644的吞咽试验入选解释。实际片段仍在两臂中，不能叫新增/丢失。当前16项成员断言补充字面引文校验；它们不是医学gold。
- 阅读辅助的可变ledger最初使用了只允许新文件的writer，第一次续写报错；改为可变阅读记录写入，已展示的N048/N071材料重新登记。没有重跑模型或改变任何输入。阅读复用保留原始空白布局，未采用012被审计指出的空白归一化等价假设。
- 原代码及原始回执均未因上述诊断/展示修正而改写。当前实验方法没有在观察结果后修改；发现条件前缀会跨临床字段后，记录局限并停止，而没有补新规则再跑。

## 科研结论边界

压力集是旧开发患者的困难抽样，不是650条自然分布或独立测试。原reference非医学金标；模型解释不是内部因果证明。合同的表面复制统计不是语义保真率；前缀附加不保证条件归属；selector没有非法ID不等于集合充分；更大候选不保证末端选择。合法标签中的检查名称/引用编号等格式偏离保留为诊断，不据此删样本或推断没判断。

本轮没有证明任何优化可推广，未消耗剩余16名开发的确认机会。更广的理论问题不能由这四个版本一并否定；但当前没有依据继续扩大这些实现或默认组合。到此停止，交独立审计。
