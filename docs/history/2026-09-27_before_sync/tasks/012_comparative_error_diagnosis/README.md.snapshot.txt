# 012_comparative_error_diagnosis

2026-09-15独立审计PASS，可冻结／结项。唯一必读：[简明中文主报告](../../outputs/012_comparative_error_diagnosis/report.md)。本任务为离线诊断，不是优化实验；没有API、新患者或新GT。

## 固定范围与比较

010同650条valid atomic claims：O=原rater121发布预测；V=发布reference＋010当前Judge；C=C48 reference＋010同期Judge。不得换成009旧预测。读取003及010/011最新审计尾部，复用004–009已有分析；011未过门槛的main不续跑。

[事前协议](../../outputs/012_comparative_error_diagnosis/protocol_001.md)固定完整三组台账、位置/机制/证据/不确定性框架及24例选择规则。22例未在先前案例包，但患者均已开发使用，非独立新测试。源上下文用于分析目标歧义，不作为EHR事实证据。

## 实现和成果

| 脚本 | 职责 | 当前正式结果 |
|---|---|---|
| `align012.py` | 650个release/010完整请求回执逐一对齐、错误并集、文本盲选例 | `alignment_002`；001为CSV中止的历史草稿 |
| `materials012.py` | 24例完整输出/两包/parent/医生票/本地轨迹和6患者原EHR、已有索引 | `materials_001` |
| `evidence012.py` | 重建650条C48选择；40条机械极性边界候选；原文至候选/重排/打包追踪 | `pipeline_001` |
| `raw012.py` | 同患者EHR的有限查找、正反/替代线索及原文锚点 | `raw_search_001`；命中不等于充分性，零命中不等于不存在 |
| `view012.py` | 完整输出/来源/两reference阅读；同患者相同块精确复用 | `reading_001`为阅读记录，不是语义gold |
| `diagnose012.py` | 逐字锚点校验、24例观察、全650最终状态与002统一评分 | `diagnosis_001` |
| `verify012.py` | 断网重放、严格冻结校验、原分数对照、历史保护及测试 | `verification_001` |

`notes_working.json`、`notes_batch002.json`、`notes_batch003.json`是三批执行者诊断输入，合成一份正式`diagnosis_001/diagnoses.json`；名称不表示另有未完成分析。所有引用均做大小写敏感字面校验。全量位置/标签机械校验与24例语义深读分开，176条错误本轮未深读。重要结论的独立定向核查见三个`independent_checks_*`，不等于全任务审计PASS。

## 复现

使用Conda `research-verifact`的Python 3.11，在仓库根目录运行；不加载key、不访问服务。新输出目录必须不存在，不覆盖正式结果。

```powershell
E:/miniconda3/envs/research-verifact/python.exe -B tasks/012_comparative_error_diagnosis/verify012.py --output outputs/012_comparative_error_diagnosis/verification_replay_002
```

入口文档、审计索引可正常变化，日常重放不以其SHA不变为前提；实际输入、现行分析代码、诊断文字、回执绑定和正式输出继续严格校验。交审快照另外记录可变文档当时版本，不将快照误作永久计算依赖。

停止边界：不改检索/重排/Judge，不补回干预，不从正向例子推总体比例。后续候选仅作建议，新任务另行确定。实际HEAD、脏文件及审计顺序见[交接](../../outputs/012_comparative_error_diagnosis/audit_handoff.md)。

当前独立结论见[012审计](../../reviews/012_comparative_error_diagnosis.md)。阅读缓存按metadata与空白规范化正文复用，实际reference/输出和字面锚点仍完整保留；不能把缓存等价当作结构等价。
