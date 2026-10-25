"""Fix 021 README task row placement without normalizing line endings."""
from pathlib import Path
import common021 as c

p=c.ROOT/'README.md'
text=p.read_bytes().decode('utf-8')
row='| '+chr(96)+'021_bge_localization'+chr(96)+' | 两个BGE本地化完成；严格API→本地冻结等价FAIL，尚未独立审计 | [任务](tasks/021_bge_localization/README.md) · [中文主报告](outputs/021_bge_localization/report.md) · [当前状态](outputs/021_bge_localization/CURRENT.md) |'
sep='\r\n' if text.count('\r\n')>=text.count('\n')/2 else '\n'
# Remove any misplaced/correct copies, then place exactly after the table's 020 row.
parts=text.split(sep)
parts=[line for line in parts if line!=row]
index=None
for i,line in enumerate(parts):
    if line.startswith('| '+chr(96)+'020_lambda2_patient_validation'+chr(96)+' |'):
        index=i
        break
if index is None:
    raise ValueError('020 task table row not found')
parts.insert(index+1,row)
p.write_bytes(sep.join(parts).encode('utf-8'))
print('021 row fixed at table index',index+1)
