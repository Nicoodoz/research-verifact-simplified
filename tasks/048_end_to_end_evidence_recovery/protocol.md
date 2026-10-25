# 048：End-to-End GT-Blind Evidence Recovery

## 目标

048验证039→043的完整自动链路，而不是继续搜索新的selector。核心问题：对系统可观测的 raw-vs-U2 冲突病例，在不知道GT、也不预先挑选“搜索成功”病例的情况下，自动检索与逐要求证据核查能否让原DeepSeek作出更有依据的判断。

本任务只使用已消费的development材料，不重新使用reserved40做开发或选择。

## 可观测触发器与患者划分

母体为044 evaluation中round0 base核心有效病例。触发器只使用系统输出：
- raw DeepSeek verdict != Supported；
- 固定DeepSeek λ=2 后 U2 = Supported。

GT不参与触发、患者划分或方法输入。

该母体共有8名development患者。患者按固定 SHA256("048/patient/v1:"+sid) 排序：前4名为screen患者，后4名为confirmation患者，患者完全不重叠。

Screen从前4名患者各固定hash取4条触发病例，共16条；不看GT。
Confirmation预先冻结后4名患者的全部触发病例；只有screen方法达到晋级门槛才执行。

## 三个证据条件

B：原E0 + 原DeepSeek-V4-Flash-0731 scoring Judge，同期基线。

K（candidate-pool recovery）：
1. Qwen只看claim，生成material requirements和最多4条保守检索query；
2. 只把原031 C48候选池中未进入E0的原始passage作为additional evidence；
3. Qwen逐要求核查E0与这些additional candidates，可给Supported / Not Supported / Not Addressed / Uncertain，并必须引用逐字原文；
4. 程序只提取引用合法的additional passage原文，按引用首次出现去重后最多12段，追加到完整E0；
5. 原DeepSeek重新判断。若无合法外部引用，K与本轮B共享同一完整Judge输入，不重复调用。

G（full-eligible-EHR recovery）：
1. 复用K同一个claim-only query plan；
2. 在同患者目标住院031 eligible corpus中，对原claim做完整dense与BM25排序，并对扩展query做BM25排序；
3. 多路RRF后排除E0 passage，固定取最多32个additional candidate（与039实际冻结实现一致，而非旧protocol里的80）；
4. 使用与K相同的Qwen逐要求核查、引用校验和证据提取规则；
5. 把合法引用的原始EHR passage追加到完整E0，再由同一DeepSeek终判。

Qwen的summary、audit_label或rationale绝不进入最终DeepSeek输入；最终Judge只看到原claim和可追溯的原始EHR文本。

## Screen终点与晋级

每个条件同时保存：
- raw verdict；
- U0（label_scores不加偏置）；
- 固定DeepSeek U2（λ=2）；
- reason/checks；
- 实际新增passage与引用合法性。

主要机制终点：相对同期B的raw verdict paired rescue/harm与净正确。
系统安全终点：U2 paired rescue/harm、false-S变化。
辅助终点：U0、Supported score移动、reason是否引用新增证据。

K或G晋级需同时满足：
- raw净正确 >= +2；
- raw rescue >=2，且来自至少2名患者；
- raw harm <=1；
- U2净正确 >=0；
- U2 harm <=1；
- false-S不得增加。
最多2条路线晋级；若两条都通过则都进入confirmation。没有路线通过则停止。

Screen另事前固定6条病例，对B和G最终Judge各做一次独立repeat；G证据包在repeat前冻结，repeat不重新运行query/audit。重复只诊断最终Judge波动，不替代方法评价。

## Confirmation与报告边界

Confirmation只在screen晋级后执行，使用后4名患者的全部冻结触发病例，不再调prompt、候选数、引用规则或晋级标准。主报告保留患者方向、作者、GT类别、raw/U0/U2转移和成本。

由于触发集合本身是raw非S而U2为S，它不是自然benchmark子样本；048不会把触发集合准确率写成整体PA/MCC。若方法只改善raw但U2不变，应表述为减少后处理依赖、改善原生判断与解释一致性，而不是整体分类增益。

039/043的reserved post-hoc样本只作为历史机制证据，不用于048选样、调参或门槛。

## 完整性与预算

查询、审计、最终Judge都不接收GT、U2结果、旧reason或039/043类别。HTTP200不因答案内容重跑；无receipt未知请求不自动重发。请求先落盘、回执append-only。

Screen收费API累计保护上限10元；048全任务累计保护上限30元。预算上限不是支出目标，没有晋级则停止。

所有新增外部证据必须可按passage ID、note ID与raw offsets回溯到031 frozen corpus。执行者核验与独立审计分开。
