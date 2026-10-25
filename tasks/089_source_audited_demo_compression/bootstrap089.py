"""Create task-local copies of stable primitives; never changes earlier tasks."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
task=Path(__file__).parent
for name in ('common','api'):
    s=(root/'tasks/088_evidence_preserving_demonstration_compression'/f'{name}088.py').read_text(encoding='utf-8-sig')
    s=s.replace('088_evidence_preserving_demonstration_compression','089_source_audited_demo_compression').replace('088','089')
    if name=='api':
        s=s.replace("ip,op=PRICES[j['body']['model']]", "assert len(canonical(j['body']).encode())+2000<128000,'price tier bound'\n    ip,op=PRICES[j['body']['model']]",1)
    with (task/f'{name}089.py').open('x',encoding='utf-8',newline='\n') as f:f.write(s)
with (task/'.gitattributes').open('x',encoding='utf-8') as f:f.write('* -text\n')
