"""Record the later user push authorization without changing historical lines."""
from pathlib import Path

replacements = {
    "AGENTS.md": ("不改.gitignore、不commit/push、不自动083", "不改.gitignore、研究结项时未自动提交推送；用户后续单独授权推送082，不自动083"),
    "README.md": ("不改.gitignore、不commit/push、不自动083", "不改.gitignore、研究结项时未自动提交推送；用户后续单独授权推送082，不自动083"),
    "docs/PROJECT_STATUS.md": ("不自动083、不提交推送", "不自动083；研究结项时未自动提交推送，用户后续单独授权推送082"),
}
for name, (before, after) in replacements.items():
    path = Path(name)
    raw = path.read_bytes()
    a, b = before.encode("utf-8"), after.encode("utf-8")
    assert raw.count(a) == 1, name
    changed = raw.replace(a, b, 1)
    assert changed.count(b) == 1
    path.write_bytes(changed)
    print(name, "recorded later push authorization; line endings preserved")
