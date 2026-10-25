# 项目说明一致性核查与修订（2026-09-15）

**已修正18份说明文件。** 当前统一状态是：001–009执行已完成并有相应独立审计依据；009于2026-09-15修订定向复核PASS，重放阻塞关闭，可正式冻结／结项。暂用C48、保留A48对照，未证明稳定优势／非劣；下一步优先单独验证EHR证据组织和打包中的检查身份、事件时间及实施状态，而非继续扩大通用planner。最终论文方法与贡献仍未确定。

核查开始时分支main、HEAD与fetch后的origin/main均为`fadcedc147c5f8507ade92c8d182cf350c16e1e9`，工作区干净。本次只作说明维护与离线检查，没有新推理、密钥读取、患者抽样或Git提交／推送，也没有重做独立审计。

## 发现与处理

|分类|问题|处理与依据|
|---|---|---|
|已修正|005–007任务入口、005–008成果入口仍写等待独立审计；008任务页缺当前审计状态|按各自2026-09-14独立审计同步完成状态；明确自查与独立结论的区别，不把任务通过当数据完整／方法有效|
|已修正|顶层摘要部分停留001–004；根README已完成列表不完整且重复第15节|前置截至009的当前状态，旧列表标为编号示例，009改为第16节|
|已修正|002／AGENTS中的默认baseline容易被理解为所有后续实验仍用发布R1预测|区分002发布预测历史参照与009新实验C48＋BGE rerank＋DeepSeek-V4-Flash；公共评价继续沿用002，不跨任务比较绝对MCC|
|已修正|40名开发患者全部可供后续新验证的旧措辞，以及003第二假设、005–008的下一步建议|明确前24名已用于方法／案例分析、剩余16名；早期建议按形成时间理解，005上下文试验已由006实施，检索与候选对照已由007–009推进，不当自动新待办|
|已修正|009成果表仍优先链接首次handoff及143项验证；原报告和旧交审页有等待复核措辞|表格区分修订PASS／146项验证与首次历史记录，入口明确提示原报告、源稿及交审页保留当时状态，不改原文件；历史清单不等于今后文档必须逐字不变|
|已修正|007任务文档将16元称为长期授权|限定为007当时任务预算，未来规则仍是全任务40元；没有改写历史8／16元授权|
|已修正|多账号工具仍写真实换号未实测、文件为空；通用Runner与009执行器行为混写|依据009已审回执标明account_1余额错误后换account_2；区分通用预留／暂停与任务自己的usage计费和重试，不声明当前余额或文件内容|
|已修正|Hospital-02笔记大量使用当前项目、正式版本、Stage09|只在页首增加历史项目身份提示，保留原技术记录；防止误认为Research-VeriFact当前方法或009任务|
|保留，入口注明历史|009审计开头／中段含初审PASS和有条件通过，末尾已更新为修订PASS|不改审计原文，reviews索引及009入口明确以最后追加为准；不是要求再次修复已经关闭的问题|
|保留，入口注明历史|005–009正式报告、报告源稿、旧run／verification／handoff中的待审计、未提交HEAD、旧测试数|原字节保留，任务／输出入口说明其历史性质；它们仍是对应版本的有效溯源，不作全仓库统一替换|
|仅建议，不应在本次修改|009干预对照长度／位置／重复随机性、rerank汇总usage为空但meta已计费|审计列为非阻塞建议，保持实验结果与限制，不能通过编辑文档假装已改进控制或修好计费展示|
|仅建议，不应在本次修改|002仓库外输出路径限制、原始标注／日期异常、论文区间差异、正式附录未取得|属于已有实现／数据／证据限制，不是状态同步应消除的矛盾；继续保留，不修数据、不补模型答案、不宣布已解决|

没有发现需要改写650条确认队列、243／407作者分母、三臂模型／检索设置、主要指标或费用的实质数值冲突。不同任务的样本量、预算、测试计数、原reference与新检索语料有其各自范围，不强行统一。006的189有效预测与190回答、192尝试，以及¥3.8661占用中的未知预留，继续保留。

## 当前统一研究约定

- **结论范围：** 008没有证明planner稳定有效；009不支持纯dense直接替代混合检索，C48仅暂定实用baseline。区间跨0不表示已证明等效或无效。
- **下一步：** 先在已用开发患者上单独验证evidence organization / evidence packaging，控制候选、重排和预算，关注检查身份、时间、计划与实施信息是否在切分／打包中分离；冻结方案后再用剩余开发患者确认。尚未证明这种组织改动能提高指标。
- **暂缓：** 通用planner扩展、纯dense替代、融合公式网格、无限扩容；不将局部诊断或实现修正包装成论文创新，也不宣布整个研究方向永久无效。
- **患者与评价：** 20探索／40开发／40保留测试的原分组不变；实际任务队列合并核对为24名已用开发、16名剩余。reserved test不用于方法选择；相同原claim、原医生标签与002统一评价继续适用。
- **执行：** 全任务预计费用≤40元的长期授权规则保持，具体历史任务预算不回写；API key仅在本地凭据文件。当前无全项目永久停用账号开关，换号状态按具体任务／阶段保存。

## 核查与验证

检查了根README、AGENTS、reviews索引、001–009各任务与成果入口共22个当前入口文件；并核对009正式报告／论文底稿、009完整审计末尾、执行修订说明、001–008审计最新结论、多账号说明和旧项目笔记定位。模板／源码资料不是当前状态页，不重新阅读保留测试病例或遍历临床正文作新归因。

修改后：

- **389个本地入口链接检查通过**；无失效目标，编码及原有换行保留。
- 修改前对8,433个Git已跟踪文件保存指纹；**除18份列明文档外，其余8,415个全部未变**。包括既有实验代码、测试、历史报告／run／manifest和独立审计原文；`.gitignore`与`.gitattributes`未改。
- 正式009离线重放在含本次文档修改的工作区完成，**146项断网测试通过，109个评分／诊断／案例／汇总内容文件与原结果逐字节一致**。原文、向量、排名、候选、真实分数、reference与完整请求缓存核查通过；费用仍为¥18.08218167，没有调用API。
- 没有为了文档同步更新历史SHA、放宽冻结材料检查或改实验代码。仅新增两个说明维护脚本和本次检查记录，不创建新编号研究任务。

证据：[文档核查结果](verification.json)、[逐文件改动与前后SHA](changes.json)、[修改前快照](before.json)、[009正式重放](../../009_retrieval_baselines/documentation_sync_verification_001/verification.json)、[测试日志](../../009_retrieval_baselines/documentation_sync_verification_001/tests.log)。

001／004任务及成果入口、009任务README和其他已经一致的说明未为统一措辞而修改。用户学习笔记与原论文／第三方代码资料保持原文；根目录已有来源定位及旧项目提示用于界定其适用范围。

## 实际修改文件及理由

下表为18份既有说明文件；维护辅助文件另为`scripts/sync_current_docs.py`、`scripts/check_documentation_sync.py`及本目录记录。

|文件|修改理由|
|---|---|
|[README.md](../../../README.md)|前置009当前统一状态、说明早期假设不是新待办、去掉不完整的已完成列表语义、修正重复章节号；补充逐任务段落的历史性质，清除005旧待办并明确C48限制|
|[AGENTS.md](../../../AGENTS.md)|消除顶层停留004、历史R1与当前C48混称、开发余量和006–008旧待办的歧义；明确C48非稳定优越，以及002元信息不统辖后续模型和队列|
|[reviews/README.md](../../../reviews/README.md)|保留所有独立结论，仅让索引用途不把早期下一步建议当当前待办|
|[tasks/002_reproduce_paper_results/README.md](../../../tasks/002_reproduce_paper_results/README.md)|区分002历史发布预测参照与009当前可部署比较链路|
|[outputs/002_reproduce_paper_results/README.md](../../../outputs/002_reproduce_paper_results/README.md)|移除R1为一切后续实验默认的歧义|
|[tasks/003_error_analysis/README.md](../../../tasks/003_error_analysis/README.md)|标明原第二假设的历史位置，更新分组使用余量|
|[outputs/003_error_analysis/README.md](../../../outputs/003_error_analysis/README.md)|保留003假设与患者划分，避免旧待办和40名全未用的误读|
|[tasks/005_pilot_effect_analysis/README.md](../../../tasks/005_pilot_effect_analysis/README.md)|005任务入口同步已有独立审计并区分原方案与当前方向|
|[outputs/005_pilot_effect_analysis/README.md](../../../outputs/005_pilot_effect_analysis/README.md)|005成果入口消除等待审计旧状态，明确报告历史措辞|
|[tasks/006_source_context_feasibility/README.md](../../../tasks/006_source_context_feasibility/README.md)|006任务入口同步已有独立审计并区分原方案与当前方向|
|[outputs/006_source_context_feasibility/README.md](../../../outputs/006_source_context_feasibility/README.md)|006成果入口消除等待审计旧状态，明确报告历史措辞|
|[tasks/007_context_retrieval/README.md](../../../tasks/007_context_retrieval/README.md)|007任务入口同步已有独立审计并区分原方案与当前方向|
|[outputs/007_context_retrieval/README.md](../../../outputs/007_context_retrieval/README.md)|007成果入口消除等待审计旧状态，明确报告历史措辞|
|[tasks/008_retrieval_planning/README.md](../../../tasks/008_retrieval_planning/README.md)|008任务入口同步已有独立审计并区分原方案与当前方向|
|[outputs/008_retrieval_planning/README.md](../../../outputs/008_retrieval_planning/README.md)|008成果入口消除等待审计旧状态，明确报告历史措辞|
|[outputs/009_retrieval_baselines/README.md](../../../outputs/009_retrieval_baselines/README.md)|使009首选链接直达修订PASS与146项验证，明确旧报告/交审历史性|
|[docs/siliconflow_pool/README.md](../../../docs/siliconflow_pool/README.md)|用009真实换号记录替换未实测旧说法，区分通用Runner与任务执行器及跨任务账号状态|
|[docs/动态切分提示词.md](../../../docs/动态切分提示词.md)|防止直接阅读旧Hospital-02材料时把其当前模型、Stage09和动态切分路线套到Research-VeriFact|
