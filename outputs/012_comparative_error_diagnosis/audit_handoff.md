# 012执行者自查与独立审计交接

**执行完成，等待独立审计。** 本文件不是独立结论。唯一主报告：[report.md](report.md)；重要结论的三个定向独立检查目录不等于整个012审计PASS。交接后停止修改同批成果。

## 实际被审版本

- 基础分支`main`，HEAD及本轮开始核对的`origin/main`：`b710543fd5caf8ca9b9017ec230cac9ac242f721`。
- **012尚未提交，也未推送。不能只审该HEAD。** 实际被审对象是HEAD加当前未提交成果；逐文件SHA256、精确Git状态及快照时间见[handoff_snapshot.json](handoff_snapshot.json)。快照不包含自身哈希。
- 开始前已经有`AGENTS.md`和`docs/siliconflow_pool/README.md`的账号起点说明修改，来自用户要求从`SILICONFLOW_API_KEY_2`开始使用；保留，不是012实验改动。本任务未读取或修改key文件，未调用余额/推理API。
- 本轮新增`tasks/012_comparative_error_diagnosis/`、`outputs/012_comparative_error_diagnosis/`、`tests/test_comparative_diagnosis012.py`；同步根`README.md`、`AGENTS.md`、`reviews/README.md`。`.gitattributes`仅追加012源码/测试的字节保留规则，防止当前`core.autocrlf=true`在以后提交/检出时改变冻结哈希；outputs已有统一保留规则。未修改任何历史独立审计原文、既有任务代码/结果、raw、.gitignore或环境定义。
- 高层说明明确012建议尚待审计；011的停止决定、未运行650条main、保留C48对照及reserved test边界继续有效。

## 主要检查入口

1. `protocol_001.md`、`alignment_002/selection.json`：深读前固定的规则，24例由标签方向/覆盖/历史阅读/哈希确定，不能根据报告故事反向选例。`alignment_001`是CSV字段错误中止草稿，002在任何新增全文深读前修好；没有按语义结果重抽。
2. `alignment_002/aligned_materials.jsonl`、`materials_001/packets.jsonl`：650对齐与24完整包；原rater121全reasoning_chain/final、原reference、010 canonical body/回执一一对应。C必须是010，不是009旧预测。
3. `diagnosis_001/ledger.csv`、`error_union.jsonl`：650完整台账，195错误并集、455三组都对、51三组都错；24深读中19错误/5共同对，176条错误未深读。`layer_review`的未归因不是确认无问题，不能将目的性深读转成总体类型占比。
4. `diagnosis_001/cases/*.md`：24例全文、医生票/评论、parent、字面锚点位置。重点N086、N395、N526分别是切分/候选/打包的不同轨迹；N501/N578并非C独有证据；N264共享目标改写；N139/N388是严格程度的反向例；N095/N188是医生GT及事件理解边界。
5. `raw_search_001/`和`pipeline_001/`：查找词式、实际范围、原文SHA/offset、保存排名/分数/舍弃；缺失分数是null，不填0。40条边界候选/11个切点不是临床错误率，部分其他入选块仍有否定。原系统上游留未知。
6. `independent_checks_001/`：直接重新连接原release及010回执，未导入012对齐逻辑；7例关键主题定向核查。`independent_checks_002/`独立核对650边界计数与N264。`independent_checks_003/`核对N501/N526/N578，确认9/1片段未入C候选。独立线程阅读范围如其原文所述，主线程24例完整reference阅读不能冒称独立线程也全读。

## 已完成自查

证据：[verification_001/verification.json](verification_001/verification.json)、[测试日志](verification_001/tests.log)。使用项目Conda环境、对socket联网入口施加禁止补丁。

| 检查 | 结果 |
|---|---|
| 自动化测试 | 165项成功，含字面否定/大小写、跨患者锚点拒绝、冻结输入变化拒绝、普通审计文件变化不阻塞等 |
| 确定性重放 | 对齐、全量C轨迹、有限原EHR查找、最终诊断/案例与统一评分，共45个内容文件逐字节一致（manifest时间不作比较） |
| 材料直接回查 | 24×3=72条proposition/医生/validity记录重新连接原表，416份EHR逐值一致、已有语料逐字节一致 |
| 原成绩保持 | 650×3预测保持；O/V/C逐作者PA、AC1、MCC、混淆矩阵和全部类别指标与010完全一致 |
| 历史保护 | 001–011共10,288个Git跟踪文件与HEAD一致并在重放前后不变；另4,884项011历史保护绑定通过 |
| API/数据边界 | 本轮新增调用0、费用¥0；无新开发/测试患者；既有回答不重跑 |
| Git字节与说明入口 | 13个012源码/测试文件的Git过滤前后字节哈希一致；主要说明链接检查通过，按既有CRLF规则检查无新增尾空白 |

逐字锚点检查曾发现两处摘录大小写/措辞未逐字匹配（N186、N395），在正式`diagnosis_001`生成前改为实际文本；没有放宽匹配或改变原输出。`raw012.py`首次内存查找曾遇note ID整型/字符串类型不一致，修正后才首次写正式目录。这些是本轮准备期修正，无失败推理、无收费补跑。

日常离线复查命令（输出目录须不存在）：

```powershell
E:/miniconda3/envs/research-verifact/python.exe -B tasks/012_comparative_error_diagnosis/verify012.py --output outputs/012_comparative_error_diagnosis/verification_replay_002
```

计算manifest严格绑定数据/代码/诊断输入；根README、AGENTS和审计索引是可变说明，不阻塞日常重放。**交审快照**记录它们当前哈希，只用于确认本次实际被审版本，不能被改作永久重放依赖。审计者的新结果目录应另建，原正式目录不覆盖。

## 未解决的研究限制

没有隔离O→V中模型/提示/结构化/运行期的单独贡献；没有恢复原系统未发布的上游日志。没有做证据补回/移除或新Judge实验，因此不把输入损失等同于已证明的标签因果。原GT一致性与特定来源事件理解分开，Codex诊断及生成解释均非医学GT。剩余176条错误无本轮深读，不强行填机制标签。012提出下一步候选，未证明其有效，也没有启动它们。

执行完成，等待独立审计。
