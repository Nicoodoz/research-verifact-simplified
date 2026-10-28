# 104工程复核记录

复核时间：2026-10-28（UTC+8）。仓库基准HEAD：`42e357f314a928253ed64c54dc45801e6307c1b7`。复核者：`training_interface104`子代理。本记录仅涉及工程不变量；不是医生审计、临床语义认可或分类提升证明。复核者编写过`training104.py`初版；该文件的检查不能称为完全作者独立审计。API、冻结器及构建器由其他执行者实现，本次进行另外阅读与测试。

结论：在下面明确限定的代码路径中，未发现需要阻止辅助API或数据构建的工程缺陷，无代码修复。现有30项纯合成测试在项目CPU/API环境中全部通过。本次新增API费用0，没有调用模型、加载权重或使用GPU；未读取真实GT key、教师解释、选型或确认集正文，未改首审台账。

## 调用、预算与恢复

- `api104.py`固定`deepseek-v4-flash-0731`、当前千问AI endpoint、thinking-high、temperature=0、top_p=1与8192输出上限。实际加载配置必须匹配固定模型/endpoint；底层transport校验body模型与配置一致，没有隐式重试，禁用redirect，回执按既有私有路径保存并去除凭据。
- 硬上限20元，主动发送运行线18元。每次发送前用SQLite `BEGIN IMMEDIATE`汇总全历史尝试，按完整UTF-8 request字节上界加2048输入余量、8192加32输出余量及忙时目录价预留；并发也要先提交预留再发送。预算不扣缓存，未知、HTTP错误和无回执尝试不释放预留。每个ID最多3次尝试，每次都独立计入累计额。
- 仅可验证的HTTP200 usage可替换保守预留；模型不符、usage异常保留预留并阻止后续dispatch。超过预留的可核实usage也如实入账并停止，不隐藏超额。开始和结束均处闲时、耗时不足一小时才采用闲时价，跨界按忙时。目录价依据见任务`pricing_verification.md`；本复核核对实现与已记录价表的一致性，没有另查账户实扣。
- HTTP200先持久化并登记，内容坏格式、截断或负面核查不触发内容重试；重启先从request/receipt重建账本，已有HTTP200的ID直接跳过。无回执的尝试按未知保留；其有限通信重试属于新计费预留，不声称原请求一定未计费。
- `api_run.lock`防止正常入口重复worker。异常退出遗留锁会让恢复拒绝启动，需确认无活进程后人工清理；当前实现不会自动删锁并冒险重复启动。没有做进程被杀或真实网络故障注入，因此不把代码阅读等同实机断电恢复验证。
- `freeze_api104.py`在任何`api_attempts`目录出现后拒绝重选抽样；候选质量面板固定hash每类最多16条，争议面板固定hash最多16条，总量不超过64。首次忙时全额预留超过16元则拒绝冻结。冻结manifest记录jobs、两份候选数据、盲审freeze、样本、预算和API实现SHA；run前逐文件核对。候选/争议集合由既定首审结果和GT抽样，不基于新增API回答；此检查不认可其临床筛选是否充分。

## 配对、编码与尾批

- `build104.py`必须先校验完整288条盲审freeze，才进入真实GT连接；原512训练ID唯一性和GT一致性有程序检查。首审快照与后续revision分别保留；初始一致仅产出`candidate_paired`，最终`paired`另需明确接纳决定、质量认可及引用检查。
- 构建输出严格同ID、同患者、同作者、同原GT、同claim/reference、同顺序与同messages；只有`answer`及同内容的`answer_text`不同。最终标签版也使用筛选后相同子集。实际训练prompt只接受claim/reference；GT、审查结果和方案名不会传入prompt。
- `training104.py`校验两臂schema、答案verdict与原GT、reference SHA、引句与当前reference逐字相符。重复引句必须保留全部出现位置，不能静默只选首处；偏移保留元数据，不进入答案。空引句仅允许NA，但程序真实性检查本身不能证明关系或NA判断正确。
- `encode_lists(tok,row)`不截断输入，prompt loss为−100，完整答案与`<|im_end|>`受监督；padding attention=0且loss=−100。两臂共用相同模板，JSON重复key被拒绝。现有端到端合成测试走真实freeze→build→loader→encode路径，覆盖重复引用、坏偏移和两份答案一致性。
- `optimizer_batches`以真实行数计划梯度累积，尾批不会丢弃、重复或仍除以8；按尾批实际行数缩放，保存真实`end_sample`并在最终尾批触发checkpoint。恢复只允许已消费的完整optimizer边界或全部结束位置。现有19条/259条合成用例检查了尾批和checkpoint边界。
- 重要限制：尾批函数与编码接口是下一次授权训练的对接准备，尚未执行新的真实训练loop、反向传播、优化器或checkpoint保存/重载。未来worker必须实际调用此批计划，不能直接原样沿用103中以固定8整除的循环；本轮没有修改103代码。实际9B tokenizer全候选长度统计由执行者另行运行，本复核没有读取临床配对文件重算。

## 实际测试与范围

成功命令（PowerShell）：

```powershell
& ./scripts/run_research.ps1 @('-m','unittest','discover','-s','tasks/104_supervision_evidence','-p','test*.py','-v')
```

结果：`Ran 30 tests ... OK`，用时0.428秒（测试器报告）。覆盖9项API、8项构建、9项训练接口及4项公开隐私扫描合成测试。首先误用系统Python时21项通过、API测试因缺`duckdb`导入失败；改用项目现有`research-verifact-029`后全通过，没有安装依赖或改变环境。`pwsh -File scripts/run_research.ps1 -m ...`不能正确绑定`-m`，上面的数组传参命令可复现。

本次阅读的版本指纹（SHA256）：

|文件|SHA256|
|---|---|
|api104.py|736b790ab44f4c14fa0f7a38ad869f8f1bfc117c58b5aba11270374d54fd6086|
|freeze_api104.py|58e9c07ef55af28595e82555e991b34164eaaf5e3b30f73b72279ab4c68616af|
|build104.py|623b2daba2fcbf1dde4e3f5b5629a8db6e121d74ccded768437c7949257a0147|
|training104.py|7964b507e6b075bda51b215f622b09d58afb7895005f02856d32954362bc9140|
|tokenize104.py|ef321f0836cc944a6f020ae844eec1ab52f31c8c5641daad006898381b0f598b|

未覆盖：真实API的服务端计费完整性、真实请求故障注入、临床语义充分性、实际训练收敛及预测收益。上述事项不能由30项合成测试替代。
