"""Record the user's later push instruction without rewriting historical records."""
from pathlib import Path

replacements = {
    "AGENTS.md": ("不改.gitignore、不commit/push、不自动084", "不改.gitignore、研究结项时未自动提交推送；用户后续单独授权推送083，不自动084"),
    "README.md": ("不改.gitignore、不commit/push、不自动084", "不改.gitignore、研究结项时未自动提交推送；用户后续单独授权推送083，不自动084"),
    "docs/PROJECT_STATUS.md": ("不自动084、不提交推送", "不自动084；研究结项时未自动提交推送，用户后续单独授权推送083"),
}
for name, (old, new) in replacements.items():
    path = Path(name)
    raw = path.read_bytes()
    a, b = old.encode("utf-8"), new.encode("utf-8")
    assert raw.count(a) == 1, name
    path.write_bytes(raw.replace(a, b, 1))
    assert path.read_bytes().count(b) == 1
    print(name, "recorded later push authorization")
