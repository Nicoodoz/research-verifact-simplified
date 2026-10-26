# R1原生比较＋同配方PriorG：从准备到关机的操作手册

版本：2026-09-28。仓库核对版本：`28daf95e9b12270d8089246176023c66c4cf298e`（095结项）。本手册不恢复被用户取消的旧096，也不安排F4、Qwen或全量R1。

本包的启动脚本是按085的模型、服务别名、vLLM版本和20K接口要求整理的新建议配置，不是已经在你的新AutoDL实例上实测过的旧启动记录。脚本完成语法检查；最终以实例预检为准。

## 1. 一次实验，三层判断

计划约143条原校准材料＋800条按合格母体比例分层的主评价＋200条NS/NA压力诊断。压力集与主集分开，预算不足先缩压力集。估计需约1143次R1临床推理，不是为每个后处理各跑一次R1。

同一回答保存raw和三分数后，在CPU分别计算：raw/U0、旧V4 Frozen PriorG、R1重新适配PriorG、prior-only和G-only。V4-B主要复用095已有回答；原VeriFact发布预测无需重新调用。

原校准为051/052的16患者、143条T-S有效ID（48/47/48），原参考比例来自同16患者1378条命题（1108/100/170）；只重新拟合一维Supported偏置，不能把评估类别比例直接当新先验。校准患者排除于主评价；目标仍是开发阶段跨模型实证，不称独立医院验证。

原VeriFact@V4仅作为可选120–160条小桥接：原prompt、发布reference、输出提取逻辑能轻量复用才执行。不为可选项重建检索数据库或新租辅助GPU。仅换成作者reference而仍用本项目T-S，必须准确称“作者reference＋本项目T-S”，不能叫原VeriFact换V4。

## 2. 最省钱的执行顺序

先把`01_codex_execution_prompt.md`发给本地仓库中的Codex，末尾追加：

> 现在只做零API准备：建立任务、抽样、校准清单、冻结请求、费用估算及恢复入口。AutoDL尚未就绪，禁止访问R1端点或发送收费API。准备完成输出READY_FOR_R1。

等它完成代码和清单后，再开始有GPU的租机阶段。环境安装/权重下载若可在平台提供的较低成本准备模式完成，可以使用；本手册没有核实每台主机都提供该模式，也不把“无卡模式”假定为免费。

关键顺序：**先准备作业 → 下载和启动服务 → 隧道与预检 → 校准/评价推理 → 确认本地回执完整 → 平台关机 → CPU拟合、统计和论文整理。**

不要让A800开着，等待Codex写一小时报告。

## 3. AutoDL选型

优先恢复085那台仍保留的实例/环境和已下载权重。新建时建议：

| 项目 | 建议 |
|---|---|
| 实例类型 | 普通按量容器实例；不必上裸金属或包月 |
| GPU | **单卡A800 80GB**；同样80GB的A100可作备选，但记录实际硬件 |
| GPU数量 | 1；不建议为了这轮先调试双4090张量并行 |
| 主机内存 | 至少64GB，优先96/128GB |
| 磁盘 | 新装环境＋权重建议准备约100GB可用空间，并确认扩容费用 |
| 镜像 | 最优先085已跑通的私有镜像；其次经核实的vLLM0.10.1.1镜像；否则Ubuntu22.04基础框架镜像＋独立Python3.11环境 |
| CUDA/驱动 | 本手册安装路线使用vLLM0.10.1.1的CUDA12.8 wheel；优先选驱动可支持CUDA12.8的主机 |
| 模型 | `Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ` |
| 推理服务 | `vllm==0.10.1.1`；20000总上下文；客户端输出预算8192 |

这是一套资源建议，不是已测显存/吞吐保证。模型发布文件总量约39.8GB，GPU还要容纳KV cache和运行开销。不要误下载未量化的`deepseek-ai/DeepSeek-R1-Distill-Llama-70B`全精度权重。

平台镜像名称/库存/单价会变化，我没有访问你的登录后镜像选择器，不能保证存在某个逐字同名镜像。选镜像只是环境起点，以实际`python/torch/vllm`版本检查为准；不是“看到PyTorch2.8就算vLLM已装好”。AutoDL普通容器不支持内部再启动Docker，所以本手册采用Python环境而非`docker run`。

新租前记下**整实例单价、计费起点、GPU预算和最迟停止时间**。可以先按GPU30元＋按token API10元规划，但这是建议上限，不代表你的实际余额。不要把095的150元授权延续为本轮150元。

## 4. 环境准备（AutoDL终端）

### 4.1 已有085环境

先激活原环境，运行：

```bash
nvidia-smi
python -c "import sys,torch,vllm; print(sys.version); print(torch.__version__,torch.version.cuda,vllm.__version__)"
```

若已经是正常可用的vLLM0.10.1.1，不要重新安装。确认`MODEL_DIR`实际存在即可。

### 4.2 全新镜像

以下安装到数据目录，避免挤满默认系统盘。不要在Windows分析环境里执行。

```bash
mkdir -p /root/autodl-tmp/envs /root/autodl-tmp/tmp /root/autodl-tmp/models
export TMPDIR=/root/autodl-tmp/tmp
source "$(conda info --base)/etc/profile.d/conda.sh"
conda create -p /root/autodl-tmp/envs/r1-vllm python=3.11 -y
conda activate /root/autodl-tmp/envs/r1-vllm
python -m pip install --upgrade pip
python -m pip install --no-cache-dir "vllm==0.10.1.1" --extra-index-url https://download.pytorch.org/whl/cu128
python -m pip check
python -c "import sys,torch,vllm; print(sys.version); print(torch.__version__,torch.version.cuda,vllm.__version__); print(torch.cuda.is_available())"
```

`nvidia-smi`显示的CUDA版本是驱动支持上限，不是环境中PyTorch实际使用的CUDA版本。旧驱动报错时不要在容器里强行换宿主机驱动；换支持该路线的主机/镜像或停下来核查。

不要另装`autoawq`来读取已有AWQ权重；量化器和推理引擎是两回事，额外安装可能扰动现有依赖。此轮不做重新量化。

如没有tmux，可在服务器上安装：

```bash
command -v tmux || (apt-get update && apt-get install -y tmux)
```

## 5. 获取权重：先复用，没有再下载

把包内`scripts/`上传到服务器，例如`/root/autodl-tmp/r1_tools/`。仅上传这些脚本；不必把整个研究仓库/病历数据库上传到AutoDL。

### 首选：已有085权重目录

指定真实目录，不重新下载，也不凭目录名断言身份。保存其下载来源、revision、配置与tokenizer哈希。

```bash
export MODEL_DIR=/你实际已有的AWQ模型目录
ls "$MODEL_DIR/config.json" "$MODEL_DIR/tokenizer_config.json" "$MODEL_DIR/model.safetensors.index.json"
```

### 新下载：Hugging Face固定revision

使用独立下载环境，不往vLLM环境升级一堆依赖。

```bash
python -m venv /root/autodl-tmp/envs/r1-download
/root/autodl-tmp/envs/r1-download/bin/python -m pip install --upgrade huggingface_hub
/root/autodl-tmp/envs/r1-download/bin/python /root/autodl-tmp/r1_tools/download_model.py
```

默认固定仓库085记录的HF revision：`ebfea7be35ca86beee303282386399416205c306`。下载到：

```text
/root/autodl-tmp/models/DeepSeek-R1-Distill-Llama-70B-AWQ
```

脚本检查索引列出的权重分片存在，并保存`download_source_manifest.json`。它不下载临床数据、不启动推理。

若HF网络不可达，优先用085已成功的ModelScope来源。作为明确的备用下载路线：

```bash
/root/autodl-tmp/envs/r1-download/bin/python -m pip install modelscope
/root/autodl-tmp/envs/r1-download/bin/python /root/autodl-tmp/r1_tools/download_model.py \
  --source modelscope --revision master \
  --output /root/autodl-tmp/models/DeepSeek-R1-Distill-Llama-70B-AWQ-modelscope
export MODEL_DIR=/root/autodl-tmp/models/DeepSeek-R1-Distill-Llama-70B-AWQ-modelscope
```

ModelScope网页和085历史记录能够定位该模型，但本次没有验证其当前master与HF冻结commit的全部权重字节相等。两种源不能往同一目录混装，也不能把HF commit直接填写为ModelScope revision。下载失败时保留断点，不要为了下载成功临时换成另一70B量化模型。

下载若要很久，优先使用平台适用的准备模式；不要让昂贵GPU长时间空转。具体网络与存储收费以账户页面为准。

## 6. 启动服务（AutoDL终端）

激活正确环境后，把`serve_r1.sh`放入`/root/autodl-tmp/r1_tools/`。

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate /root/autodl-tmp/envs/r1-vllm
export MODEL_DIR=/root/autodl-tmp/models/DeepSeek-R1-Distill-Llama-70B-AWQ
# 若实际使用已有目录/ModelScope目录，上面改为实际位置。
tmux new -s r1-096
bash /root/autodl-tmp/r1_tools/serve_r1.sh
```

脚本主要启动参数：

```bash
vllm serve "$MODEL_DIR" \
  --served-model-name Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ \
  --host 127.0.0.1 --port 8000 --api-key EMPTY \
  --tokenizer "$MODEL_DIR" --tensor-parallel-size 1 \
  --dtype half --quantization awq \
  --max-model-len 20000 --gpu-memory-utilization 0.90 \
  --max-num-seqs 4 --max-num-batched-tokens 8192 \
  --enable-chunked-prefill --enable-prefix-caching \
  --reasoning-parser deepseek_r1 --no-enable-log-requests
```

脚本会记录环境与服务日志。启动成功、出现服务可接受请求的日志后，可按`Ctrl+B`，再按`D`离开tmux，不要按`Ctrl+C`终止服务。需回看时运行`tmux attach -t r1-096`。

vLLM0.10.1.1文档用`--reasoning-parser deepseek_r1`；不要照搬很早版本必须添加`--enable-reasoning`的命令。解析器只是把推理和最终答案分开，不保证每个输入都会生成长推理。

服务只监听loopback。`EMPTY`并不是公网安全密钥，不能把相同配置暴露在`0.0.0.0`或公开端口上。不要为此次实验开放6006/6008公网推理入口。

服务器另开终端测试：

```bash
curl -f -H "Authorization: Bearer EMPTY" http://127.0.0.1:8000/v1/models
```

OOM时先看错误发生在加载权重、profile、CUDA graph还是请求阶段。可以在正式冻结前把`max-num-seqs`降到2，必要时诊断`--enforce-eager`；不要先降低20K上下文或截短病历来掩盖显存问题。变更启动参数后保留日志，不宣称与085运行完全相同。

## 7. 本地Windows建立SSH隧道

从AutoDL控制台复制真正SSH主机和端口，例如它给你的登录形式为：

```text
ssh -p <SSH端口> root@<SSH主机>
```

在本地PowerShell窗口A中执行，替换两个占位符：

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:8000:127.0.0.1:8000 -p <SSH端口> root@<SSH主机>
```

按正常SSH流程核对主机指纹并登录，密码自己输入，不交给聊天、不写入仓库。不使用`StrictHostKeyChecking=no`。登录后窗口安静等待通常是隧道在运行，不要关闭窗口A。

也可用本包的PowerShell脚本：

```powershell
.\start_tunnel.ps1 -SshHost "真实主机" -SshPort 真实端口
```

窗口B中检查：

```powershell
curl.exe -f -H "Authorization: Bearer EMPTY" http://127.0.0.1:8000/v1/models
```

若本地8000已被其他进程占用，不要杀未知进程；可把左侧改成18000，R1_BASE_URL相应改为`http://127.0.0.1:18000/v1`。新任务应显式接受该loopback端口，不修改旧085锁。

这里的“本地”必须是**Codex实际执行runner的同一环境**。Windows能访问不代表WSL/容器中的127.0.0.1也通；若Codex在WSL，就在该环境里建立/验证隧道。不建议把临床端点改成公网来解决网络命名空间问题。

## 8. 连通性预检与正式放行

在本地runner所在环境运行随包`scripts/smoke_test.py`：

```powershell
$env:R1_BASE_URL="http://127.0.0.1:8000/v1"
$env:R1_MODEL="Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ"
$env:R1_API_KEY="EMPTY"
python .\scripts\smoke_test.py --output .\r1_smoke_result.json
```

这只发送一个虚构算术问题，不是临床成绩。应能取得非空最终content与正常结束；reasoning字段单列。精确的085式三分类/score接口预检由Codex在正式批量前做。

随后在持有原研究仓库及私有材料的本地终端启动/恢复Codex。命令行从同一窗口启动可继承上述环境变量；IDE里的已有Codex进程可能需要在它自己的实际终端/配置中设置变量。授权必须限于此项目与必要端点，不要求关闭沙盒或所有审批。

把下面放行消息发给已完成READY_FOR_R1的Codex：

```text
R1已准备好，请按01_codex_execution_prompt.md继续本轮实验。
本地/v1/models和虚构smoke均通过。
R1_BASE_URL=http://127.0.0.1:8000/v1
R1_MODEL=Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ
R1_API_KEY=EMPTY
vLLM=0.10.1.1；max_model_len=20000
GPU=（填写型号/数量）；整实例单价=（填写）元/小时
GPU计费起点=（填写日期、时间及UTC+8）
本轮GPU硬上限=（建议30）元；新增token API硬上限=（建议10）元
最迟停止R1新请求时间=（填写）
本地私有环境/模型来源记录路径=（填写）
先做精确请求技术预检和吞吐预算核算，再冻结可完成规模。
所有R1回执落本地并核对完整后，立即通知我平台关机，后续继续CPU分析。
```

满足以下条件即可放行：模型身份和环境记录有据、loopback隧道可达、虚构请求正常、Codex能读到原私有C48/校准材料、GPU单价/起点/上限已给、接口访问权限已正常授予。`/models`只通过而正式schema未试过时，不应直接千条发送。

## 9. 结束与省钱

Codex应写`R1_INFERENCE_DONE`，并确认校准和评价响应都已保存到本地私有目录、manifest可恢复。收到后到AutoDL网页执行关机，确认实例状态变为已关机。

关闭SSH窗口、Ctrl+C退出vLLM、停止Python，都不等价于停止平台计费。不要等论文图表画完才关机。

关机后仍可能有付费数据盘/文件存储等费用。不要删除唯一成果或释放未备份实例；权重可重下，研究请求、回执、校准参数和环境记录必须先备份。定时关机可以在平台预设为安全保险，时间由用户确认，不由本包偷偷调用平台账号接口。

## 10. 常见故障

| 现象 | 优先检查 |
|---|---|
| 连接被拒绝 | vLLM是否仍在加载/已退出；端口是否8000；隧道是否存活 |
| 401 | 客户端Bearer EMPTY与服务api-key是否一致；不要删掉全部认证或暴露公网 |
| /models模型名不同 | 是否连到旧1.5B练习服务/错误端口；served-model-name是否正确；再核实际模型目录 |
| Python CUDA导入失败 | vLLM/torch/wheel/宿主驱动兼容，不在容器里重装宿主驱动 |
| content为空、reasoning有内容 | 可能输出预算被耗完或解析模板异常；先看finish_reason，不补默认NA |
| 大量输出8192截断 | 技术问题先停，不能把全队列故障当R1弱；任何修复须在新冻结前记录 |
| Codex读不到病历 | 原文/回执为gitignored，重新clone不会带回来；在原本地仓库运行 |
| 校准后无增益 | 这是可报告结果；不自动改成2维/训练Gate/F4追分 |

## 11. 参考来源与事实边界

仓库来源（固定到095）：
- https://github.com/Nicoodoz/research-verifact/blob/28daf95e9b12270d8089246176023c66c4cf298e/tasks/085_r1_70b_valdemardi/README.md
- https://github.com/Nicoodoz/research-verifact/blob/28daf95e9b12270d8089246176023c66c4cf298e/tasks/085_r1_70b_valdemardi/preflight.py
- https://github.com/Nicoodoz/research-verifact/blob/28daf95e9b12270d8089246176023c66c4cf298e/tasks/052_first_tier_validation/fit_calibration052.py
- https://github.com/Nicoodoz/research-verifact/blob/28daf95e9b12270d8089246176023c66c4cf298e/tasks/053_thinking_prior_validation/protocol.md
- https://github.com/Nicoodoz/research-verifact/blob/28daf95e9b12270d8089246176023c66c4cf298e/tasks/053_thinking_prior_validation/common053.py
- https://github.com/philipchung/verifact/blob/main/scripts/evaluate/README.md （上游会变化，实际实验需固定commit）

官方服务/模型文档（2026-09-28核对）：
- https://huggingface.co/Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ/tree/main
- https://www.modelscope.cn/models/Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ （网页动态；实际下载revision需记录）
- https://huggingface.co/docs/huggingface_hub/guides/download
- https://docs.vllm.ai/en/v0.10.1.1/getting_started/installation/gpu.html
- https://docs.vllm.ai/en/v0.10.1.1/features/reasoning_outputs.html
- https://docs.vllm.ai/en/v0.10.1.1/cli/serve.html
- https://www.autodl.com/docs/env/
- https://www.autodl.com/docs/deps/
- https://www.autodl.com/docs/cuda/
- https://www.autodl.com/docs/ssh/
- https://api.autodl.com/docs/ssh_proxy/
- https://www.autodl.com/docs/local_disk/
- https://www.autodl.com/docs/price/

模型、版本与原配方来自仓库；GPU/内存/磁盘、样本量和30＋10预算属于本手册的建议，不是仓库已完成的实测。HF/ModelScope两源、Valdemardi/Casperhansen两个量化checkpoint均不在此声称逐字节相同。
