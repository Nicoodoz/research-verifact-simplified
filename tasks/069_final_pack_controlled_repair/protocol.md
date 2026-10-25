> 阅读镜像：已省略20行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# 069：final pack 受控修复验证（收费执行前冻结）

## 研究目标与边界

在固定 053 T-S thinking-high scoring Judge 与 Frozen PriorG 下，判断 C48 内的证据包操作能否**稳定**修复原先错误，同时保护原先正确病例。066 的 GT-aware oracle 只用于第一步机制诊断，不是方法成绩；第二步选择器绝不读取 GT、oracle 选择或历史干预结果。全任务收费 API（预检、重复、重试、未知预留）累计≤人民币 8 元，所有阶段共用账本；不扩大检索、不换 Judge、不调 PriorG、不使用 reserved 开发、不按 HTTP200 答案择优重跑。不自动追加版本。

067 在 v1/v2 实现与正式来源上存在冲突，069 只作离线核查并提供单独更正说明，不改历史文件；不把 v1 的替换结果称为保守增补成绩。

## 第二步：条件触发的 GT 盲复现

候选队列在第一步新答案出现前确定：从 052 T-S 有效病例中，排除第一步 8 名患者与重复 proposition ID，按 SHA-256(ID) 顺序取原 baseline 错误 8 条、原 baseline 正确 12 条；这些标签仅用于评价分层，**不进入 selector 输入或 Judge body**。跨批次、患者隔离但仍属已开发 development，不是独立测试集。若某分层不足，按可用数量缩减且事前记录。

仅第一步过门槛时，冻结**一个**最小 GT 盲选择方案及其无变化规则。方案只能用 claim、原 final pack、同患者冻结 C48；不能看 GT、066 oracle passage、066/069 历史干预效果或病例名单的错误/正确分层。只对真正改变 reference 的病例调用同一 T-S Judge，未改变者复用原 052 回答。保护病例一并进入完整同 ID 评价。不得搜索多个 prompt、模型、分类器或后处理。

第二步报告全部 20 条的 raw 与 PriorG 后的 PA/AC1/MCC、false-S、逐例 rescue/harm、患者分布和固定重复。要称为值得继续的开发信号，至少须有 PriorG 后稳定 rescue≥2 条且跨≥2患者、保护病例 0 harm、false-S 不增加、净正确>0；否则停止当前版本。无论结果如何，不自动扩大到 reserved 或启动 070。

## 评价与交付

统一使用 `verifact_research.evaluation.evaluate` / `paired_compare`，默认 valid-only、三分类 micro、完整同 ID 和 1,000 次患者 cluster bootstrap。第一步是以 GT-aware oracle 挑出的错误病例组成的诊断样本，不计算部署方法的自然队列成绩；第二步单列原错误/正确分层，并说明人为加密带来的外推限制。保存协议、冻结请求、预算与回执、逐例结果、自检和中文报告。结论分别回答操作机制、重复性与 GT 盲可识别性。
