"""Insert current 085A snapshot without changing existing files' newline style."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STATUS={
    "AGENTS.md": "**085A最新（2026-09-26）：** R1-Distill-Llama-70B的SageMaker JumpStart替换实验完成部署前离线准备：冻结084的180条/21患者、360条B/F4中立输入及四例；官方固定revision tokenizer仅取配置，chat长度B 2592–3918、F4 8368–9694。8K放不下F4，实际容器context未验证。AWS只读诊断、显式推理gate、延后A/B/C预检、原生解析和四臂评价框架已备；2194项离线自检PASS。0推理、¥0、未部署、未读评价GT选方法、未用reserved、未改.gitignore；默认B＋Frozen PriorG不变。等待用户手动部署并提供非敏感endpoint/示例调用信息，不自动开始正式085。本具体任务明确不commit/push，优先于一般推送约定。[085A报告](outputs/085_r1_70b_model_swap/report_predeploy.md)",
    "README.md": "**085A最新（2026-09-26）：** 已为JumpStart R1-Distill-Llama-70B替换实验冻结084的180条/21患者、360条B/F4中立输入；官方tokenizer审计B 2592–3918、F4 8368–9694 chat tokens，8K容器无法容纳F4。AWS只读诊断、显式推理gate、延后预检/解析/四臂评价框架齐备，2194项自检PASS。未部署、0推理/¥0、未用reserved或评价GT调方法；默认系统不变。等待用户手动部署，正式085未启动；本具体任务不commit/push。[报告](outputs/085_r1_70b_model_swap/report_predeploy.md)",
    "docs/PROJECT_STATUS.md": "**085A最新（2026-09-26）：** SageMaker JumpStart R1-Distill-Llama-70B部署前准备完成：084固定180条/21 development患者、B/F4各180条中立输入与四例SHA冻结。官方tokenizer chat长度B 2592–3918、F4 8368–9694；8K不足，16K＋4096输出可容纳全部F4，但实际容器context未确认。AWS诊断与推理显式gate、A/B/C延后预检、解析及统一四臂评价框架已备；2194项自检PASS。0新推理/¥0、未部署、未用reserved、未按评价GT调方法；默认B＋Frozen PriorG不变。等待用户手动部署；本具体任务明确不commit/push，不自动正式085。[085A报告](../outputs/085_r1_70b_model_swap/report_predeploy.md)",
}

for relative,line in STATUS.items():
    path=ROOT/relative
    raw=path.read_bytes()
    newline=b"\r\n" if b"\r\n" in raw else b"\n"
    first,sep,rest=raw.partition(newline)
    assert sep and "085A最新".encode("utf-8") not in raw and first.startswith(b"# ")
    path.write_bytes(first+newline+newline+line.encode("utf-8")+newline+newline+rest.lstrip(b"\r\n"))
    assert path.read_bytes().count(b"085A" )>=1
print("Updated AGENTS.md, README.md, docs/PROJECT_STATUS.md; existing newline style retained")
