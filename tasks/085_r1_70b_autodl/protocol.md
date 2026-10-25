# 085 AutoDL/vLLM恢复协议（事前）

用户在089后明确恢复085，替代AWS执行路线。原085A所有文件、暂停记录与089成果保持字节；新分支为tasks/085_r1_70b_autodl及outputs同名目录，不改.gitignore，不用reserved40，不自动其他研究。

只换Judge。复用085A/084冻结180条21患者、B/F4各180、原C48/claim/四例/语义，V4直接复用084同期回执。Primary为原生最终raw verdict，四臂共同有效ID评价；invalid/缺失固定180分母单列，不用旧答填R1。有效三分数才给U0/U2/FrozenPriorG compatibility，不拟合参数、不加辅助LLM。

目标casperhansen/deepseek-r1-distill-llama-70b-awq，tokenizer deepseek-ai/DeepSeek-R1-Distill-Llama-70B。public identity lock保存resolved revisions、公开每个权重文件SHA及config；远端预置模型先验证原文件哈希，不重下合法权重，不同checkpoint停止等待用户决定。原VeriFact配置证实仓库名，但未pin历史HF revision，因此不宣称原实验历史权重逐字节可证。官方tokenizer沿085A固定revision，而非AWQ仓库附带的另一份tokenizer。

远端用户租用/管理实例与SSH tunnel，项目不使用SSH密码、AutoDL token或AWS。模型默认缓存/root/autodl-tmp/huggingface，下载需远端显式选项且先检查数据盘空间。本地只取公开metadata，不下载权重。vLLM0.9.2、VLLM_USE_V1=1、dtype auto、context20000、显存0.90、TP1/PP1、block16、swap4、prefix cache、scheduler steps1、max_num_seqs4、enable_reasoning及deepseek_r1。直接python服务，无Docker。额外generation-config vllm防止HF generation_config悄然覆盖未指定采样参数，disable-log-requests防止服务日志记录研究原文；二者记录为实现差异。客户端temperature0/top_p1/max_tokens8192、nonstreaming；不添加Alibaba字段或新guided decoder，不追加提示、示例批注、8B解析器。

只接loopback的R1_BASE_URL（例如http://127.0.0.1:8000/v1），本地vLLM key为公开惯例EMPTY。先验证远端manifest+实时进程/版本/models观察，服务名本身不证明权重身份。单客户端串行预检；默认正式并发1，当前没有测量证据就不提高并发。未来若需提高至2–4必须保存同配置真实稳定性/显存证据并重新给出吞吐预测，不通过换模型、prompt、上下文或生成参数提速。

A为085A冻结的虚构病例，仅接口结构检查。B固定短B、中位F4、最长F4三例，第一份HTTP200直接计入360，不因无效/答错重发。实际prompt_tokens与085A官方tokenizer逐例值核对，最长9694+8192=17886，小于20000但真实服务仍须验证；不截断目标或示例。A观察envelope路径，B只检真实结构/usage/finish和解析有效性，随后按原parse_r1冻结profile，无GT输入。A/B若invalid或length保持原回答、gate关闭，不换案例或解码直到通过。

所有请求及OpenAI原始bytes append-only，SHA、模型、usage、finish、reasoning/content、墙钟时间与retry链保留；HTTP0/408/429/5xx最多3次，3/6秒退避。只有没有成功回答的请求可恢复；HTTP200核心无效按invalid处理。失联未知不猜免费，也不覆盖旧记录。正式请求成功后永不重复，Stage B三份按requestID直接复用。

AutoDL小时费用与项目API费用分账；不设置虚假的20元GPU额度。本阶段无付费API。runtime ledger记录用户提供的实例及服务起止、小时单价，正式run另外记录墙钟；这些区间重叠不能相加。A/B后按3例实际耗时/输出、并发1预测剩余357（或真实剩余）耗时，另给50%规划余量，声明样本小不是硬上界。没有实际单价则费用null，不编造价格。**在用户明确授权正式大批量前不运行formal**；formal需已有forecast和parser、单价、授权说明与max-runtime-hours。发送前预留一个timeout时长，防止无时间余量继续派发；GPU实例停止仍由用户管理，脚本不能控制停止租金。

评价复用085A公共函数：PA/MCC/AC1/Macro-F1、三类P/R/F1、混淆、false-S/non-S、救回伤害、患者胜负平、1000患者cluster bootstrap。比较R1-B−V4-B、R1-F4−R1-B、R1-F4−V4-F4，另报V4-F4−V4-B及F4效应跨Judge差异。raw与三分数分层，无GT修parser。区间跨零不是等效，不预告70B更强。

本轮先交付所有离线适配、远端脚本、tunnel说明、manifest、自检和无网络dry-run。无端点就明确等待，不冒充实测。正式085完成报告自检后提交推送；当前离线阶段不把正式研究标为完成，不自动下一任务。
