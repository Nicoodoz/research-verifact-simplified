"""Add the finished 081 status to current navigation while preserving existing newlines."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUMMARY = (
    "**081最新（2026-09-25）：** 24名development患者96条GT盲选证U、GT教师T与同期原包B比较，Frozen PriorG正确71/73/74，raw为67/70/67；首轮Teacher/Blind gate均PASS，但配对区间跨0。48条患者哈希重复中，U−B净0→−3、T−B净+1→−4；T−U首轮净+1全部来自U/T完全同包的Judge波动。未证明稳定选包收益或GT特权增量，停止本版final-pack selector/utility learning，默认B不变。816个HTTP200、1个HTTP0保守预留，累计估算¥17.467488/20；Stage 2完整预算不足。执行者自检1299 PASS，独立审计未执行；无reserved、不自动082；研究结项时未自动提交，随后用户另行授权推送。 [081报告](outputs/081_gt_blind_evidence_selection/report.md)"
)


def insert(path, header, link_prefix):
    raw = path.read_bytes()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    anchor = (header + "\n\n").encode("utf-8").replace(b"\n", newline)
    assert raw.startswith(anchor)
    text = SUMMARY.replace("(outputs/", "(" + link_prefix + "outputs/")
    content = (text + "\n\n").encode("utf-8").replace(b"\n", newline)
    assert content not in raw
    path.write_bytes(anchor + content + raw[len(anchor):])


def main():
    insert(ROOT / "README.md", "# Research-VeriFact", "")
    insert(ROOT / "AGENTS.md", "# 项目背景", "")
    insert(ROOT / "docs/PROJECT_STATUS.md", "# 项目现状总览", "../")


if __name__ == "__main__":
    main()
