"""Prepend current 085 A/B status while preserving each existing file's newline style."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXTS = {
    "AGENTS.md": "**085 Valdemardi A/B最新（2026-09-27）：** 用户另行恢复085并接入本机SSH tunnel的AutoDL Valdemardi AWQ/vLLM 0.10.1.1；旧Casperhansen0.9.2、085A/AWS身份锁原样保留。360条冻结B/F4仅换model；虚构A及冻结B三条均首次HTTP200，actual prompt token与新本地tokenizer逐条一致，最长F4加8192=17884<20000。剩余B179/F4 178未调用，串行预估2.85小时、加50%余量4.27小时；本实例小时价未知。0评价GT、0正式批量、0默认升级；私有原生回执在忽略目录，自检61项及5项测试PASS。用户查看forecast并另行授权前不运行formal；本A/B任务结项后提交推送。[报告](outputs/085_r1_70b_valdemardi/report.md) · [预测](outputs/085_r1_70b_valdemardi/forecast.json)。",
    "README.md": "**085 Valdemardi A/B最新（2026-09-27）：** 用户另行恢复085；本机loopback实际服务为Valdemardi AWQ、20K上下文。冻结360条B/F4仅换Judge model；虚构A和三条冻结B均首次HTTP200，实际输入token与新模板一致。剩余B179/F4 178未调用，串行预测2.85小时、50%余量4.27小时；本实例时价未知。旧Casperhansen/085A/AWS不回写，0评价GT、0正式批量，默认不变；需另行授权formal。 [报告](outputs/085_r1_70b_valdemardi/report.md) · [预测](outputs/085_r1_70b_valdemardi/forecast.json)。",
    "docs/PROJECT_STATUS.md": "**085 Valdemardi A/B最新（2026-09-27）：** 用户新授权恢复085，在loopback接入Valdemardi AWQ/vLLM 0.10.1.1配置。085A冻结180条/21患者B/F4各180条仅换model；虚构A及固定short B、median F4、longest F4均首次HTTP200，raw与scores独立有效，实际输入token与Valdemardi本地模板逐条相等，最长F4+8192=17884<20K。当前B179/F4 178待formal，串行预估2.85小时、50%余量4.27小时；本实例时价未知。GT未读、V4未重跑、默认不变，旧Casperhansen/085A/AWS工件不改。独立审计未执行；需要用户看forecast后另行授权formal。[报告](../outputs/085_r1_70b_valdemardi/report.md) · [预测](../outputs/085_r1_70b_valdemardi/forecast.json)。",
}

for rel, paragraph in TEXTS.items():
    path = ROOT / rel
    original = path.read_bytes()
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    text = paragraph.encode("utf-8")
    if text in original:
        continue
    head, sep, rest = original.partition(newline + newline)
    if not sep:
        raise ValueError("unexpected heading structure: " + rel)
    path.write_bytes(head + sep + text + newline + newline + rest)
