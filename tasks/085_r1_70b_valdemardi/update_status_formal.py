"""Prepend formal 085 outcome without rewriting historical status paragraphs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXTS = {
    "AGENTS.md": "**085 Valdemardi正式完成（2026-09-27）：** 冻结084的180条/21患者，R1-B/F4各180个唯一HTTP200；Stage B三条复用、正式新增357、0重试。177条四臂raw共同有效：原VeriFact/V4-B/V4-F4/R1-B/R1-F4正确154/134/139/138/152；R1-F4较V4-F4 raw净+13，但false-S 3→11/30、NA召回14→9/19，MCC仅+0.0033。全180条最终系统R1-F4＋Frozen PriorG对当前V4-B＋G正确156对155、MCC0.5423对0.5881、false-S11对6/30；不升级默认。主自检1853项、补充61项PASS，独立审计未执行；GPU价格/租金未知。旧085A/Casperhansen/AWS不改、reserved未用、私有原文/回执不推送。[正式报告](outputs/085_r1_70b_valdemardi/report_formal.md) · [对账](outputs/085_r1_70b_valdemardi/formal_reconciliation.json)。",
    "README.md": "**085 Valdemardi正式完成（2026-09-27）：** 180条/21患者的R1-B/F4各180个首次HTTP200，原Stage B三条复用、357条新增。177条raw共同有效R1-F4较V4-F4净+13，但false-S增加8/30；全180条R1-F4＋Frozen PriorG较现行V4-B＋G仅净+1、MCC下降、false-S增加5/30。默认不变；0重试，自检1853＋61项PASS，实例租金未知。旧085A/AutoDL身份锁不回写、reserved未用。[正式报告](outputs/085_r1_70b_valdemardi/report_formal.md)。",
    "docs/PROJECT_STATUS.md": "**085 Valdemardi正式完成（2026-09-27）：** 固定084的180条/21患者，R1-B/F4各180个唯一HTTP200，Stage B复用3＋正式新增357、0重试。raw四臂共同有效177条，原VeriFact/V4-B/V4-F4/R1-B/R1-F4正确154/134/139/138/152；R1-F4对V4-F4净+13但false-S3→11/30、MCC仅+0.0033。全180条冻结PriorG最终系统：现行V4-B 155正确/MCC0.5881/false-S6，R1-F4 156/0.5423/11；不升级默认。自检1853＋61项PASS、独立审计未执行，实例时价/租金未知；旧Casperhansen/AWS材料不改，不用reserved。[报告](../outputs/085_r1_70b_valdemardi/report_formal.md) · [对账](../outputs/085_r1_70b_valdemardi/formal_reconciliation.json)。",
    "docs/RUN_ENVIRONMENT.md": "**085 Valdemardi正式运行（2026-09-27）：** 用户管理的AutoDL A800/vLLM服务经本机loopback用于固定R1-B/F4各180条；公开服务名和20K上下文经过本机观察，checkpoint字节/远端版本仍未独立核验。单客户端并发1，357条新增＋3条Stage B复用，0重试。正式R1调用走独立`tasks/085_r1_70b_valdemardi/formal_runner.py`，统计评价走本页`research-verifact-029`启动器；两套环境用途不混淆。默认V4系统、旧085A/Casperhansen/AWS分支不改。[正式报告](../outputs/085_r1_70b_valdemardi/report_formal.md)。",
}

for rel, paragraph in TEXTS.items():
    path = ROOT / rel
    original = path.read_bytes()
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    new = paragraph.encode("utf-8")
    if new in original:
        continue
    heading, separator, rest = original.partition(newline + newline)
    if not separator:
        raise ValueError("unexpected status heading: " + rel)
    path.write_bytes(heading + separator + new + newline + newline + rest)
