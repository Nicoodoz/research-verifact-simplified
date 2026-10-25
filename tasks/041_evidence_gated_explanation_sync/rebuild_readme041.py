from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
p=ROOT/"README.md"
cur=p.read_text(encoding="utf-8")
idx=cur.find("**036当前：**")
if idx<0: raise RuntimeError("036 marker missing")
header="# Research-VeriFact"
start=cur.find("\n",len(header))+1
add=cur[start:idx].strip("\r\n")

head=subprocess.check_output(["git","show","HEAD:README.md"],cwd=ROOT)
newline="\r\n" if b"\r\n" in head[:500] else "\n"
base=head.decode("utf-8")
idx2=base.find("**036当前：**")
if idx2<0: raise RuntimeError("HEAD 036 marker missing")
add=add.replace("\r\n","\n").replace("\r","\n")
new=base[:idx2]+add+"\n\n"+base[idx2:]
p.write_bytes(new.encode("utf-8"))
print("README rebuilt from HEAD with additions only; newline",repr(newline))
