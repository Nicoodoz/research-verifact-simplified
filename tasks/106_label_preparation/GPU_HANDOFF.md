# 106：下一次GPU决策交接

**当前只完成准备，未获本轮GPU启动授权。** 推荐唯一任务为原196条上的标签目标诊断；不同时训练512数据路线，不补27B/35B，不改变默认系统。

## 已备好的私有包

- 目录：`.local_models/106_label_preparation/gpu_objective_bundle/`
- 归档：`.local_models/106_label_preparation/gpu_objective_bundle.tar.gz`
- manifest SHA256：`25ce0348590cb6f96cd4bf1adbe2bc115683db806047bfb690788e07bd24571f`
- 归档SHA256：`861cc2d58c46eb755480974e23b9b39b5e50654b18f076321a5ca96c21ccf8d1`
- manifest列51个文件，目录206,505,922 bytes，归档165,892,163 bytes。

包包含必要9B代码、原196标签输入、原500开发输入、12条固定训练诊断、冻结参数/环境/四分片预期SHA、缓存预测及约173MB的固定mean控制适配器；**含受限临床输入及训练权重，不可公开上传GitHub**。不包含基础权重、密钥、SSH密码、35B/27B或全部历史工件。固定mean只作推理控制，绝不作为sum初始化。完整optimizer无需为控制推理下载；它不在该控制备份中。

当前已分别通过执行者与独立子代理的全文件SHA核对、仓库外清PYTHONPATH/隔离导入和worker帮助检查。未加载9B、控制适配器或初始化CUDA。环境/基础模型是否仍完整可用，应在用户选择的未来环境中按真实SHA核对，不能据旧路径自动连接原实例。

## 下一次用户必须明确的事实

需要新GPU执行授权、实际小时报价、平台开始计费时间、累计预算和缓存模式。默认规划仍优先20元以内；按旧7.98元/小时估计含2元余量约8.52–10.73元。异GPU重评base500和mean500的谨慎规划约15.39元，但存在控制训练硬件不同的诊断限制；这些都不是本轮租卡授权。

优先复用原A800-SXM4-80GB及固定103/105环境、原9B四分片。缺环境/模型时先报告缺口，不自动下载、安装、购买或开机。严禁索要或复用旧SSH密码；由用户管理实例访问。

## 无卡准备与明确授权后的流程

1. 在用户提供、已合法准备的环境解包，只核对本包和必要9B，不克隆35B/27B与历史仓库。先用无卡阶段完成环境/权重/全部token映射预检：

   `python tasks/106_label_preparation/run106.py preflight --bundle . --model-dir <原始9B目录> --work <结果目录>`

   该入口不导入torch或加载权重；它核四分片SHA、安装版本、实际JSON token和prompt SHA。本地tokenizers0.22.0与GPU冻结0.23.3不同，逐条桥接必须真实通过，不放宽校验。

2. 用户明确决定执行后，填写私有授权JSON并绑定本包manifest SHA、报价/平台计费起点/预算。包内`AUTHORIZATION_REQUIRED.template.json`刻意设置为未授权，不能直接启动。授权还必须确认原始底座与环境及缓存模式。

3. `baseline_cache_mode=reuse`仅允许原精确GPU身份、冻结后端、模型、context13097、BF16、batch、greedy384、parser和逐条输入SHA全部符合。不同GPU的`rerun`模式须重评base500及冻结mean适配器500，不重训mean；并明确接受`accept_cross_hardware_training_diagnostic_only=true`。它只恢复推理对齐，mean仍在旧A800训练，不能作为严格新硬件纯loss确认。后端版本仍硬锁；要做新硬件严格训练控制须另行冻结同卡mean重训，当前包不自动追加。

4. 仅在上述新决定成立后，执行：

   `python tasks/106_label_preparation/run106.py run --bundle . --model-dir <原始9B目录> --work <结果目录> --authorization <本次私有授权JSON> --execute-authorized-gpu`

   流程串行完成：无optimizer更新的最长训练/完整batch资源gate；按实际已耗与整轮剩余成本检查可完成性；必要的新控制评价；固定训练诊断；原底座新训练sum196×2/50步/392消费；sum正式500及诊断。顺序、参数和输出解析不根据分数修改。

5. 每个模型的12条诊断保留自由greedy原输出及36条完整canonical JSON+EOS路径评分、首标签分支原始概率和评分上下文。成功greedy批次不重发；中断只补尚缺路径记录。缺诊断不得标完整任务完成；不能临时以路径MAP替换正式500的greedy结果。

6. 原子保存每步完整恢复状态、固定最终sum适配器和全部小回执后，程序写`MANUAL_SHUTDOWN_REQUIRED.json`，由用户在平台手动关机并确认。守卫不调用系统/平台关机，停止进程不代表停止计费。报告、大文件传输及归档在CPU/无卡阶段进行；原基础模型和历史权重不自动删除。

## GPU仍未执行的检查

真实最长反向的有限loss/非零梯度；开发及诊断最长完整8条batch资源；384完整生成的显存/吞吐；248个LoRA_B真实更新；50步/392消费与固定检查点；实际硬件数值行为；模型质量与最终账单。CPU小张量不能替代这些检查。

完成后用同包`evaluate106.py --bundle <包> --results <结果目录> --output <新CPU结果路径>`离线统一评价。自然/压力分开，主mean/sum共同有效与三臂共同表、完整覆盖、invalid与上下界、三类指标及患者配对区间同时报告。点门槛按[protocol](protocol.md)，不自动升级、扩量或进入确认40人。

当前状态保持 **READY_FOR_NEXT_GPU_DECISION**。本轮API0元、GPU0；没有提交或推送。
