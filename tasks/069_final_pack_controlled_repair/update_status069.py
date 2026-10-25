"""Add 069 navigation to current project status, preserving original line endings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def edit(path, old, new):
    raw = path.read_bytes()
    before, after = old.encode("utf-8"), new.encode("utf-8")
    if raw.count(before) != 1:
        raise RuntimeError(f"expected one insertion anchor: {path}")
    path.write_bytes(raw.replace(before, after, 1))


def main():
    crlf = "\r\n"
    edit(ROOT / "README.md", "# Research-VeriFact" + crlf + crlf,
         "# Research-VeriFact" + crlf + crlf +
         "**069当前：** 066 C48内oracle修对的10条错误完成原包／oracle重复与只增、只删、组合受控对照。严格要求原包两次均错及操作两次均对后，稳定救回分别为只增2、只删1、组合1，均未达≥3条且≥3患者的事前门槛；GT盲第二步未启动。64/64 HTTP200，估算¥1.828542/8元，自检574 PASS，独立审计未执行；不自动070、不commit/push。 [069报告](outputs/069_final_pack_controlled_repair/report.md) · [067更正](outputs/069_final_pack_controlled_repair/067_correction.md)。" + crlf + crlf)
    edit(ROOT / "AGENTS.md", "# 项目背景" + crlf + crlf,
         "# 项目背景" + crlf + crlf +
         "**069当前：** final pack受控修复验证已按事前停止条件结束。10条066 GT-aware C48内修复病例中，原包重复3条自行改对；只增／只删／组合的严格稳定救回2／1／1，均未达同一操作≥3条且≥3患者的门槛。20条患者隔离development备选队列只冻结未执行；无GT盲方法成绩、正确病例保护未验证。64/64 HTTP200，费用估算¥1.828542/8元，自检PASS、独立审计待进行；不自动070、不commit/push。067历史口径冲突见[更正说明](outputs/069_final_pack_controlled_repair/067_correction.md)，069[报告](outputs/069_final_pack_controlled_repair/report.md)。未来新任务仍按下文默认10元政策，069特例上限8元。" + crlf + crlf)
    edit(ROOT / "docs/PROJECT_STATUS.md", "# 项目现状总览\n\n",
         "# 项目现状总览\n\n" +
         "**069当前：** 066 C48内GT-aware oracle修复病例的受控操作未找到达到事前门槛的稳定单一方案：只增2、只删1、组合1条稳定修复，原包本身重复3/10改对。患者隔离GT盲第二步未启动，不能宣称选择器成败或安全性。64/64 HTTP200、估算¥1.828542/8元、自检574 PASS，独立审计未执行；不自动070。[主报告](../outputs/069_final_pack_controlled_repair/report.md) · [067更正](../outputs/069_final_pack_controlled_repair/067_correction.md)。\n\n")


if __name__ == "__main__":
    main()
