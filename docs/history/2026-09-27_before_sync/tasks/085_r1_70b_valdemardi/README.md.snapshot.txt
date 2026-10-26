# 085 Valdemardi / vLLM 0.10.1.1 运行配置

本目录是085原 Casperhansen/vLLM 0.9.2 离线分支之外的**独立实际运行配置**。旧 `tasks/085_r1_70b_autodl`、085A/AWS、身份锁及离线工件原样保留。所用模型属于相同 DeepSeek-R1-Distill-Llama-70B 基础家族，公开 `config.json` 的4-bit AWQ参数与旧目标相同；仓库checkpoint并非同一个，也不是原VeriFact完整流水线的逐字节复现。当前服务器仅通过loopback `/v1/models` 证明了服务名及20K上下文；远端权重字节和vLLM安装版本未由本机独立取证。

**正式任务已完成。** 085A固定180条/21名development患者，R1-B/F4各180个HTTP200；原Stage B三条复用，本轮357条新增，0重试。raw四臂共同有效177条；R1两臂raw及三分数在180条均有效。R1-F4 raw较V4-F4 raw净+13/177，但同180条R1-F4＋Frozen PriorG仅比当前V4-B＋Frozen PriorG多1正确、MCC更低、false-S多5/30；默认不替换。详见[正式报告](../../outputs/085_r1_70b_valdemardi/report_formal.md)。

## A/B历史快照

085A已冻结的180条/21名development患者、B/F4各180个请求，仅将`model`替换为 Valdemardi；Stage A为虚构病例，Stage B为既定short B、median F4、longest F4三条。A/B时4次推理均首次HTTP200，余357条尚未调用、GT未读取。此为正式授权前的历史状态，见[预检报告](../../outputs/085_r1_70b_valdemardi/report.md)。

## 路径与运行

- 显式配置入口：`preflight.py --profile valdemardi-vllm-0.10.1.1`负责A/B；用户另行授权后用`formal_runner.py --profile valdemardi-vllm-0.10.1.1`完成续跑。旧`tasks/085_r1_70b_autodl/runner.py`仍只代表Casperhansen历史配置。
- 本地变量：`R1_BASE_URL=http://127.0.0.1:8000/v1`，`R1_MODEL=Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ`，`R1_API_KEY=EMPTY`。仅接受loopback且禁止重定向。
- `prepare`需要忽略目录中的四个Valdemardi公开tokenizer/配置文件；固定revision为`ebfea7be35ca86beee303282386399416205c306`，不下载权重。
- 公开哈希、ID、token、耗时及[正式请求台账](../../outputs/085_r1_70b_valdemardi/formal_request_ledger.jsonl)：`outputs/085_r1_70b_valdemardi/`。含临床原文的冻结请求及全部原生回执：`.local_models/085_valdemardi_private/`，已被现有仓库规则忽略。迁移机器时需单独安全迁移该私有目录。
- `python tasks/085_r1_70b_valdemardi/selfcheck.py`可复核旧冻结来源、所有回执哈希、上下文及授权边界；`python -m unittest tasks.085_r1_70b_valdemardi.test_preflight`运行离线单测。使用已存在的`.local_models/085a_tokenizer_venv/Scripts/python.exe`可加载本地tokenizer。

## 正式执行与离线评价

用户于本轮明确授权余下357条，不再用A/B历史forecast或未知时价阻止执行。`formal_runner.py`每条首次HTTP200占位，保留全部原生尝试链，未读取GT；推理完先运行`reconcile_formal.py`核对3＋357。随后通过`scripts/run_research.ps1`运行`evaluate_formal.py`、`analyze_final_system.py`及两个自检脚本，最后`render_formal_report.py`生成并人工核查中文报告。正式批量已完成；再次运行正式脚本只会读取已有回执，不会为成功位置发新请求。用户未授权新的模型实验，不自动启动后续任务。
