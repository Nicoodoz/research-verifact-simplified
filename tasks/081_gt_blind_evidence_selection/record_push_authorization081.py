"""Record the later user push authorization without changing frozen research results."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(relative, old, new):
    path = ROOT / relative
    raw = path.read_bytes()
    before, after = old.encode("utf-8"), new.encode("utf-8")
    assert raw.count(before) == 1, relative
    path.write_bytes(raw.replace(before, after, 1))


def main():
    for path in ("AGENTS.md", "README.md", "docs/PROJECT_STATUS.md"):
        replace(path, "无reserved、不自动082、不commit/push。",
                "无reserved、不自动082；研究结项时未自动提交，随后用户另行授权推送。")
    replace("outputs/081_gt_blind_evidence_selection/CURRENT_STATUS.md",
            "无commit/push、不启动082。",
            "研究结项时未自动commit/push；随后用户另行授权推送，不启动082。")
    replace("outputs/081_gt_blind_evidence_selection/README.md",
            "本任务没有独立审计、commit或push；不启动082。",
            "本任务没有独立审计；研究结项时未自动提交，随后用户另行授权推送；不启动082。")
    replace("outputs/081_gt_blind_evidence_selection/audit_handoff.md",
            "本任务没有commit/push。",
            "研究结项时未自动commit/push；随后用户另行授权推送。")
    replace("outputs/081_gt_blind_evidence_selection/report.md",
            "历史工件未覆盖，无commit/push，不启动082。",
            "历史工件未覆盖；研究结项时未自动commit/push，随后用户另行授权推送；不启动082。")
    replace("tasks/081_gt_blind_evidence_selection/sync_status081.py",
            "无reserved、不自动082、不commit/push。",
            "无reserved、不自动082；研究结项时未自动提交，随后用户另行授权推送。")


if __name__ == "__main__":
    main()
