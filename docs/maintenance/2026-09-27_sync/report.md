# 092结项后的文档与环境说明同步

本次由用户授权查找并更新与项目现状不同步、矛盾或过时的说明，完成后推送。基准科学成果提交ee8060a2b1652aca7342e9ad0aab731f8822e242。此为文档维护，不创建093、不开展新研究、不改变默认系统。

## 找到并处理的问题

|问题|原影响|更新方式|
|---|---|---|
|README/AGENTS/PROJECT_STATUS重复堆叠多个“最新”|092完成与暂停、085完成与待部署并列；读者容易误启动|整理为单一当前状态，原文逐文件归档|
|现行规则仍含旧“不推送”|与完整任务自检后直接提交推送的用户约定冲突|AGENTS与RESEARCH_EXECUTION统一为新约定，旧任务范围另标|
|数据范围混用|仍绝对禁止reserved训练，或暗示存在未用患者，与092明确授权相冲突|写明全100人已暴露、092特定授权的五折CV，不能称新holdout，不自动授权新任务|
|环境名和版本落后|environment.yml仍为早期research-verifact，而启动器实际用research-verifact-029|实测CPU环境并同步根配置；旧依赖另存legacy清单|
|GPU用途与平台混淆|021 BGE、032/092本地verifier、092 AutoDL和085 vLLM混为一类|新增local-verifier/autodl-verifier清单，明确Python/tokenizer等差异与实际激活方式|
|API路由/预算混入历史|旧“全池耗尽后阿里云”、80/40元与当前Judge直连/20元规则混读|API_POLICY及平台说明只保留现行规则，历史专项不结转，旧客户端默认值另说明|
|任务导航仍写待审/暂停/待执行|例如033待审、085旧部署、087/090中的R1暂停、092恢复未完成训练|118份历史任务导航增加现行范围与正式来源，092 README改为已完成的隔离复现说明|
|更正链不显眼|067版本争议、086 fallback归因容易沿用旧表述|任务导航与总索引明确链接069/087追加更正，原报告不回写|
|论文和审计入口落后|v1稿含未回填占位；审计README停在072并残留80元现行措辞|指向092完整稿，更新实际审计记录索引，不将自检改称独立审计|
|复算与只读查看混淆|prepare/analyze/render/verify可能写正式目录|REPRODUCIBILITY及092 README标明写入和历史hash限制，不把生成器当只读命令|

共盘点2220份原已跟踪Markdown/YAML文档，按现行导航、冻结实验/审计、来源快照、历史协议及阅读材料分类；更新139份现行说明或配置，另交付归档、盘点及检查材料。这里的“盘点”指仓库清单和范围分类，不声称重新逐篇审读2220份研究报告或医学材料。准确路径及变化见[changes.json](changes.json)，全量分类见[inventory.json](inventory.json)。

## 环境核对

- 当前CPU：Python3.11.16、NumPy2.4.6、SciPy1.17.1、pandas3.0.6、scikit-learn1.9.1、duckdb1.5.5、Matplotlib3.10.8。通过原有禁网环境smoke test，优化器及矩阵核对成功。irrCAC/pypdf未在此主环境安装，不伪称具备。
- 本地032/092 venv：Python3.9.23，torch2.8.0+cu128、transformers4.56.1、numpy1.26.4、scipy1.13.1、scikit-learn1.6.1、tokenizers0.22.0、sentencepiece0.2.1、Matplotlib3.5.1。
- AutoDL092：依据用户已提供的原始快照，Python3.12.3、RTX4090、torch2.8.0+cu128、tokenizers0.22.2、sentencepiece0.2.2、Matplotlib3.10.5。未重新登录云端或查询实例。
- 五份环境YAML都经解析与对应版本核对。新清单是实测关键依赖声明，不是完整传递依赖锁，也未宣称空机器安装成功；本次没有安装、升级或重建任何环境。

[CPU自检](cpu_environment.json) · [CPU包清单](cpu_packages.json) · [本地verifier包清单](local_verifier_environment.json)。

## 历史保留与复现影响

修改前说明保持原字节和SHA，保存在[历史索引](../../history/2026-09-27_before_sync/README.md)中；归档使用.snapshot.txt，防止旧AGENTS成为嵌套生效指令。局部.gitattributes仅保护本次快照与检查材料字节，未改.gitignore。

本次没有修改outputs中的任何报告、指标、manifest或临床材料，没有修改任务protocol、训练/推理代码、src、独立审计正文、reviews/artifacts或docs/sources。历史README正文在新的适用范围提示下保留，阶段事实不追溯改写。

部分旧manifest把当年的导航README也绑定为SHA；更新导航后不能把当前文件冒充旧冻结输入。严格历史重放应使用对应冻结commit/隔离checkout及原导航快照，不能改旧manifest或放宽验证器。本次未运行历史研究重放，因此不宣称所有旧验证器在新导航工作区直接通过。092科学成果的completion指纹保持不变。

## 核查与交付

检查器[check_sync.py](check_sync.py)仅检查文件、SHA、YAML、版本、当前导航链接、历史保护边界和盘点完整性，不访问API、不训练。初次检查仅发现本报告尚未创建导致两条链接缺失，补齐报告后重新检查；最终状态见[verification.json](verification.json)。这是执行者文档自检，不是新增独立研究审计。

本机复查命令：E:/miniconda3/python.exe docs/maintenance/2026-09-27_sync/check_sync.py。使用现有Conda base提供的ruamel.yaml解析器，不要求把该维护工具依赖安装到冻结研究环境。

用户已有docs/002提示词.txt删除与docs/写论文提示词.txt未跟踪文件不纳入本次提交。0收费API、0新研究推理、0环境安装，不启动下一任务。按本次明确授权完成检查后提交并推送GitHub。
