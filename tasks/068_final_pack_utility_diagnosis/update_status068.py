"""Add current 068 navigation without altering historical task reports."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def edit(rel, old, new):
    path = ROOT / rel
    raw = path.read_bytes()
    a, b = old.encode("utf-8"), new.encode("utf-8")
    if raw.count(a) != 1:
        raise RuntimeError(f"expected one insertion point: {rel}")
    path.write_bytes(raw.replace(a, b, 1))


def main():
    crlf = "\r\n"
    edit("README.md", "# Research-VeriFact" + crlf + crlf,
         "# Research-VeriFact" + crlf + crlf +
         "**068当前：** final pack效用诊断完成。发现067 v1原包ID全空，所谓保守增补实际为约12段→1–2段替换；067较早v2冻结与较晚主报告互相冲突。v2修正分支raw正确177→181，PriorG后198→200但两条final救回同输入重复均未重现；不训练selector，先独立审计067来源口径。068新增164/164 HTTP200，估算¥3.785280/10元，自检PASS，独立审计未执行；无reserved、不自动069、不commit/push。 [068报告](outputs/068_final_pack_utility_diagnosis/report.md) · [当前状态](outputs/068_final_pack_utility_diagnosis/CURRENT_STATUS.md)。" + crlf + crlf)

    policy = "**2026-09-23 现行费用政策：** 新任务／实验收费 API 全任务累计上限人民币10元，含预检、重复、重试、所有阶段与未知预留；历史任务的原授权和账目不变。068按此上限执行。下文历史阶段文字中的80元仅表示当时授权。"
    edit("AGENTS.md", policy + crlf + crlf + "# 项目背景" + crlf + crlf,
         "# 项目背景" + crlf + crlf + policy + crlf + crlf +
         "**068当前：** final pack效用诊断已执行、自检PASS；067 v1原包映射全空，较晚报告使用v1与较早v2冻结/执行备注冲突。v2修正分支原2条PriorG救回在同输入重复中均未复现，raw 4条中3条同病例复现；当前无足够稳定的GT盲selector监督。068累计¥3.785280/10元、164次HTTP200、reserved未用；独立审计未执行，不自动069，不commit/push。 [报告](outputs/068_final_pack_utility_diagnosis/report.md)。" + crlf + crlf)

    prefix = "**2026-09-23 费用更新：** 新任务／实验收费API全任务累计上限10元；历史冻结任务预算不变。068执行范围见[事前协议](../tasks/068_final_pack_utility_diagnosis/protocol.md)。"
    edit("docs/PROJECT_STATUS.md", prefix + "\n\n# 项目现状总览\n\n",
         "# 项目现状总览\n\n" + prefix + "\n\n" +
         "**068当前：** 067 v1实现无效与v2修正分支的正式来源互相冲突；068分别核对后发现v2原2条PriorG救回均未在同输入重复中重现。raw有3条同病例重复救回，最终系统仍缺少可学习的稳定效用信号。068累计¥3.785280/10元，164/164 HTTP200，自检1346 PASS，独立审计待进行；不训练selector、不自动069。 [报告](../outputs/068_final_pack_utility_diagnosis/report.md)。\n\n")

    edit("docs/API_POLICY.md", "**现行更新（2026-09-23）：** 新任务／实验收费 API 全任务累计上限人民币10元，包含收费预检、重复、重试、所有供应商/阶段及未知请求预留。超过10元或无法合理估算须先确认；历史冻结任务的预算、授权与费用记录保持原样。\n\n# API现行执行约定\n\n",
         "# API现行执行约定\n\n**现行更新（2026-09-23）：** 新任务／实验收费 API 全任务累计上限人民币10元，包含收费预检、重复、重试、所有供应商/阶段及未知请求预留。超过10元或无法合理估算须先确认；历史冻结任务的预算、授权与费用记录保持原样。\n\n")


if __name__ == "__main__":
    main()
