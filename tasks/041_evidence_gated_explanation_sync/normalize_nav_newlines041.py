from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for rel in ("README.md","docs/PROJECT_STATUS.md"):
    p=ROOT/rel
    raw=p.read_bytes()
    p.write_bytes(raw.replace(b"\r\n",b"\n"))
    print(rel,"normalized LF")
