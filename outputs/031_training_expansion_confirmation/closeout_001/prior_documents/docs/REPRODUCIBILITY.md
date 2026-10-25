# 当前环境与安全复查入口

**030当前离线入口（快速独立审计PASS）：** 独立research-verifact-029环境；只读核验`close030.py outputs/030_gate_training_stability/<new-directory>`，重算保存模型不拟合；完整重训`run030.py --run-id <new-id>`，禁止覆盖run_001。[完整命令及边界](../outputs/030_gate_training_stability/audit_handoff.md) · [独立审计](../reviews/030_gate_training_stability.md)。

**029当前离线入口（快速独立审计PASS）：** 通过`conda run --no-capture-output -n research-verifact-029`运行`python -B tasks/029_semantic_information_gate/run029.py --run-id <new-id>`，禁止覆盖run_001。该入口离线重训固定条件，0 API，不修改原环境；收尾核验另重算3096个保存模型状态、0次拟合。[交审](../outputs/029_semantic_information_gate/audit_handoff.md)与[独立审计](../reviews/029_semantic_information_gate.md)含完整命令、固定预测bootstrap及辅助检查的工作区前提。

**028当前离线入口（快速独立审计PASS）：** `python -B tasks/028_traceable_claim_evidence_verification/replay028.py outputs/replays/<new-directory>`；禁网，从回执核对16份正式机器结果。只读核查为 `verify028.py outputs/028_traceable_claim_evidence_verification/<new-directory>`；禁止用收费runner重放。[独立审计](../reviews/028_traceable_claim_evidence_verification.md)。

**027当前离线入口（快速独立审计PASS）：** `python -B tasks/027_dual_judge_transfer_diagnosis/replay027.py outputs/replays/<new-directory>`；禁网、禁止新拟合，核对11个正式文件。正式analysis_002／figures_002；[独立审计](../reviews/027_dual_judge_transfer_diagnosis.md)说明概率来源、完整global及病例诊断边界。

**026当前离线入口（快速独立审计PASS）：** `python -B tasks/026_frozen_sd_patient_transfer/replay026.py outputs/replays/<new-directory>`；禁网、新目录、校验15个机器结果。只读来源核查：`verify026.py outputs/026_frozen_sd_patient_transfer/<new-verification-directory>`。禁止使用收费runner做重放。冻结SD未达迁移门槛，已停止；[主报告](../outputs/026_frozen_sd_patient_transfer/report.md) · [独立审计](../reviews/026_frozen_sd_patient_transfer.md)。

**025当前离线入口（快速独立审计PASS）：** `python tasks/025_lambda_flip_risk_separability/verify025.py`；重放`analyze025_numeric.py --output outputs/replays/<new-directory>`，网络禁用，不覆盖正式analysis_003。0API，固定λ不变。[独立审计](../reviews/025_lambda_flip_risk_separability.md)记录了来源重建、嵌套阈值与混合包络核验。

**024当前离线入口（快速独立审计PASS）：** `python tasks/024_lambda2_transfer_validation/verify024_core.py`；完整指标重放使用 `analyze024_core.py --replay-dir outputs/replays/<new-directory>`（仅离线，新建目录）。当前采用用户amendment_002核心字段与各比较有效交集口径，旧strict/repaired入口仅用于历史核查。审计重放额外禁用了socket网络；这些冻结入口本身不调用API，但不声称全部自带网络拦截。不要运行收费runner做重放。[当前状态](../outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)。


## 023离线复核（快速独立审计PASS）

`python -B tasks/023_lambda_boundary_response_analysis/verify023.py --output outputs/replays/audit023`

要求新目录、禁止网络；从冻结评分重建401点/精确/患者曲线并比较19个内容文件。其中16项从评分重建；3项描述重放读取已校验的正式分析表，独立审计另行核验其曲线依据，见[023审计](../reviews/023_lambda_boundary_response_analysis.md)。历史019–022不变。图重放使用既有research环境Matplotlib3.5.1，命令见[023交审](../outputs/023_lambda_boundary_response_analysis/audit_handoff.md)；不安装新BGE环境、不发API。

以下为既有已审任务的安全入口。

更新：2026-09-19。适用于已结项019–022；原任务README、报告和交审快照中的执行命令／待审状态保留形成时含义。

## 两套环境

| 用途 | 环境文件 | 说明 |
|---|---|---|
| 数据、002评价、已有回执／本地输出的离线重放 | [environment.yml](../environment.yml) | research-verifact，Python3.11；本次核对无须升级原计算依赖 |
| 本地BGE推理 | [environment.local-bge.yml](../environment.local-bge.yml) | 独立research-bge，Python3.9.23、Torch2.8.0+cu128、Transformers4.56.1；沿021实测关键版本 |

021历史实际使用既有research环境；新的research-bge是独立重建名称，不会修改该历史环境。021直接用Transformers，不依赖SentenceTransformers接口；历史环境另装的SentenceTransformers5.1.0不作为这套最小运行声明的必需包。

本次核对了现有环境包版本、模型哈希和全部pair未截断长度，未新建并安装一套空环境。因此yml是已核对的关键依赖声明，不宣称全新机器安装已实测或是完整传递依赖锁文件。CUDA 12.8包来源见[PyTorch官方历史安装页](https://pytorch.org/get-started/previous-versions/)。

## 安全离线复查

仓库根目录、research-verifact环境中运行，每个输出目录必须不存在：

~~~powershell
python -B scripts/replay_completed_research.py --task 019 --output outputs/replays/audit019
python -B scripts/replay_completed_research.py --task 020 --output outputs/replays/audit020
python -B scripts/replay_completed_research.py --task 021 --output outputs/replays/audit021
~~~

此入口先校验被审冻结文件，禁止网络，只复制必要材料到新目录，再重放原计算代码；不加载模型、不读取密钥、不发送API，也不重生成GPU输出。支持仓库外的新目录；仓库内只允许outputs/replays下的新目录。已有目录或受保护目录会拒绝，重放输出由.gitignore排除。

- 019：从原回执重放22个统计文件及停止决定（生成时间除外）。
- 020：从原回执重放11个分析内容文件，包括002患者bootstrap和固定λ决定。
- 021：从保存的本地向量／分数重建候选、pair及6个比较文件。新目录里的report.md是原生成器的简版渲染，正式中文主报告仍是outputs/021_bge_localization/report.md；二者的统计来源相同，不能回写覆盖。

**不要直接运行旧任务README中的整组执行命令来“复查”。** 旧GPU脚本会写入固定正式路径，旧verify021.py会重写verification_001.json；旧019 replay入口锁定历史导航且固定verification_001已存在。它们保留历史实现含义，日常复查使用上面的新入口。该入口校验冻结材料，不以放宽历史计算哈希换取通过。

## 模型与数据

原始数据和本地权重均不上传；原始VeriFact数据须用户合法取得并放入原路径。保存的研究回执、向量、分数和分析文件继续纳入Git，不用通用*.npy或*.jsonl规则误排除。

| 模型 | 固定revision | 本地权重 |
|---|---|---|
| BAAI/bge-m3 | 5617a9f61b028005a4858fdac845db406aefb181 | .local_models/021/bge-m3/pytorch_model.bin |
| BAAI/bge-reranker-v2-m3 | 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e | .local_models/021/bge-reranker-v2-m3/model.safetensors |

未来需要重新推理时，先取得上述固定revision对应的权重、config、tokenizer及sentencepiece文件，再按021登记SHA-256验证。不要把main分支文件混入冻结revision；模型路径由共享.gitignore排除，已有本机exclude可以保留。

021最终条件：embedding FP32/CLS/L2，reranker FP16/batch32/max_length512。49,246个pair实际未截断最大319 tokens。021本次只证明此冻结数据上的运行可行和不等价结果，不保证其他GPU／软件组合输出逐字节相同；后续新运行须用新目录登记，不能覆盖历史结果。

## 状态解释

019审计PASS不改变其原保护门槛失败；020审计PASS不等于reserved-test完成；021审计PASS不改变严格等价性FAIL。当前研究状态见[项目总览](PROJECT_STATUS.md)，当前调用路由见[API约定](API_POLICY.md)。

## 022 离线复查

022阶段A只使用NumPy/SciPy和现有002评价依赖，沿用research-verifact环境，无须变更环境yml或安装本地模型。仓库根目录运行，输出目录必须是新目录：

~~~powershell
python -B tasks/022_competition_aware_support_calibration/verify022.py --output outputs/replays/audit022
~~~

该冻结入口禁止网络、校验准备及分析哈希，重算15个内容文件并要求字节一致，不覆盖原成果。它还要求已跟踪文件只有原登记导航可变；提交后的干净工作区满足此要求，遇到其他未提交改动会拒绝，应保留改动并查明原因，不删文件强行通过。仓库外路径不在原入口支持范围内；本次审计使用临时路径适配，仅作用于新输出manifest路径，没有修改冻结源码。

022快速独立审计PASS，阶段A方法门槛FAIL；不因此开启收费阶段。独立复算证据见[审计附件](../reviews/artifacts/022_audit_20260919/README.md)。

027独立审计补充：21项测试、11文件重放、成对AUC及患者bootstrap、冲突/组级参考和31份病例来源绑定通过；重点完整深读四例，未重新医学裁决全部病例。见[审计范围](../reviews/027_dual_judge_transfer_diagnosis.md)。
